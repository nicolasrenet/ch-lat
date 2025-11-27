#!/usr/bin/env python

from pathlib import Path
import sys
import itertools
import numpy as np
import json
from tqdm import tqdm
import logging
import re

import torch
from torch.utils.data.dataset import Dataset
from torch.utils.data import DataLoader
from torchvision.transforms import v2
from torchvision.transforms.v2 import Compose
from torchvision.datasets import VisionDataset
import fargv

from libs import transforms as tsf
from libs import seglib, metrics
from libs.htr_model import HTR_Model



# ## TODO:
# 
# * ensure that lines are concatenated in reading order (write a utility that may detect discrepancy between line ids and reading order)
# * performance measure: complete, with confusion matrix and F1, on large number of manuscripts
# * compare results with alignment based on edit distance

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s - %(funcName)s: %(message)s", force=True)
logger = logging.getLogger(__name__)

p = {
        "appname": "gt_alignment",
        "model_path": "/tmp/default_model.mlmodel",
        "img_paths": set([]),
        "heuristics_on": 1,
        "gt_seg_suffix": 'lines.gt.json',
        "pregt_htr_suffix": 'htr.pregt.json',
        "tenor_suffix": "revised_tenor.txt",
}

class InferenceDataset( VisionDataset ):

    def __init__(self, img_path: Union[str,Path],
                 segmentation_data: Union[str,Path], 
                 transform: Callable=None,
                 line_padding_style=None) -> None:

        trf = v2.Compose( [v2.ToImage(), v2.ToDtype(torch.float32, scale=True)])
        if transform is not None: 
            trf = v2.Compose( [trf, transform] )
        super().__init__('.', transform=trf )

        img_path = Path( img_path ) if type(img_path) is str else img_path
        segmentation_data = Path( segmentation_data ) if type(segmentation_data) is str else segmentation_data

        line_extraction_func = seglib.line_images_from_img_json_files if segmentation_data.suffix == '.json' else seglib.line_images_from_img_xml_files

        line_padding_func = lambda x, m, channel_dim=2: x # by default, identity function
        if line_padding_style == 'noise':
            line_padding_func = tsf.bbox_noise_pad
        elif line_padding_style == 'median':
            line_padding_func = tsf.bbox_median_pad
        elif line_padding_style == 'zero':
            line_padding_func = tsf.bbox_zero_pad

        self.pagedict = line_extraction_func( img_path, segmentation_data )
        self.data = []
        for (img_hwc, mask_hwc, linedict) in self.pagedict['lines']:
            mask_hw = mask_hwc[:,:,0]
            self.data.append( { 'img': line_padding_func( img_hwc, mask_hw, channel_dim=2 ), 
                                'height':img_hwc.shape[0],
                                'width': img_hwc.shape[1],
                                'line_id': str(linedict['id']),
                               } )
        # restoring original line dictionaries into the page data
        self.pagedict['lines'] = [ triplet[2] for triplet in self.pagedict['lines'] ]
        self.line_id_to_index = { str(lrecord['id']): idx for idx, lrecord in enumerate( self.pagedict['lines']) }
        

    def update_pagedict_line(self, line_id:str, kv: dict ):
        self.pagedict['lines'][ self.line_id_to_index[ line_id ]].update( kv )

    def __getitem__(self, index: int):
        sample = self.data[index].copy()
        return self.transform( sample )

    def __len__(self):
        return len(self.data)


def closest( tbl, val ):
    for i in range(val):
        if val-i in tbl.keys():
            return val-i

def split_on_offsets( string, offsets ):
    if not offsets:
        return string
    if not string:
        return []
    output = []
    last_offset = 0
    for i in offsets:
        output.append( string[last_offset:i] )
        last_offset = i
    output.append( string[last_offset:] )
    return output

if __name__ == "__main__":

    args, _ = fargv.fargv( p )

    for img_path in tqdm(list( args.img_paths )):

        logger.debug(img_path)
        img_path = Path(img_path)
        img_path_prefix = img_path.parent.joinpath( str(img_path.name).replace('.img.jpg', ''))
        segmentation_filepath = Path('{}.{}'.format(img_path_prefix, args.gt_seg_suffix))
        htr_gt_filepath = Path('{}.{}'.format(img_path_prefix, args.pregt_htr_suffix ))

        dataset = InferenceDataset( img_path, segmentation_filepath,
                              transform = Compose([ tsf.ResizeToHeight(128,2048), tsf.PadToWidth(2048),]), line_padding_style='median')
        model = HTR_Model.load( args.model_path )

        predictions = []
        for line, sample in enumerate(DataLoader(dataset, batch_size=1)):
            line_id = sample['line_id'][0]
            predicted_string, _ = model.inference_task( sample['img'], sample['width'])
            line_dict = { 'id': line_id }
            line_dict['text'] = predicted_string[0]
            dataset.update_pagedict_line( line_id, line_dict )

        transcriptions_pred = [ line['text'] for line in dataset.pagedict['lines']]
        logger.debug(transcriptions_pred)
        transcriptions_pred_cat = ''.join( transcriptions_pred )

        # Get GT transcriptions, 
        tenor_path = img_path.with_suffix('').with_suffix(f'.{args.tenor_suffix}')
        transcriptions_gt_cat = ''
        with open(tenor_path, 'r') as tenor_in:
            transcriptions_gt_cat = tenor_in.read().rstrip()

        # compute positions of line breaks in pred. (it is an offset in the string. Eg. 12 means 'after substring [0..11]
        line_break_offsets_pred = list(itertools.accumulate( len(tr) for tr in transcriptions_pred ))[:-1]
        logger.debug(line_break_offsets_pred)

        gt_segmented = [transcriptions_gt_cat]
        
        if len(line_break_offsets_pred) > 0:

            align_pred, align_gt = metrics.align_lcs( transcriptions_pred_cat, model.alphabet.reduce(transcriptions_gt_cat) )
            
            # compute map of aligned characters: pred_idx --> gt_idx
            lcs_translation_table = { p:g for (p,g) in zip( align_pred, align_gt ) }
            logger.debug(lcs_translation_table)
        
            line_break_offsets_gt_segmented = []
            for offset in line_break_offsets_pred:
                # in map of aligned pred chars, find closest one
                logger.debug(f"Closest({offset}, range={offset})")
                lcs_i_pred = closest( lcs_translation_table, offset)
                logger.debug("Found closest index in GT string ={}".format(lcs_i_pred))
                assert lcs_i_pred in lcs_translation_table
                lcs_i_gt = lcs_translation_table[lcs_i_pred]
                line_break_offsets_gt_segmented.append( lcs_i_gt )

            gt_segmented = split_on_offsets(transcriptions_gt_cat, line_break_offsets_gt_segmented)
            
            if args.heuristics_on:
                for idx, gtl in enumerate(gt_segmented):
                    # isolated letters heading a line should be put back at end of preceding line
                    if idx > 0 and re.match( r'^[a-z][., ]', gtl):
                        gt_segmented[idx-1] += gtl[:2]
                        gt_segmented[idx] = gtl[2:]

        logger.debug(gt_segmented)

        # updating (predicted) page dictionary with GT lines
        for idx, line in enumerate( gt_segmented ):
            dataset.pagedict['lines'][idx]['text']=line
        with open( htr_gt_filepath, 'w') as htr_outfile:
            json.dump( dataset.pagedict, htr_outfile, indent=4)
        

    sys.exit()

###################### UNREACHABLE ########
# IoU
line_break_offsets_gt = list(itertools.accumulate( len(tr) for tr in transcriptions_gt ))[:-1]
positions = list(range(len(transcriptions_gt_cat)))
gt_sets =  [ set(s) for s in split_on_offsets( positions, line_break_offsets_gt )]
gt_segmented_sets = [ set(s) for s in split_on_offsets(positions, line_break_offsets_gt_segmented)]

print('Lists have {} and {} elements, respectively.'.format( len(transcriptions_gt), len(gt_segmented_sets)))
for l in range(len(gt_sets)):
    intersection = gt_sets[l].intersection(gt_segmented_sets[l])
    union = gt_sets[l].union(gt_segmented_sets[l])
    print("IoU =", len(intersection)/len(union))
    
confusion_matrix = np.zeros((len(gt_sets), len(gt_segmented_sets)))
for i,gss in enumerate(gt_segmented_sets):
    for j,gs in enumerate(gt_sets):
        confusion_matrix[i,j]=len(gs.intersection(gss))

# row sum = all predicted set 1 assignments -> precision
confusion_matrix / confusion_matrix.sum(axis=1)

        





#!/usr/bin/env python
# coding: utf-8

# In[40]:


from typing import Tuple, List, Union, Callable
from pathlib import Path
import sys
import re
import itertools
import numpy as np

from torch.utils.data.dataset import Dataset
from torch.utils.data import DataLoader
from torchvision.transforms.v2 import ToTensor, Compose
from torchvision.datasets import VisionDataset

sys.path.append('..')
from libs import list_utils as lu
from libs import transforms as tsf
from libs import seglib, charters_htr, metrics
from model_htr import HTR_Model
from torchvision.transforms import v2
import torch


# ## TODO:
# 
# * ensure that lines are concatenated in reading order (write a utility that may detect discrepancy between line ids and reading order)
# * performance measure: complete, with confusion matrix and F1, on large number of manuscripts
# * compare results with alignment based on edit distance

# In[3]:


class InferenceDataset( VisionDataset ):

    def __init__(self, img_path: Union[str,Path],
                 segmentation_data: Union[str,Path], 
                 transform: Callable=None,
                 line_padding_style=None) -> None:
        """ A minimal dataset class for inference on a single charter (no transcription in the sample).
        Allow for keeping the segmentation meta-data along with the about-to-be generated HTR.

        Args:
            img_path (Union[Path,str]): charter image path
            segmentation_data (Union[Path, str]): segmentation metadata (XML or JSON)
            transform (Callable): Image transform.
            line_padding_style (str): How to pad the bounding box around the polygons
        """

        trf = v2.Compose( [v2.ToImage(), v2.ToDtype(torch.float32, scale=True)])
        if transform is not None: 
            trf = v2.Compose( [trf, transform] )
        super().__init__(root, transform=trf )

        img_path = Path( img_path ) if type(img_path) is str else img_path
        segmentation_data = Path( segmentation_data ) if type(segmentation_data) is str else segmentation_data

        # extract line images: functions line_images_from_img_* return tuples (<line_img_hwc>: np.ndarray, <mask_hwc>: np.ndarray)
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
            self.data.append( { 'img': line_padding_func( img_hwc, mask_hw, channel_dim=2 ), #tsf.bbox_median_pad( img_hwc, mask_hw, channel_dim=2 ), 
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
        print(f"type(sample['img'])={type(sample['img'])} with shape= {sample['img'].shape}" )
        return self.transform( sample )

    def __len__(self):
        return len(self.data)



# ## Collect data to be aligned
# 
# ### Predicted transcription on charter image

root = Path('.')

collection_path = Path('./data')
img_path = collection_path.joinpath('5411cf6870b06f5a1bb6df520cbdb4b9.Wr_OldText.5.img.jpg')
segmentation_file_path = collection_path.joinpath('5411cf6870b06f5a1bb6df520cbdb4b9.Wr_OldText.5.lines.gt.json')

dataset = InferenceDataset( img_path, segmentation_file_path,
                          transform = Compose([ tsf.ResizeToHeight(128,2048), tsf.PadToWidth(2048),]), line_padding_style='median')
model = HTR_Model.load('/tmp/teklia_fined_tuned_2025.01.30-2.mlmodel')


predictions = []
for line, sample in enumerate(DataLoader(dataset, batch_size=1)):
    line_id = sample['line_id'][0]
    predicted_string, _ = model.inference_task( sample['img'], sample['width'])
    line_dict = { 'id': line_id }
    line_dict['text'] = predicted_string[0]
    dataset.update_pagedict_line( line_id, line_dict )

transcriptions_pred = [ line['text'] for line in dataset.pagedict['lines']]
transcriptions_pred_cat = ''.join( transcriptions_pred )

print(transcriptions_pred_cat)



# ### Ground truth transcriptions


# Get GT transcriptions, 
tenor_path = img_path.with_suffix('').with_suffix('.revised_tenor.txt')
transcriptions_gt_cat = ''
with open(tenor_path, 'r') as tenor_in:
    transcriptions_gt_cat = tenor_in.read().rstrip()
print(transcriptions_gt_cat)


# ## Computing alignment

# compute positions of line breaks in pred. (it is an offset in the string. Eg. 12 means 'after substring [0..11]
line_break_offsets_pred = list(itertools.accumulate( len(tr) for tr in transcriptions_pred ))[:-1]
line_break_offsets_pred
print("Breaks in predicted strings =", len(line_break_offsets_pred))


align_pred, align_gt = metrics.align_lcs( transcriptions_pred_cat, model.alphabet.reduce(transcriptions_gt_cat) )
#''.join([ transcriptions_pred_cat[i] for i in align_pred ])


def closest( tbl, val ):
    for i in range(val):
        if val-i in tbl.keys():
            #print("Closest=",val-i, end=" ")
            return val-i
            
lcs_translation_table = { p:g for (p,g) in zip( align_pred, align_gt ) }
#transcriptions_gt_segmented = []
#last_offset = 0
line_break_offsets_gt_segmented = []
for offset in line_break_offsets_pred:
    print(transcriptions_pred_cat[offset], end=' ')
    # find closest index in LCS-pred. Before or after? Depends on how
    # likely characters at SOL and EOL respectively are included in the LCS.
    lcs_i_pred = closest( lcs_translation_table, offset-1)
    lcs_i_gt = lcs_translation_table[lcs_i_pred]
    line_break_offsets_gt_segmented.append( lcs_i_gt+1 )
print("Breaks in segmented GT strings =", len(line_break_offsets_gt_segmented))

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



'@'.join(transcriptions_pred)
print("Length:", len( transcriptions_pred))


gt_segmented = split_on_offsets(transcriptions_gt_cat, line_break_offsets_gt_segmented)
'@'.join( gt_segmented )
print("Length:", len( gt_segmented))


#''.join([transcriptions_pred_cat[i] for i in align_pred ])


# ## Evaluation IoU



print(gt_segmented, "len=", len(gt_segmented))

sys.exit()


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

        





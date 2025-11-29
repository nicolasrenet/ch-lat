from pathlib import Path
import re
import json
import itertools
import base64
from datetime import datetime
from PIL import Image, ImagePath
import sys 
import io


def lemmatize( p:Path, suffix='', replacement=''):
    if suffix:
        return re.sub(r'(.+).{}$'.format(suffix), r'\1.{}'.format( replacement ) if replacement else r'\1', str(p))
    return re.sub(r'\..+', f'.{replacement}' if replacement else '' ,  str(p))


class Fsdb:

    def __init__(self, conf ):
        self.config = conf


    def stats(self, ):
        """ A few stats about this database."""
        
        img_suff, lines_gt_suff, lines_pred_suff, htr_pregt_suff, htr_gt_suff = [ self.config[k] for k in ('charter_img_suffix', 
                                    'gt_seg_suffix', 'pred_seg_suffix', 
                                    'pregt_htr_suffix', 'gt_htr_suffix') ]
        all_charters = list(Path(self.config['fsdb_root']).glob('*/*/*/CH.cei.xml'))
        
        if self.config['crop']:
            charter_img_paths=list(Path(self.config['fsdb_root']).glob('*/*/*/*.seals.crops/*.{}'.format(img_suff)))
        else:
            charter_img_paths=list(Path(self.config['fsdb_root']).glob('*/*/*/*.{}'.format(img_suff)))

        current_state = [ 
                ( Path(lemmatize(p, suffix=img_suff, replacement=lines_pred_suff )).exists(), Path(lemmatize(p, suffix=img_suff, replacement=lines_gt_suff )).exists(),
                  Path(lemmatize(p, suffix=img_suff, replacement=htr_pregt_suff )).exists(), Path(lemmatize(p, suffix=img_suff, replacement=htr_gt_suff )).exists()) for p in charter_img_paths ]
        report = { "total_charters": len(all_charters), "total_images": len(current_state), 
                "lines_pred_count": len(list(itertools.filterfalse(lambda t: not t[0], current_state))), "lines_gt_count": len(list(itertools.filterfalse(lambda t: not t[1], current_state))),
                "htr_pregt_count": len(list(itertools.filterfalse(lambda t: not t[2], current_state))), "htr_gt_count": len(list(itertools.filterfalse(lambda t: not t[3], current_state)))
                }
        report['lines_pred_ratio']=round(float(report['lines_pred_count']/report['total_images']),2)
        report['lines_gt_ratio']=round(float(report['lines_gt_count']/report['total_images']),2)
        report['htr_pregt_ratio']=round(float(report['htr_pregt_count']/report['total_images']),2)
        report['htr_gt_ratio']=round(float(report['htr_gt_count']/report['total_images']),2)

        return report


    def search(self,  archive_id:str='*', charter_img_id:str='*', suffix:str=None) -> list[Path]:
        if suffix is None:
            suffix = self.config['charter_img_suffix']
        if self.config['crop']:
            file_paths=list(Path(self.config['fsdb_root']).glob('{}/*/*/*.seals.crops/{}.{}'.format(archive_id, charter_img_id, suffix)))
        else:
            file_paths=list(Path(self.config['fsdb_root']).glob('{}/*/*/{}.{}'.format(archive_id, charter_img_id, suffix)))
        if not file_paths:
            return None
        return file_paths

    def write_img_metadata(self, data:dict, archive_id:str, charter_img_id:str, suffix=None):
        if suffix is None or suffix==self.config['charter_img_suffix']:
            return {}
        output_filename = self.search( archive_id, charter_img_id )
        if output_filename is None:
            return {}
        output_filename = lemmatize( output_filename[0], suffix=self.config['charter_img_suffix'], replacement=suffix)
        returnValue, outputfile = {}, None
        try:
            outputfile = open(output_filename, 'w')
            print( json.dumps(data, indent=4), file=outputfile)
            outputfile.close()
            returnValue = {'filename': output_filename, 'size': Path(output_filename).stat().st_size }
        except (IOError) as e:
            outputfile.close()
        return returnValue

    def read_img_metadata(self, archive_id:str, charter_img_id:str, suffix=None):
        if suffix is None:
            return {}

        infile, returnValue = None, {}
        data_path = self.search( archive_id, charter_img_id, suffix=suffix)
        if data_path is None:
            return {}
        try:
            infile = open(data_path[0], 'r') 
            returnValue = json.load( infile );
        except (IOError, FileNotFoundError) as e:
            pass
        finally:
            if infile is not None:
                infile.close();
        return returnValue;


    def write_flags(self,  flag_data:dict, archive_id:str, charter_img_id:str):
        return self.write_img_metadata( flag_data, archive_id, charter_img_id, suffix='flags.json')

    def update_flags(self, updates:dict, archive_id:str, charter_img_id:str):
        flag_data = self.read_img_metadata( archive_id, charter_img_id, suffix='flags.json')
        flag_data.update( updates )
        print(f"fsdb_update_flags({updates}) -> {flag_data}")
        return self.write_img_metadata( flag_data, archive_id, charter_img_id, suffix='flags.json')


    def read_flags(self,  archive_id:str, charter_img_id:str):
        return self.read_img_metadata( archive_id, charter_img_id, suffix='flags.json')

    def write_segmentation_file(self,  page_data: dict, archive_id:str, charter_img_id: str)->dict:
        """
        Write segmentation data into a JSON file.

        TODO: deal with multi-region files.

        Args:
            archive_id (str): archive name
            charter_img_id (str): charter atom id
            page_data (dict): a dictionary
                {'image_width': <width>
                 'image_height': <height>,
                 'regions': [ 
                    {'coords': ...,
                     'lines': [{'centerline': [[x1,y1], ...], 'coords': [[x1,y1], ...]}, ...] }]}
            charter_img_id: Image atom id.
        Returns:
            dict: if successful, an object with filename and size; otherwise an empty dictionary.

        """
        width, height = page_data['image_width'], page_data['image_height']
        # Image-wide pseudo-region: change to simply read actual regions 
        page_data.update( {
            'image_filename': Path(page_data['image_filename']).name,
            "type": "centerlines",
            "text_direction": "horizontal-lr",
            #"regions": [ { 'id': 'r0', 'coords': [[0,0],[width-1,0],[width-1,height-1],[0,height-1]] } ],
        })
        page_header={ 'metadata': { 'created': str(datetime.now()), 'creator': 'ch-lat:{}'.format(Path(__file__).name), 'comments': '' }}
        page_header.update( page_data )
        return self.write_img_metadata( page_header, archive_id, charter_img_id, suffix=self.config['gt_seg_suffix'])


    def read_segmentation_file(self, archive_id:str, charter_img_id: str, suffix: str ) -> dict:
        """
        Args:
            archive_id (str): archive name
            charter_img_id (str): charter atom id
            suffix (str): 'lines.gt.json' (GT) or 'lines.pred.json' (prediction).
        Returns:
            dict: a segmentation dictionary.
        """
        return self.read_img_metadata(archive_id, charter_img_id, suffix)

    def get_archives(self, ) -> list[str]:
        """
        Get a list of all archive directories.

        Returns:
            list[str]: a list of archive names.
        """
        archives = list([ p.name for p in Path( self.config['fsdb_root']).glob('*') if p.is_dir() and re.match(r'[A-Z]{2}-[A-Za-z]+', p.name)])
        archives.append('COLLECTIONS')
        return sorted(archives)


    def get_charter_images(self, archive_id:str='') -> tuple[str,dict]:
        """
        For given archive, get a map of all images, with their attributes.

        Args:
            archive_id (str): the name of an archive directory; if empty, the first archive in the list is used.
        Returns:
            tuple[str,dict]: a pair with the archive id passed to the function, as well as a dictionary
                with image ids as keys and a dictionary of image attributes (filename, segmentation data, ...)
                as value. 
        """
        if not archive_id:
            archive_id = sorted([ p.name for p in Path( self.config['fsdb_root']).glob('*') if p.is_dir() and p.name != '.git'])[0]
        charter_images = []
        if self.config['crop']:
            charter_images = [ {'id': lemmatize(img.name, suffix=self.config['charter_img_suffix']), 'archive': archive_id, 'filename': str(img), 'gtsegfile': None} for img in Path(self.config['fsdb_root']).glob('{}/*/*/*.seals.crops/*.{}'.format( archive_id, self.config['charter_img_suffix'])) ]
        else:
            charter_images = [ {'id': lemmatize(img.name, suffix=self.config['charter_img_suffix']), 'archive': archive_id, 'filename': str(img), 'gtsegfile': None} for img in Path(self.config['fsdb_root']).glob('{}/*/*/*.{}'.format( archive_id, self.config['charter_img_suffix'])) ]

        for number, ch_img in enumerate(charter_images, start=1):
            filepath_stem = lemmatize( Path(ch_img['filename']), suffix=self.config['charter_img_suffix'] )
            ch_img['number']=number
            if self.config['crop']:
                ch_img['charter']=Path(ch_img['filename']).parent.parent.name
            else:
                ch_img['charter']=Path(ch_img['filename']).parent.name

            gt_seg_filename = '{}.{}'.format( filepath_stem, self.config['gt_seg_suffix'])
            if Path( gt_seg_filename ).exists():
                ch_img['hasGTData']=True
            pred_seg_filename = '{}.{}'.format( filepath_stem, self.config['pred_seg_suffix'] )
            if Path( pred_seg_filename ).exists():
                ch_img['hasPredData']=True
        
        return archive_id, charter_images


    def get_image(self, archive_id: str, charter_img_id:str):
        """
        Find an image from the given archive, given its id.

        Args:
            archive_id (str): the name of an archive directory.
            charter_img_id (str): the image id.
        Returns:
            bytes: an array of bytes.
        """
        charter_img_path = self.search( archive_id, charter_img_id )
        if charter_img_path is None:
            return None
        try:
            data = open( charter_img_path[0], 'rb' ).read()
            return data
        except (IOError) as e:
            print("Could not open {}".format( charter_img_path[0]))
            return None


    def read_lines(self, charter_img_id:str, data_type='pregt', polygon_key='coords'):
        """ Read line items. 
        Output:
            tuple[list[list],int}]: a list of line descriptors, as well as the maximum
                width of a line (character length).
        """

        suffix = self.config['gt_htr_suffix'] if data_type=='gt' else self.config['pregt_htr_suffix']
        charter_img_path = self.search( '*', charter_img_id )
        charter_htr_path = self.search( '*', charter_img_id, suffix=suffix)
        if charter_img_path is None or charter_htr_path is None:
            return ([], -1)
        else:
            charter_img_path = charter_img_path[0]
            charter_htr_path = charter_htr_path[0]
        try:
            page_img = Image.open( charter_img_path, 'r')
            page_dict = json.load( open(charter_htr_path, 'r') )
            line_tuples = []
            max_width = 0
            # YET TO BE TESTED
            lines = itertools.chain.from_iterable( [ reg['lines'] for reg in page_dict['regions'] if 'lines' in reg ] )
            #if reg in page_dict['regions']:
            #    if 'lines' in reg:
            #        lines.extend( reg['lines'] )
            for tl in lines:
                polygon_coordinates = [ tuple(pair) for pair in tl[polygon_key]]
                textline_bbox = ImagePath.Path( polygon_coordinates ).getbbox()
                bbox_width = textline_bbox[2]-textline_bbox[0]
                if bbox_width > max_width: 
                    max_width = bbox_width
                imgByteArr = io.BytesIO()
                page_img.crop( textline_bbox ).save( imgByteArr, format='PNG')
                line_tuples.append( [tl['id'], tl['text'], base64.b64encode(imgByteArr.getvalue()).decode(), bbox_width ])

            return (line_tuples, max_width) #json.dumps(line_tuples)
        except (IOError) as e:
            print("Could not open{}".format( charter_img_path))
            return ([], -1)

                

    def write_line_transcriptions(self, line_transcriptions, charter_img_id ):
        """
        Export the aligned transcriptions:
        1. Read the line candidate GT file
        2. Update the segmentation dictionary with the transcription
        3. Save under a new name ('*.htr.gt.json')
        """
        # read htr/segmentation file
        page_htr_dict = self.read_img_metadata('*', charter_img_id, self.config['pregt_htr_suffix'])
        new_lines = [] 
        for idx, line in enumerate( page_htr_dict['lines']):
            if line_transcriptions[idx]=='--<discard>--':
                continue
            new_lines.append( page_htr_dict['lines'][idx] )
            if line_transcriptions[idx] is not None:
                new_lines[-1]['text']=line_transcriptions[idx]
        page_htr_dict['lines']=new_lines 
        return self.write_img_metadata( page_htr_dict, '*', charter_img_id, suffix=self.config['gt_htr_suffix'])




"""
A Flask interface to read and write segmentation data on locally stored charters.
"""
from flask import Flask
from flask import render_template, request, jsonify, make_response, redirect, url_for, abort
from pathlib import Path
import re
import json
import itertools
import base64
from PIL import Image
from typing import List, Tuple
import sys

# TODO:
#

app = Flask(__name__)



# SETTINGS
app.config.update(
    scaling_factor= .7,
    max_width=1450,
    charter_img_suffix='img.jpg',
    gt_segfile_suffix='lines.gt.json',
    pred_segfile_suffix='lines.pred.json',
    fsdb_root='/home/nicolas/tmp/data/fsdb_work/fsdb_full_text_sample_1000',
    crop=False,
    gui_tool_smoothing=False,
    gui_tool_dataType='gt',
    gui_tool_strokeWidth=6,
    gui_tool_overlapHandling=True,
    gui_tool_overlapBuffer=2,
    gui_tool_overlapScope=3,
    gui_tool_annotationFlavour=0,
)

app.config.from_prefixed_env()

def lemmatize( p:Path, suffix='', replacement=''):
    if suffix:
        return re.sub(r'(.+).{}$'.format(suffix), r'\1.{}'.format( replacement ) if replacement else r'\1', str(p))
    return re.sub(r'\..+', f'.{replacement}' if replacement else '' ,  str(p))



########## DATA ACCESS ################

def fsdb_stats():
    """ A few stats about this database."""
    
    img_suff, gt_suff, pred_suff = [ app.config[k] for k in ('charter_img_suffix', 'gt_segfile_suffix', 'pred_segfile_suffix') ]
    all_charters = list(Path(app.config['fsdb_root']).glob('*/*/*/CH.cei.xml'))
    
    if app.config['crop']:
        charter_img_paths=list(Path(app.config['fsdb_root']).glob('*/*/*/*.seals.crops/*.{}'.format(img_suff)))
    else:
        charter_img_paths=list(Path(app.config['fsdb_root']).glob('*/*/*/*.{}'.format(img_suff)))

    current_state = [ (True, Path(lemmatize(p, suffix=img_suff, replacement=pred_suff )).exists(), Path(lemmatize(p, suffix=img_suff, replacement=gt_suff )).exists()  ) for p in charter_img_paths ]
    report = { "total_charters": len(all_charters), "total_images": len(current_state), "pred_count": len(list(itertools.filterfalse(lambda t: not t[1], current_state))), "gt_count": len(list(itertools.filterfalse(lambda t: not t[2], current_state))) }
    report['pred_ratio']=round(float(report['pred_count']/report['total_images']),2)
    report['gt_ratio']=round(float(report['gt_count']/report['total_images']),2)

    return report


def fsdb_search( archive_id:str, charter_img_id:str, suffix:str=None) -> Path:
    if suffix is None:
        suffix = app.config['charter_img_suffix']
    if app.config['crop']:
        file_paths=list(Path(app.config['fsdb_root']).glob('{}/*/*/*.seals.crops/{}.{}'.format(archive_id, charter_img_id, suffix)))
    else:
        file_paths=list(Path(app.config['fsdb_root']).glob('{}/*/*/{}.{}'.format(archive_id, charter_img_id, suffix)))
    if not file_paths:
        return None
    return file_paths[0]

def fsdb_write_img_metadata(data:dict, archive_id:str, charter_img_id:str, suffix=None):
    if suffix is None or suffix==app.config['charter_img_suffix']:
        return {}
    output_filename = fsdb_search( archive_id, charter_img_id )
    if output_filename is None:
        return {}
    output_filename = lemmatize( output_filename, suffix=app.config['charter_img_suffix'], replacement=suffix)
    returnValue, outputfile = {}, None
    try:
        outputfile = open(output_filename, 'w')
        print( json.dumps(data, indent=4), file=outputfile)
        outputfile.close()
        returnValue = {'filename': output_filename, 'size': Path(output_filename).stat().st_size }
    except (IOError) as e:
        outputfile.close()
    return returnValue

def fsdb_read_img_metadata(archive_id:str, charter_img_id:str, suffix=None):
    if suffix is None:
        return {}

    infile, returnValue = None, {}
    data_path = fsdb_search( archive_id, charter_img_id, suffix=suffix)
    if data_path is None:
        return {}
    try:
        infile = open(data_path, 'r') 
        returnValue = json.load( infile );
    except (IOError, FileNotFoundError) as e:
        pass
    finally:
        if infile is not None:
            infile.close();
    return returnValue;


def fsdb_write_flags( flag_data:dict, archive_id:str, charter_img_id:str):
    return fsdb_write_img_metadata( flag_data, archive_id, charter_img_id, suffix='flags.json')

def fsdb_update_flags(updates:dict, archive_id:str, charter_img_id:str):
    flag_data = fsdb_read_img_metadata( archive_id, charter_img_id, suffix='flags.json')
    flag_data.update( updates )
    print(f"fsdb_update_flags({updates}) -> {flag_data}")
    return fsdb_write_img_metadata( flag_data, archive_id, charter_img_id, suffix='flags.json')


def fsdb_read_flags( archive_id:str, charter_img_id:str):
    return fsdb_read_img_metadata( archive_id, charter_img_id, suffix='flags.json')

def fsdb_write_segmentation_file( page_data: dict, archive_id:str, charter_img_id: str)->dict:
    """
    Write segmentation data into a JSON file.

    Args:
        archive_id (str): archive name
        charter_img_id (str): charter atom id
        page_data (dict): a dictionary
            {'page_wh': [<width>, <height>],
             'lines': [{'centerline': [[x1,y1], ...], 'boundary': [[x1,y1], ...]}, ...] }
        charter_img_id: Image atom id.
    Returns:
        dict: if successful, an object with filename and size; otherwise an empty dictionary.

    """
    page_data.update( {
        "type": "centerlines",
        "text_direction": "horizontal-lr",
    })
    
    return fsdb_write_img_metadata( page_data, archive_id, charter_img_id, suffix=app.config['gt_segfile_suffix'])


def fsdb_read_segmentation_file(archive_id:str, charter_img_id: str, suffix: str ) -> dict:
    """
    Args:
        archive_id (str): archive name
        charter_img_id (str): charter atom id
        suffix (str): 'lines.gt.json' (GT) or 'lines.pred.json' (prediction).
    Returns:
        dict: a segmentation dictionary.
    """
    return fsdb_read_img_metadata(archive_id, charter_img_id, suffix)

def fsdb_get_archives() -> List[str]:
    """
    Get a list of all archive directories.

    Returns:
        List[str]: a list of archive names.
    """
    archives = list([ p.name for p in Path( app.config['fsdb_root']).glob('*') if p.is_dir() and re.match(r'[A-Z]{2}-[A-Za-z]+', p.name)])
    archives.append('COLLECTIONS')
    return sorted(archives)


def fsdb_get_charter_images(archive_id:str='') -> Tuple[str,dict]:
    """
    For given archive, get a map of all images, with their attributes.

    Args:
        archive_id (str): the name of an archive directory; if empty, the first archive in the list is used.
    Returns:
        Tuple[str,dict]: a pair with the archive id passed to the function, as well as a dictionary
            with image ids as keys and a dictionary of image attributes (filename, segmentation data, ...)
            as value. 
    """
    if not archive_id:
        archive_id = sorted([ p.name for p in Path( app.config['fsdb_root']).glob('*') if p.is_dir() ])[0]
    charter_images = []
    if app.config['crop']:
        charter_images = [ {'id': lemmatize(img.name, suffix=app.config['charter_img_suffix']), 'archive': archive_id, 'filename': str(img), 'gtsegfile': None} for img in Path(app.config['fsdb_root']).glob('{}/*/*/*.seals.crops/*.{}'.format( archive_id, app.config['charter_img_suffix'])) ]
    else:
        charter_images = [ {'id': lemmatize(img.name, suffix=app.config['charter_img_suffix']), 'archive': archive_id, 'filename': str(img), 'gtsegfile': None} for img in Path(app.config['fsdb_root']).glob('{}/*/*/*.{}'.format( archive_id, app.config['charter_img_suffix'])) ]

    for number, ch_img in enumerate(charter_images, start=1):
        filepath_stem = lemmatize( Path(ch_img['filename']), suffix=app.config['charter_img_suffix'] )
        ch_img['number']=number
        if app.config['crop']:
            ch_img['charter']=Path(ch_img['filename']).parent.parent.name
        else:
            ch_img['charter']=Path(ch_img['filename']).parent.name

        gt_seg_filename = '{}.{}'.format( filepath_stem, app.config['gt_segfile_suffix'])
        if Path( gt_seg_filename ).exists():
            ch_img['hasGTData']=True
        pred_seg_filename = '{}.{}'.format( filepath_stem, app.config['pred_segfile_suffix'] )
        
        if Path( pred_seg_filename ).exists():
            ch_img['hasPredData']=True
    
    return archive_id, charter_images


def fsdb_get_image(archive_id: str, charter_img_id:str):
    """
    Find an image from the given archive, given its id.

    Args:
        archive_id (str): the name of an archive directory.
        charter_img_id (str): the image id.
    Returns:
        bytes: an array of bytes.
    """
    charter_img_path = fsdb_search( archive_id, charter_img_id )
    if charter_img_path is None:
        return None
    try:
        data = open( charter_img_path, 'rb' ).read()
        return data
    except (IOError) as e:
        print("Could not open {}".format( charter_img_paths[0]))
        return None


#################### ROUTES ###############

@app.errorhandler(404)
def resource_not_found(e):
    return jsonify(error=str(e)), 404



@app.route('/')
def charters_choice():
    """ Display first charter of first archive
    """
    archive_id, charter_images = fsdb_get_charter_images()

    if not charter_images:
        abort(404, description="No charter images found for archive '{}'".format( archive_id ))
    charter_img_id = charter_images[0]['id']
    return redirect(f'/{archive_id}/{charter_img_id}')

@app.get('/archive')
def all_archives():
    archives = fsdb_get_archives()
    if not archives:
        abort(404, description="No archives found")
    return make_response( archives )


@app.route('/archive/<archive_id>')
def archive_charter_all_images(archive_id:str):
    _, charter_images = fsdb_get_charter_images(archive_id)

    if not charter_images:
        abort(404, description="No charter images found for archive '{}'".format( archive_id ))

    charter_img_id = charter_images[0]['id']
    return redirect(f'/{archive_id}/{charter_img_id}')

@app.get('/<archive_id>/<charter_img_id>')
def archive_charter_one_image( archive_id:str, charter_img_id:str):
    """ Display a charter image, as well as the list of charters.
    """
    archives = fsdb_get_archives()
    _, charter_images = fsdb_get_charter_images(archive_id)
    # ensure that image of interest is a the top
    item_of_interest_idx= list([ img['id'] for img in  charter_images]).index(charter_img_id)
    charter_img_filename = charter_images[item_of_interest_idx]['filename']
    charter_images = charter_images[item_of_interest_idx:]+charter_images[:item_of_interest_idx]

    if not charter_images:
        abort(404, description="No charter images found for archive '{}'".format( archive_id ))

    if charter_img_id not in [ img['id'] for img in charter_images]:
        abort(404, description="No charter image found with id='{}'".format( charter_img_id ))

    def get_scaling_factor( actual_width:int, max_width=app.config['max_width'] ):
        """ Ensure that image canvas is not too wide, for layout purpose """
        #return app.config['scaling_factor'] if img.size[0] <= max_width else max_width/img.size[0]
        return max_width/img.size[0]
    
    with Image.open( charter_img_filename, 'r') as img:
        display_size = [int(d*get_scaling_factor(img.size[0])) for d in img.size]
        return render_template(
                'charters.html', 
                archives=archives,
                archive_id=archive_id,
                charter_images=charter_images, 
                charter_img_id=charter_img_id, 
                charter_img_size=img.size,
                charter_filename=Path(charter_img_filename).name,
                display_size=display_size,
                fsdb_stats=fsdb_stats(),
                )

@app.get('/img/<archive_id>/<charter_img_id>')
def serve_img( archive_id:str, charter_img_id:str):
    image_bytes = fsdb_get_image(archive_id, charter_img_id)
    
    if image_bytes is not None:
        resp = make_response( image_bytes )
        resp.headers.set('Content-Type', 'image/jpeg')
        return resp
     
    abort(404, description="Could not find charter image {} in archive {}".format( charter_img_id, archive_id))


@app.post('/segdata/<archive_id>/<charter_img_id>')
def write_segmentation_data( archive_id:str, charter_img_id:str ):
    """Export segmentation annotation to disk.
    """
    segmentation_data = request.get_json()
    fsdb_update_flags({'baseline-offset': bool(len(segmentation_data['lines'][0]['baseline']))}, archive_id, charter_img_id)
    ok = fsdb_write_segmentation_file( segmentation_data, archive_id, charter_img_id )
    resp = make_response( ok )
    return resp

@app.get('/segdata/<archive_id>/<charter_img_id>')
def get_segmentation_gt( archive_id:str, charter_img_id:str):
    """ Import a mask generated by this application (for updates)
    """
    suffix = app.config['pred_segfile_suffix'] if request.args.get( 'segtype' ) == 'pred' else app.config['gt_segfile_suffix']
    segmentation_data = fsdb_read_segmentation_file( archive_id, charter_img_id, suffix )
    return make_response( segmentation_data )


@app.post('/flags/<archive_id>/<charter_img_id>')
def write_flags( archive_id:str, charter_img_id:str ):
    """Export segmentation flags to disk.
    """
    flag_data = request.get_json()
    ok = fsdb_write_flags( flag_data, archive_id, charter_img_id )
    resp = make_response( ok )
    return resp

@app.get('/flags/<archive_id>/<charter_img_id>')
def get_flags( archive_id:str, charter_img_id:str):
    """ Import segmentation flags
    """
    flag_data = fsdb_read_flags( archive_id, charter_img_id )
    # note: since data read from json file, no need to jsonify
    return make_response( flag_data )


@app.get('/appconfig')
def get_config():
    config_data = json.dumps({ k.replace('gui_tool_', ''):v for k,v in app.config.items() if 'gui_tool_' in k } )
    return make_response( config_data )


@app.post('/appconfig')
def write_config():
    """Export segmentation flags to disk.
    """
    config_data = request.get_json()
    stored = {}
    for k,v in config_data.items():
        if 'gui_tool_'+k in app.config:
            app.config['gui_tool_'+k]=v
            stored = { k:v for k,v in app.config.items() if 'gui_tool_' in k }
    resp = make_response(stored)
    return resp

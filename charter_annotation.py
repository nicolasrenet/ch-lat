"""
A Flask interface to read and write segmentation data on locally stored charters.
"""
from flask import Flask
from flask import render_template, request, jsonify, make_response, redirect, url_for
from pathlib import Path
import re
import json
import base64
from PIL import Image

# TODO:
#

app = Flask(__name__)

# SETTINGS
settings = {
        'scaling_factor': .5,
        'charter_img_suffix': 'img.jpg',
        'gt_segfile_suffix': 'lines.gt.json',
        'pred_segfile_suffix': 'lines.pred.json',
        'fsdb_root': '/home/nicolas/tmp/data/fsdb_work/fsdb_full_text_sample_1000',
}




def lemmatize( p:Path):
    return re.sub(r'\..+', '',  p.name)


########## DATA ACCESS ################

def fsdb_write_segmentation_file( page_data: dict, charter_img_id: str)->dict:
    """
    Write segmentation data into a JSON file.

    Args:
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
    output_filename = '{}.lines.gt.json'.format(charter_img_id)
    returnValue = {}
    outputfile = None
    try:
        outputfile = open(output_filename, 'w')
        print( json.dumps(page_data, indent=4), file=outputfile)
        outputfile.close()
        returnValue = {'filename': output_filename, 'size': Path(output_filename).stat().st_size }
    except (IOError) as e:
        outputfile.close()
    return returnValue


def fsdb_read_segmentation_file( segmentation_file: str ) -> dict:
    """
    Args:
        segmentation_file (str): a JSON file, Kraken-style
    Returns:
        dict: a segmentation dictionary.
    """
    seginfile = None
    returnValue = {}
    try:
        seginfile = open(segmentation_file, 'r') 
        returnValue = json.load( seginfile );
    except (IOError, FileNotFoundError) as e:
        pass
    finally:
        if seginfile is not None:
            seginfile.close();
    return returnValue;


# Listing all charter images, with their existing segmentation meta-data
def fsdb_get_charter_images(archive_id):

    charter_images = { lemmatize(img):{'archive': archive_id, 'filename': str(img), 'gtsegfile': None} for img in Path(settings['fsdb_root']).glob('{}/*/*/*.{}'.format( archive_id, settings['charter_img_suffix'])) }

    for md5id in charter_images:
        charter_images[md5id]['charter']=Path(charter_images[md5id]['filename']).parent.name
        gt_seg_filename = '{}.{}'.format( md5id, settings['gt_segfile_suffix'])
        if Path( gt_seg_filename ).exists():
            charter_images[md5id]['hasGTData']=True
        pred_seg_filename = '{}.{}'.format( md5id, settings['pred_segfile_suffix'] )
        if Path( pred_seg_filename ).exists():
            charter_images[md5id]['hasPredData']=True
    return charter_images


def fsdb_get_image(archive_id: str, charter_img_id:str):
    img_data=None
    charter_img_paths = list(Path(settings['fsdb_root']).glob('{}/*/*/{}.{}'.format(archive_id, charter_img_id, settings['charter_img_suffix'])))
    if not charter_img_paths:
        return None
    try:
        data = open( charter_img_paths[0], 'rb' ).read()
        return data
    except (IOError) as e:
        print("Could not open {}".format( charter_img_paths[0]))
        return None


#################### ROUTES ###############

@app.route('/')
def charters_choice():
    """ Display first charter in the list.
    """
    current = list(fsdb_get_charter_images().keys())[0]
    return redirect(f'/{current}')

@app.route('/archive/<archive_id>')
def charters_archive_list(archive_id:str):
    print('charters_archive_list()')
    current = list(fsdb_get_charter_images(archive_id).keys())[0]
    return redirect(f'/{archive_id}/{current}')

@app.get('/<archive_id>/<charter_img_id>')
def charter_pick( archive_id:str, charter_img_id:str):
    """ Display a charter image, as well as the list of charters.
    """
    charter_images = fsdb_get_charter_images(archive_id)
    with Image.open( charter_images[charter_img_id]['filename']) as img:
        display_size = [int(d*settings['scaling_factor']) for d in img.size]
        return render_template(
                'charters.html', 
                charter_images=charter_images, 
                charter_img_id=charter_img_id, 
                display_size=display_size
                )

@app.get('/img/<archive_id>/<charter_img_id>')
def serve_img( archive_id:str, charter_img_id:str):
    print('serve_img({}, {}'.format( archive_id, charter_img_id ))
    image_bytes = fsdb_get_image(archive_id, charter_img_id)
    if image_bytes is not None:
        resp = make_response( image_bytes )
        resp.headers.set('Content-Type', 'image/jpeg')
        return resp
    return make_response(404)






@app.post('/export/<charter_img_id>')
def record_segmentation_data( charter_img_id:str ):
    """Export segmentation annotation to disk.
    """
    segmentation_data = request.get_json()
    ok = fsdb_write_segmentation_file( segmentation_data, charter_img_id )
    resp = make_response( ok )
    return resp

@app.get('/import/<charter_img_id>')
def get_segmentation_gt( charter_img_id:str ):
    """ Import a mask generated by this application (for updates)
    """
    suffix = settings['pred_segfile_suffix'] if request.args.get( 'segtype' ) == 'pred' else settings['gt_segfile_suffix']
    segmentation_data = fsdb_read_segmentation_file( '{}.{}'.format( charter_img_id, suffix ))
    print(segmentation_data)
    return make_response( segmentation_data )



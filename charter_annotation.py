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
import sys
import statistics

# TODO:
# - adapt font-size to length of transcription
# - 

sys.path.append('.')
from fsdb import Fsdb, lemmatize

app = Flask(__name__)


# SETTINGS
app.config.update(
    scaling_factor= .7,
    max_width=1200,
    charter_img_suffix='img.jpg',
    gt_seg_suffix='lines.gt.json',
    gt_htr_suffix='htr.gt.json',
    pregt_htr_suffix='htr.pregt.json',
    pred_seg_suffix='lines.pred.json',
    fsdb_root='/home/nicolas/tmp/data/fsdb_work/fsdb_full_text_sample_1000',
    json_validate=True,
    schema_path='static/lines_schema.json',
    crop=False,
    flat=False,
    polygon_attribute='coords',
    gui_tool_smoothing=True,
    gui_tool_dataType='gt',
    gui_tool_alpha = 0.5,
    gui_tool_strokeWidth=6,
    gui_tool_overlapHandling=False,
    gui_tool_overlapBuffer=2,
    gui_tool_overlapScope=3,
)


app.config.from_prefixed_env()

print(app.config)


fsdb = Fsdb( app.config )


#################### ROUTES ###############

@app.errorhandler(404)
def resource_not_found(e):
    return jsonify(error=str(e)), 404



@app.route('/segmentation')
def charters_choice():
    """ Display first charter of first archive
    """
    archive_id, charter_images = fsdb.get_charter_images()

    if not charter_images:
        abort(404, description="No charter images found for archive '{}'".format( archive_id ))
    charter_img_id = charter_images[0]['id']
    return redirect(f'/{archive_id}/{charter_img_id}')

@app.route('/')
def align_choice():
    return redirect(f'/segmentation')


@app.get('/archive')
def all_archives():
    archives = fsdb.get_archives()
    if not archives:
        abort(404, description="No archives found")
    return make_response( archives )


@app.route('/archive/<archive_id>')
def archive_charter_all_images(archive_id:str):
    _, charter_images = fsdb.get_charter_images(archive_id)

    if not charter_images:
        abort(404, description="No charter images found for archive '{}'".format( archive_id ))

    charter_img_id = charter_images[0]['id']
    return redirect(f'/{archive_id}/{charter_img_id}')

@app.get('/<archive_id>/<charter_img_id>')
def archive_charter_one_image( archive_id:str, charter_img_id:str):
    """ Display a charter image, as well as the list of charters.
    """
    archives = fsdb.get_archives()
    _, charter_images = fsdb.get_charter_images(archive_id)
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
        return max_width/img.size[0]
    
    with Image.open( charter_img_filename, 'r') as img:
        display_size = [int(d*get_scaling_factor(img.size[0])) for d in img.size]
        return render_template(
                'charters.html' if not app.config['flat'] else 'charters_flat.html', 
                archives=archives,
                archive_id=archive_id,
                charter_images=charter_images, 
                charter_img_id=charter_img_id, 
                charter_img_size=img.size,
                charter_filename=Path(charter_img_filename).name,
                display_size=display_size,
                fsdb_stats=fsdb.stats(),
                )

@app.get('/img/<archive_id>/<charter_img_id>')
def serve_img( archive_id:str, charter_img_id:str):
    image_bytes = fsdb.get_image(archive_id, charter_img_id)
    
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
    ok = fsdb.write_segmentation_file( segmentation_data, archive_id, charter_img_id )
    resp = make_response( ok )
    return resp

@app.get('/segdata/<archive_id>/<charter_img_id>')
def get_segmentation_gt( archive_id:str, charter_img_id:str):
    """ Import a mask generated by this application (for updates)
    """
    suffix = app.config['pred_seg_suffix'] if request.args.get( 'segtype' ) == 'pred' else app.config['gt_seg_suffix']
    segmentation_data = fsdb.read_segmentation_file( archive_id, charter_img_id, suffix )
    return make_response( segmentation_data )


@app.post('/flags/<archive_id>/<charter_img_id>')
def write_flags( archive_id:str, charter_img_id:str ):
    """Export segmentation flags to disk.
    """
    flag_data = request.get_json()
    ok = fsdb.write_flags( flag_data, archive_id, charter_img_id )
    resp = make_response( ok )
    return resp

@app.get('/flags/<archive_id>/<charter_img_id>')
def get_flags( archive_id:str, charter_img_id:str):
    """ Import segmentation flags
    """
    flag_data = fsdb.read_flags( archive_id, charter_img_id )
    # note: since data read from json file, no need to jsonify
    return make_response( flag_data )


@app.get('/alignment')
def all_lines():
    # retrieve all existing charter ids (for browsing)
    charter_htr_gts = fsdb.search('*', '*', suffix=app.config['pregt_htr_suffix'])
    if not charter_htr_gts:
        abort(404, description="Failed to retrieve charters ids.")
    ch_id = lemmatize( charter_htr_gts[0].name, suffix=app.config['pregt_htr_suffix'] )
    return redirect(f'/alignment/{ch_id}')




@app.get('/alignment/<charter_img_id>')
def get_lines( charter_img_id:str):
    
    charter_htr_gts = fsdb.search('*', '*', suffix=app.config['pregt_htr_suffix'])
    if not charter_htr_gts:
        abort(404, description="Failed to retrieve charters ids.")
    charter_ids = [ {'number': nbr, 
                     'id': lemmatize(img_id.name, suffix=app.config['pregt_htr_suffix']),
                     'hasGTData': Path( lemmatize( img_id, suffix=app.config['pregt_htr_suffix'], replacement=app.config['gt_htr_suffix'])).exists(),
                     } for nbr, img_id in enumerate(charter_htr_gts)]

    item_of_interest_idx=[ ch['id'] for ch in charter_ids ].index(charter_img_id)
    charter_ids = charter_ids[item_of_interest_idx:]+charter_ids[:item_of_interest_idx] 
    if not charter_ids:
        abort(404, description="No charter images found for archive '{}'".format( archive_id ))

    if charter_img_id not in [ ch['id'] for ch in charter_ids]:
        abort(404, description="No charter image found with id='{}'".format( charter_img_id ))

    return render_template(
            "alignment.html", 
            fsdb_stats=fsdb.stats(),
            charter_img_id=charter_img_id,
            charter_ids=charter_ids,
            )

@app.get('/lines/<charter_img_id>')
def get_line_items( charter_img_id:str):
    data_type = request.args.get('dataType') if 'dataType' in request.args else 'pregt'
    line_data, line_max_width = fsdb.read_lines( charter_img_id, data_type, polygon_key=app.config['polygon_attribute'])

    if not line_data:
        abort(404, description="No line metadata found for charter '{}'".format( charter_img_id ))

    text_avg_length = statistics.mean( [ len(ld[1]) for ld in line_data] )
    text_size='medium'
    if text_avg_length > 180:
        text_size='xsmall' if text_avg_length > 210 else 'small'

    line_data = [ ldt + [ ldt[3] * app.config['max_width']/line_max_width ] for ldt in line_data ]
    
    return render_template(
            "line_items.html", 
            charter_img_id=charter_img_id,
            line_data=line_data,
            text_size=text_size,
            )


@app.post('/lines/<charter_img_id>')
def write_line_transcriptions( charter_img_id: str):
    line_transcriptions = request.get_json()
    ok=fsdb.write_line_transcriptions( line_transcriptions, charter_img_id )
    resp = make_response( ok )
    return resp


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



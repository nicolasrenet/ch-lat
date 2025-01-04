from flask import Flask
from flask import render_template, request, jsonify, make_response, redirect, url_for
from pathlib import Path
import re
import json
from PIL import Image

# TODO:
#
#   + image W,H in segmentation data

app = Flask(__name__)

def lemmatize( p:Path):
    return re.sub(r'\..+', '',  p.name)

def write_segmentation_file( page_data: dict, charter_id: str):
    """
    Args:
        segdata (dict): a dictionary
            {'page_wh': [<width>, <height>],
             'lines': [{'baseline': [[x1,y1], ...], 'boundary': [[x1,y1], ...]}, ...] }

    """
    page_data.update( {
        "type": "baselines",
        "text_direction": "horizontal-lr",
    })
    output_filename = '{}.lines.gt.json'.format(charter_id)
    returnValue = {}
    try:
        outputfile = open(output_filename, 'w')
        print( json.dumps(page_data, indent=4), file=outputfile)
        outputfile.close()
        returnValue = {'filename': output_filename, 'size': Path(output_filename).stat().st_size }
    except IOError as e:
        outputfile.close()
        returnValue = {'Abort': str(e) }
    finally:
        return returnValue

SCALING_FACTOR = .5
charters = { lemmatize(p):{'filename': str(p)} for p in Path('.').glob('*.img.jpg') }

@app.route('/')
def charters_choice():
    current = list(charters.keys())[0]
    return redirect(f'/{current}')

@app.route('/<charter_id>')
def charter_pick( charter_id:str):
#    charters = { lemmatize(p):{'filename': str(p)} for p in Path('.').glob('*.img.jpg') }
    with Image.open( charters[charter_id]['filename']) as img:
        #print([d*scaling_factor for d in img.size])
        return render_template(
                'charters.html', 
                charters=charters, 
                charter_id=charter_id, 
                charter_size=[d*SCALING_FACTOR for d in img.size])


@app.post('/export/<charter_id>')
def record_segmentation_data( charter_id:str ):
    segmentation_data = request.get_json()
    ok = write_segmentation_file( segmentation_data, charter_id )
    resp = make_response( ok )
    return resp

@app.get('/import/<charter_id>')
def apply_segmentation_data( charter_id:str ):
    segmentation_data = read_segmentation_file( '{}.lines.pred.json'.format( charter_id ))


# GET: 
    # collection: display list of charters (from disk)
    # element: display charter for annotation


# POST: create charter annotation

# PUT: update charter annotation

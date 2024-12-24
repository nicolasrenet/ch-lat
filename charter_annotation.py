from flask import Flask
from flask import render_template
from pathlib import Path
import re

app = Flask(__name__)


@app.route('/')
def charter_annotate():

    charters = [ {'filename': str(p), 'href': 'charter/{}'.format( re.sub(r'\..+', '', p.name))} for p in Path('.').glob('*.img.jpg')]

    return render_template('charters.html', charters=charters)

 


# GET: 
    # collection: display list of charters (from disk)
    # element: display charter for annotation


# POST: create charter annotation

# PUT: update charter annotation

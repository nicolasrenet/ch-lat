from flask import Flask
from flask import render_template
from pathlib import Path
import re

app = Flask(__name__)

def lemmatize( p:Path):
    return re.sub(r'\..+', '',  p.name)

@app.route('/')
def charters_choice():
    charters = { lemmatize(p):{'filename': str(p)} for p in Path('.').glob('*.img.jpg') }
    return render_template('charters.html', charters=charters, current=list(charters.keys())[0])

@app.route('/<charter_id>')
def charter_pick( charter_id:str):
    charters = { lemmatize(p):{'filename': str(p)} for p in Path('.').glob('*.img.jpg') }
    return render_template('charters.html', charters=charters, current=charter_id)




# GET: 
    # collection: display list of charters (from disk)
    # element: display charter for annotation


# POST: create charter annotation

# PUT: update charter annotation

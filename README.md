# GT Alignment toolchain

## Charter line annotation tool


A JS+Flask GUI for annotating charter lines, that runs on top of a FSDB-like tree. 

### Startup

```bash
FLASK_crop=1 flask --app charter_annotation run
```
See `charter_annotation.py` for setting the root of the FSDB tree.

### Create or correct a line segmentation

```
http://localhost:5000/segmentation

```
![](doc/segmentation_screenshot.png)

### Correct a line-based transcription


```
http://localhost:5000
```

![](doc/alignment_screenshot.png)


## Alignment script

A hack that uses a passable HTR in order to align existing full-paragraph GT transcriptions with an existing segmentation.

### Syntax 

```bash
python3 gt_alignment.py [options]
```

where the options are as follows:

```bash
-appname=<class 'str'>  Default 'gt_alignment' . Passed 'gt_alignment'
-model_path=<class 'str'>  Default '/tmp/default_model.mlmodel' . Passed '/tmp/default_model.mlmodel'
-img_paths=<class 'set'>  Default set() . Passed set()
-heuristics_on=<class 'int'>  Default 1 . Passed 1
-gt_seg_suffix=<class 'str'>  Default 'lines.gt.json' . Passed 'lines.gt.json'
-pregt_htr_suffix=<class 'str'>  Default 'htr.pregt.json' . Passed 'htr.pregt.json'
-tenor_suffix=<class 'str'>  Default 'revised_tenor.txt' . Passed 'revised_tenor.txt'
-help=<class 'bool'> Print help and exit. Default False . Passed False
-bash_autocomplete=<class 'bool'> Print a set of bash commands that enable autocomplete for current program. Default False . Passed False
-h=<class 'bool'> Print help and exit Default False . Passed True
-v=<class 'int'> Set verbosity level. Default 1 . Passed 1
```

### Examples

Aligning GT for explicit image files:


```bash
export PYTHONPATH=/home/nicolas/graz/htr/vre/ddpa_htr; ~/graz/htr/hw_gt_alignment/gt_alignment.py -model_path $PYTHONPATH/models/default.mlmodel -img_paths CH-StaASG/b54cf369ddc02d3d3201184dc49dfb51/b7e63381574d0bf613d337b453ea6758/3d87e370bb72595c8d65265bd765b695.seals.crops/3d87e370bb72595c8d65265bd765b695.Wr_OldText.3.img.jpg
```

Aligning GT for all images that have valid tenor file:

```bash
(for img in $(find . -name "*OldText*.img.jpg"); do 
	test -f "${img%.img.jpg}.revised_tenor.txt" && echo $img ; 
done ) | xargs ~/graz/htr/hw_gt_alignment/gt_alignment.py -model_path $PYTHONPATH/model_save.mlmodel.best -img_paths
```

Resulting `*.htr.gt.json` file can be reviewed and corrected with the line transcription viewer above.

## Running in Docker

Build the container:

```bash
sudo docker image rm alignment-flask;  sudo docker build --tag alignment-flask .
```

Run:

```bash
sudo docker run -v /home/nicolas/tmp/data/fsdb_work/fsdb_full_text_sample_1000:/fsdb_root --network host --rm -it --env-file .env alignment-flask
```


# GT Alignment toolchain

## Charter line annotation tool


A JS+Flask GUI for annotating charter lines, that runs on top of a FSDB-like tree.


### How to use

```bash
FLASK_crop=1 flask --app charter_annotation run
```
See `charter_annotation.py` for setting the root of the FSDB tree.


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
-help=<class 'bool'> Print help and exit. Default False . Passed False
-bash_autocomplete=<class 'bool'> Print a set of bash commands that enable autocomplete for current program. Default False . Passed False
-h=<class 'bool'> Print help and exit Default False . Passed True
-v=<class 'int'> Set verbosity level. Default 1 . Passed 1
```

### Example

```bash
(for img in $(find . -name "*OldText*.img.jpg"); do 
	test -f "${img%.img.jpg}.revised_tenor.txt" && echo $img ; 
done ) | xargs ~/graz/htr/hw_gt_alignment/gt_alignment.py -model_path $PYTHONPATH/model_save.mlmodel.best -img_paths
```



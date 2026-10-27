# GT Alignment toolchain

## 1. Charter line annotation tool


A JS+Flask GUI for annotating charters, either for line segmentation or HTR ground-truthing.

### 1.1 Startup

#### Option 1. On top of an FSDB deep tree
```bash
FLASK_fsdb_root='/home/nicolas/fsdb' flask --app charter_annotation run -p 5001
```

By default, the entire charter image is used, with the regions read from the initial line segmentation file (or an image-wide region if no such file is provided). In order to restrict the scope to existing `OldText` crops, use the `FLASK_crop=1` at startup. At export time, the resulting annotation file is a crop-wide file.

#### Option 2. Read and write from a flat directory

No FSDB compliance needed: just ensure that filenames use a consistent prefix/suffix pattern.

```bash
FLASK_flat=1 FLASK_fsdb_root='/home/nicolas/fsdb' flask --app charter_annotation run -p 5001
```

### 1.2 Default suffixes


| Data | Workflow | Flask option | Prefix |
|:-----|:---------|:-------------|:-------|
| Line segmentation predictions | line annotation input | `FLASK_pred_seg_suffix` | `lines.pred.json`|
| Line segmentation data GT | line annotation input/output | `FLASK_gt_seg_suffix` | `lines.gt.json`|
| HTR predictions | HTR annotation input | `FLASK_pregt_htr_suffix` | `htr.pregt.json`|
| HTR ground-truth | HTR annotation input/output | `FLASK_gt_htr_suffix` | `htr.gt.json` |

### 1.3 Other options


See `charter_annotation.py` for the following flags:

+ `FLASK_json_validate`: JSON validation
+ `FLASK_schema_path`: JSON schema (default: `static/lines_schema.json`)

### 1.4 Annotation modes

#### Segmentation GT: Create or correct a line segmentation

```
http://localhost:5000/segmentation

```
![](doc/segmentation_screenshot.png)

Limitations: regions can be read and modified or deleted, but they cannot be created from scratch.
They are typically read from an existing segmentation prototype.

#### HTR ground-truth: review/correct a line-based transcription

```
http://localhost:5000/alignment
```

![](doc/alignment_screenshot.png)

DiDip-style transcription annotations of the kind `[<what you read>|what you see]` (including their more concise syntactic variations eg. `<what you read>|<what you see>`, `[<what you read>`...) are automatically highlighted:

![](doc/double_transcription.png)


## 2. Auxiliary scripts


### 2.1 Long and short-form transcriptions from a single file: `compile_transcription.py`

**Input**: a single annotation file (JSON or PageXML) that stores both the expanded and abbreviated form of the transcription. Eg.

```
"[et|% Rogatis In [Cuius|Cui Rei [testimonio|testio%m plenius [presentes|p%ntes [litteras|lra%s [dedimus|dedim% [nostro|n%ro [pendenti|pend%nti"
```

**Output**: 

+ `*.exp.json`: expanded form: `"et Rogatis In Cuius Rei testimonio plenius presentes litteras dedimus nostro pendenti"`
+ `*.abr.json`: abbreviated form: `"% Rogatis In Cui Rei testio%m plenius p%ntes lra%s dedim% n%ro pend%nti"`

Although it is better practice to use DiDip-flavored JSON or PageXML as input formats, the script can be used with any file that has a consistent pattern for a line transcription.

#### Syntax

```bash
Usage: compile_transcription.py [-h] [--abbreviate] [--expand] [--expanded_suffix EXPANDED_SUFFIX] [--abbreviated_suffix ABBREVIATED_SUFFIX]
                       [--line_pattern LINE_PATTERN] [--input_format INPUT_FORMAT] [--verbosity {0,1,2}]
                       input_file

positional arguments:
  input_file

options:
  -h, --help            show this help message and exit
  --abbreviate          By default, the script generate both flavours of outputs; with this option, the abbreviated files are created, but their
                        expanded counterpart is not, unless the '--expand' option is used. (default: False)
  --expand              By default, the script generate both flavours of outputs; with this option, the expanded files are created, but their
                        abbreviated counterpart is not, unless the '--abbreviate' option is used. (default: False)
  --expanded_suffix EXPANDED_SUFFIX
                        Suffix to be added to the expanded transcription before the '.json' suffix. (default: .exp)
  --abbreviated_suffix ABBREVIATED_SUFFIX
                        Suffix to be added to the abbreviated transcription before the '.json' suffix. (default: .abr)
  --line_pattern LINE_PATTERN
                        A custom line pattern to isolate relevant part of the transcription line. (default: (^\s*"text":\s+")([^"]+)(".*)$)
  --input_format INPUT_FORMAT
                        File input format. (default: json)
  --verbosity {0,1,2}   Verbosity: 0=ERROR, 1=INFO, 2=DEBUG (default: 1)
```

#### Example

Generate both expanded and abbreviated forms:

```bash
./split_corpus.py 4574a41d2f834e6b2e807f96d82cddb3.htr.gt.json
```

Generate only the short-form transcription:

```bash
./split_corpus.py --abbreviate 4574a41d2f834e6b2e807f96d82cddb3.htr.gt.json
```

### 2.2 Aligning full-paragraph transcriptions with segmentation: `gt_alignemnt.py`

A hack that uses a passable HTR in order to align existing full-paragraph GT transcriptions with an existing segmentation.

#### Syntax 

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

#### Examples

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

## 3. Running in Docker

Build the container:

```bash
sudo docker image rm ch-lat;  sudo docker build --tag ch-lat .
```

Run:

```bash
sudo docker run -v /tmp/fsdb_full_text_sample_100:/fsdb_root --rm -it --env-file ./env ch-lat
```


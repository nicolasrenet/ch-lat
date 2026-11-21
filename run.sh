#!/bin/bash

USAGE="$0 [-f|--flat [0/1]] [h|--help] [(-i|--charter_img_suffix) <suf> ] [(-s|--pred-seg-suffix) <suf>] [(-S|--gt-seg-suffix) <suf>] [(-t|--pregt-htr-suffix) <suf>] [(-T|--gt-htr-suffix) <suf>] [<source directory>]"

TEMP=$(getopt -o 'hf::i:s:S:t:T:' --long 'help,flat::,charter-img-suffix:,pred-seg-suffix:,gt-seg-suffix:,pregt-htr-suffix:,gt-htr_suffix:', -n "$0" -- "$@")

if [ $? -ne 0 ]; then
	echo "Exit..." >&2
	exit 1
fi

eval set -- "$TEMP"
unset TEMP

export FLASK_flat=1
export FLASK_charter_img_suffix='img.jpg'
export FLASK_pred_seg_suffix='lines.pred.json'
export FLASK_gt_seg_suffix='lines.gt.json'
export FLASK_pregt_htr_suffix='htr.pregt.json'
export FLASK_gt_htr_suffix='htr.gt.json'
export FLASK_fsdb_root='/home/nicolas/tmp/data/transcriptions_johannes'

while true; do
	case "$1" in
		'--flat')
			case "$2" in
				'')
					FLASK_flat=1
				;;
				*)
					FLASK_flat=$2
				;;
			esac
			shift 2
			continue
		;;
		'--charter-img-suffix')
			FLASK_charter_img_suffix=$2
			shift 2
			continue
		;;
		'--pred-seg-suffix')
			FLASK_pred_seg_suffix=$2
			shift 2
			continue
		;;
		'--gt-seg-suffix')
			FLASK_gt_seg_suffix=$2
			shift 2
			continue
		;;
		'--pregt-htr-suffix')
			FLASK_pregt_htr_suffix=$2
			shift 2
			continue
		;;
		'--gt-htr-suffix')
			FLASK_gt_htr_suffix=$2
			shift 2
			continue
		;;
		'-h'|'--help')
			echo $USAGE
			exit 0
		;;
		'--')
			shift
			echo $USAGE
			break
		;;
		*)
			echo 'Internal error'
			exit 1
		;;
	esac
done

if [[ "$#" > 0 ]]; then
	FLASK_fsdb_root=$1
fi

echo fsdb_root=$FLASK_fsdb_root



flask --app charter_annotation run -p 5001

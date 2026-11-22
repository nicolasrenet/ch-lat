#!/bin/bash
# NPR, 11/2026
#
# A launch script for Ch-Lat

display_help() {
cat << EOF
NAME
	$0 - Ch-Lat launch script.

SYNOPSIS
	$0 [options] <source directory>

OPTIONS
	-f, --flat [ 0/1 ]
		Work on a flat tree, not a deep, FSDB-compliant directory.
	-h, --help 
		Display help text and exit.
	-i, --charter-img-suffix <suffix>
		Suffix of charter images (i.e. part of the name that is _not_ shared with label files).
	-s, --pred-seg-suffix <suffix>
		Suffix of predicted segmentation labels (read-only).
	-S, --gt-seg-suffix <suffix>
		Suffix of revised segmentation labels (writeable).
	-t, --pregt-htr-suffix <suffix>
		Suffix of prototype transcription labels (read-only).
	-T, --gt-htr-suffix <suffix>]
		Suffix of revised transcription labels (writeable)
	-c, --check
		Check that current suffixes match a set of existing images and labels.
	-m, --mode (segmentation|alignment)
		Default mode for root URL ('alignment' is default).
EOF
}


TEMP=$(getopt -o 'hf::i:s:S:t:T:cm:g:' --long 'help,flat::,charter-img-suffix:,pred-seg-suffix:,gt-seg-suffix:,pregt-htr-suffix:,gt-htr-suffix:,check,mode:,flag:', -n "$0" -- "$@")

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
export FLASK_flag_suffix='flag.json'
export FLASK_default_feature='alignment'
export FLASK_fsdb_root='/home/nicolas/tmp/data/transcriptions_johannes'

export check_only=0

while true; do
	case "$1" in
		'-f'|'--flat')
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
		'-i'|'--charter-img-suffix')
			FLASK_charter_img_suffix=$2
			shift 2
			continue
		;;
		'-s'|'--pred-seg-suffix')
			FLASK_pred_seg_suffix=$2
			shift 2
			continue
		;;
		'-S'|'--gt-seg-suffix')
			FLASK_gt_seg_suffix=$2
			shift 2
			continue
		;;
		'-t'|'--pregt-htr-suffix')
			FLASK_pregt_htr_suffix=$2
			shift 2
			continue
		;;
		'-T'|'--gt-htr-suffix')
			FLASK_gt_htr_suffix=$2
			shift 2
			continue
		;;
		'-g'|'--flag')
			FLASK_flag_suffix=$2
			shift 2
			continue
		;;
		'-m'|'--mode')
			FLASK_default_feature=$2
			shift 2
			continue
		;;
		'-c'|'--check')
			shift 1
			check_only=1
			continue
		;;
		'-h'|'--help')
			shift 1
			display_help
			exit 0
		;;
		'--')
			shift
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


if [[ "$check_only" -eq 1 ]]; then
	echo "To be implemented."
	exit 0
fi


flask --app charter_annotation run -p 5001

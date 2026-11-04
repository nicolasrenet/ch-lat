#!/bin/bash

USAGE="$0 [-fsdb--fsdb] [<source directory>]"

SOURCE='/home/nicolas/tmp/data/transcriptions_johannes'
FLAT=1

if [[ $# -gt 0 ]]; then
	if [[ "$1" == "--fsdb" || "$1" == "-fsdb" ]]; then
		FLAT=0
		if [[ "$#" -gt 1 ]]; then
			SOURCE=$2
		else
			echo "No source folder argument: using default location (${SOURCE}).";
		fi
	elif [[ -d "$1" ]]; then
		SOURCE=$1
	fi
else
	echo "No source folder argument: using default location (${SOURCE}).";
fi


FLASK_flat=${FLAT} FLASK_fsdb_root=${SOURCE} flask --app charter_annotation run -p 5001

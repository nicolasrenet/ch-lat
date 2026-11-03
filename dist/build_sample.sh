#!/bin/bash
#
# Build a random sample of image+transcription pairs from the given source

USAGE="$0 <source directory> [ <number of items> ]"

choose () 
{ 
    FUNCUSE="USAGE: choose <number of items>";
    if [[ $# -lt 1 ]]; then
        echo "$FUNCUSE";
        return -1;
    fi;
    cat | shuf | head -$1
}

if [[ $# -lt 1 ]]; then echo $USAGE ; exit ; fi 

SOURCE=$1
ZIPPATH=./samples.zip
ZIPDIR=./samples

test -d "${ZIPDIR}" || mkdir $ZIPDIR
test -f "${ZIPPATH}" && rm -f $ZIPPATH
rm -f $ZIPDIR/*

n=5
if [[ $# -gt 1 ]]; then
	n=$2
fi

for gt in $(ls $SOURCE/*.htr.gt.json | choose ${n}); do
	rsync -Lav $gt ${gt%.gt.json}.pregt.json ${gt%.htr.gt.json}.img.jpg $ZIPDIR/;
done
zip -r $ZIPPATH $ZIPDIR
ls -l $ZIPPATH
unzip -l $ZIPPATH


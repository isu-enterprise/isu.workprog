#!/bin/bash

echo "Processing $1"
xml=$1.xml
pdftohtml -c -s -xml -i $1 $xml
if python syllabus.py $xml; then
    echo "Success"
else
    echo "Error"
    echo "See log file $xml.log"
fi
# rm -f $xml

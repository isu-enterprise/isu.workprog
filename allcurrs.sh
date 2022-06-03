#!/bin/bash

cirrs="../cirriculums/"

for file in $cirrs*.xls
do
    echo Processing $file
    python curriculum.py $file
done

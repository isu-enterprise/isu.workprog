#!/bin/bash

currs="../curriculums/"

for file in $currs*.xls
do
    echo Processing $file
    python curriculum.py $file
done

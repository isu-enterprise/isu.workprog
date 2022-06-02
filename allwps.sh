#!/bin/bash


# execute `process` once for each file
find $1 -name '*.pdf' -exec ./proc_wp.sh {} \;

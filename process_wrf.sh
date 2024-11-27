#!/bin/bash

# Input files
D04_FILE=$1
D05_FILE=$2

#
cdo -expr,'M=sqrt((U*U)+(V*V));'  -intlevel,80 -selvar,U,V $D04_FILE foo.nc
# 182x215
#cdo -expr,'M=sqrt((U*U)+(V*V));' -intlevel,80 -selvar,U,V -selindexbox,10,172,10,105 $D05_FILE d05_final.nc
# 226 x 199
cdo -expr,'M=sqrt((U*U)+(V*V));' -selvar,U,V -intlevel,80 -selindexbox,10,216,10,189 $D05_FILE d05_final.nc

cdo remapdis,d05_final.nc foo.nc d04_final.nc



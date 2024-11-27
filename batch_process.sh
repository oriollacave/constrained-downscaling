#!/bin/bash

# Directories
INPUT_DIR="data/1394741"
OUTPUT_DIR="output"
TRAIN_DIR="$OUTPUT_DIR/train"
VAL_DIR="$OUTPUT_DIR/val"
TEST_DIR="$OUTPUT_DIR/test"
rm -fr output/*

# Create output directories
mkdir -p $TRAIN_DIR $VAL_DIR $TEST_DIR

# Split logic
declare -a SUBFOLDERS=($(ls -d $INPUT_DIR/*))
TOTAL_FOLDERS=${#SUBFOLDERS[@]}
VAL_INDEX=0
N_TEST=$(($TOTAL_FOLDERS/5))
TEST_INDEX=$((VAL_INDEX + N_TEST + 1))

# Process folders
for i in "${!SUBFOLDERS[@]}"; do
    FOLDER=${SUBFOLDERS[$i]}
    D04_FILE="$FOLDER/wrfout_d04_*.nc"
    D05_FILE="$FOLDER/wrfout_d05_*.nc"

    # Temporary filenames
    D04_TMP="d04_final.nc"
    D05_TMP="d05_final.nc"

    # Process NetCDF with CDO
    ./process_wrf.sh $D04_FILE $D05_FILE || { echo "Processing failed for $FOLDER"; continue; }

    # Convert to PyTorch tensors
    python3 convert_to_pt.py $D04_TMP $D05_TMP || { echo "Conversion failed for $FOLDER"; continue; }

    # Determine output location
    end_val=$(($VAL_INDEX + $N_TEST))
    end_test=$(($TEST_INDEX + $N_TEST))
    if [ $i -ge $VAL_INDEX ] && [ $i -le $end_val ]; then
        mv d04_tensor.pt $VAL_DIR/d04_tensor${i}.pt
        mv d05_tensor.pt $VAL_DIR/d05_tensor${i}.pt
    elif [ $i -ge $TEST_INDEX ] && [ $i -le $end_test ]; then
        mv d04_tensor.pt $TEST_DIR/d04_tensor${i}.pt
        mv d05_tensor.pt $TEST_DIR/d05_tensor${i}.pt
    else
        mv d04_tensor.pt $TRAIN_DIR/d04_tensor${i}.pt
        mv d05_tensor.pt $TRAIN_DIR/d05_tensor${i}.pt
    fi

    echo "Processed and moved data from $FOLDER."
done
echo "Merge train files"
# Merge training data along the time dimension
python3 merge_pt.py $TRAIN_DIR
python3 merge_pt.py $TEST_DIR
python3 merge_pt.py $VAL_DIR


exit 1
mv output/train/d04_train_merged.pt output/train/input_train.pt
mv output/train/d05_train_merged.pt output/train/target_train.pt
rm output/train/d0*pt

mv output/test/d04_test_merged.pt output/test/input_test.pt
mv output/test/d05_test_merged.pt output/test/target_test.pt
rm output/test/d0*pt


mv output/val/d04_val_merged.pt output/val/input_val.pt
mv output/val/d05_val_merged.pt output/val/target_val.pt
rm output/val/d0*pt

echo "Batch processing complete!"


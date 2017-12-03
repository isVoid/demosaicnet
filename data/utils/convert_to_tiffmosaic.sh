#!/bin/bash

root="/media/michael/Work Drive 1/Pairs/"
declare -a batches=("batch1" "Batch10" "Batch12" "Batch13" "Batch14" "Batch15" "Batch16" "batch3" "Batch4" "Batch5" "Batch6" "Batch7" "Batch8" "Batch9")

out=\"$root"Pairs_Mosaic/"\"

arraylength=${#batches[@]}

for ((i=0; i < $arraylength; i++));
do
  r="\"$root${batches[i]}/\""

  echo python ./convert_into_mosaic.py $r $out
  eval python ./convert_into_mosaic.py $r $out

done

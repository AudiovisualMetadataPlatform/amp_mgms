#!/bin/bash

if [ $# -ne 2 ]; then
	echo "Usage: sh create_lm.sh <training-text-file> <words-file>"
	exit 1;
fi

train_txt=$1
lm_dir=$(dirname "${train_txt}")
words=$2

python scripts/convert_unk.py $train_txt $words $lm_dir/lm_unk.txt
sh add-start-end.sh < $lm_dir/lm_unk.txt > $lm_dir/train.txt
sh build-lm.sh -i $lm_dir/train.txt -o $lm_dir/train.ilm.gz -k 16 -n 2 --PruneSingletons --debug
compile-lm $lm_dir/train.ilm.gz --text=yes /dev/stdout | gzip -c > $lm_dir/train.lm.gz


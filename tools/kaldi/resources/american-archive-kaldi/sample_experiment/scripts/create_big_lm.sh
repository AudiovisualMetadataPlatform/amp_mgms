#!/bin/bash

if [ $# -ne 3 ]; then
	echo "Usage: sh create_big_lm.sh <lm_dir> <lang_dir> <new_lang_dir>"
	exit 1;
fi

lm_dir=$1
lang_dir=$2
new_lang_dir=$3

sh build-lm.sh -i $lm_dir/train.txt -o $lm_dir/iarpa5.lm.gz -k 16 -n 5 --debug
compile-lm $lm_dir/iarpa5.lm.gz --text=yes /dev/stdout | gzip -c > $lm_dir/arpa5.lm.gz
utils/build_const_arpa_lm.sh $lm_dir/arpa5.lm.gz $lang_dir $new_lang_dir

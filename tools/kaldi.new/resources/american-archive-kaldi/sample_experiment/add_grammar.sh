#!/bin/bash
PREFIX=$(dirname $0)
PATHSETTER=$PREFIX/set-kaldi-path.sh
. $PATHSETTER
TMPDIR=/var/extra/audio/work

lm_text=$1

sh scripts/create_lm.sh $lm_text exp/lang/words.txt
sh utils/format_lm.sh exp/lang exp/lm/train.lm.gz exp/dict/lexicon.txt exp/lang_newlm
sh utils/mkgraph.sh exp/lang_newlm exp/tri3 exp/tri3/graph


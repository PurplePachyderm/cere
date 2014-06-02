#!/bin/bash

TMPDIR=`mktemp -d`
make veryclean
make -j4 MODE=--dump
LD_BIND_NOW=1 ./BT

make clean
make -j4 INVITRO_CALL_COUNT=1 MODE=--replay=__extracted__verify_verify__265
./BT > $TMPDIR/test.replay.out

cat $TMPDIR/test.replay.out

cat $TMPDIR/test.replay.out | head -n1 > $TMPDIR/test.a

diff $TMPDIR/test.a verif

exit $?

#!/bin/bash

# ISO image not provided on the command-line; build it
./creator.py -c ovirt.ks >& $OUT
ISO=`ls -1rt livecd-ovirt*.iso | tail -n 1`
echo $ISO
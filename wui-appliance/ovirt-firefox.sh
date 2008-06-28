#!/bin/bash

SSH_ARGS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -fY"

ssh $SSH_ARGS 192.168.50.2 firefox -no-remote


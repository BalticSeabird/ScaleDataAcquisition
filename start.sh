#!/bin/bash

set -e

sudo systemctl start $1.service
sudo systemctl start $1_restart.timer

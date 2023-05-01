#!/bin/bash

set -e

sudo systemctl start $1_scaledaq.service
sudo systemctl start $1_restart.timer

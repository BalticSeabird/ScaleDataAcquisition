#!/bin/bash

set -e

sudo systemctl disable $1_scaledaq.service
sudo systemctl disable $1_restart.timer

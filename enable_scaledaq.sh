#!/bin/bash

set -e

sudo systemctl enable $1_scaledaq.service
sudo systemctl enable $1_restart.timer

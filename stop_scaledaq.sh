#!/bin/bash

set -e

sudo systemctl stop group_a_scaledaq.service
#sudo systemctl stop group_a_restart.service
sudo systemctl stop group_a_restart.timer

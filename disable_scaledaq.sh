#!/bin/bash

set -e

sudo systemctl disable group_a_scaledaq.service
#sudo systemctl disable group_a_restart.service
sudo systemctl disable group_a_restart.timer

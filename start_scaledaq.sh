#!/bin/bash

set -e

sudo systemctl start group_a_scaledaq.service
#sudo systemctl start group_a_restart.service
sudo systemctl start group_a_restart.timer

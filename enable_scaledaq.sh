#!/bin/bash

set -e

sudo systemctl enable group_a_scaledaq.service
#sudo systemctl enable group_a_restart.service
sudo systemctl enable group_a_restart.timer

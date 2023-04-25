#!/bin/bash

set -e

sudo ln -sf $PWD/group_a_scaledaq.service /etc/systemd/system/group_a_scaledaq.service
sudo ln -sf $PWD/group_a_restart.service /etc/systemd/system/group_a_restart.service
sudo ln -sf $PWD/group_a_restart.timer /etc/systemd/system/group_a_restart.timer

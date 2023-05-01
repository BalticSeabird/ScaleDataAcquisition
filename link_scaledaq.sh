#!/bin/bash

set -e

#echo $1_scaledaq.service

sudo ln -sf $PWD/$1_scaledaq.service /etc/systemd/system/$1_scaledaq.service
sudo ln -sf $PWD/$1_restart.service /etc/systemd/system/$1_restart.service
sudo ln -sf $PWD/$1_restart.timer /etc/systemd/system/$1_restart.timer

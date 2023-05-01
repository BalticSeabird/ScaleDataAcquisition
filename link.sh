#!/bin/bash

set -e

sudo ln -sf $PWD/$1.service /etc/systemd/system/$1.service
sudo ln -sf $PWD/$1_restart.service /etc/systemd/system/$1_restart.service
sudo ln -sf $PWD/$1_restart.timer /etc/systemd/system/$1_restart.timer

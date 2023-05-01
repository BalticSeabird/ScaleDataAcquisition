#!/bin/bash

set -e

sudo systemctl stop $1_scaledaq.service
sudo systemctl stop $1_restart.timer

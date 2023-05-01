#!/bin/bash

set -e

sudo systemctl enable $1.service
sudo systemctl enable $1_restart.timer

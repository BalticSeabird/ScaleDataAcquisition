#!/bin/bash

set -e

sudo systemctl stop $1.service
sudo systemctl stop $1_restart.timer

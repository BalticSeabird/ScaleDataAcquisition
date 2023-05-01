#!/bin/bash

set -e

sudo systemctl disable $1.service
sudo systemctl disable $1_restart.timer

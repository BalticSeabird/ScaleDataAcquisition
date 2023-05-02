#!/bin/bash

sh stop.sh dgt1
sh stop.sh dgt2
sh stop.sh weatherlink

sudo systemctl stop bsp_backup.service
sudo systemctl stop bsp_backup.timer
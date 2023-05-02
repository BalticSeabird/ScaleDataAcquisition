#!/bin/bash

sh disable.sh dgt1
sh disable.sh dgt2
sh disable.sh weatherlink

sudo rm /etc/systemd/system/dgt1_restart.service
sudo rm /etc/systemd/system/dgt2_restart.service
sudo rm /etc/systemd/system/weatherlink_restart.service

sudo systemctl disable bsp_backup.service
sudo systemctl disable bsp_backup.timer

#!/bin/bash

sh enable.sh dgt1
sh enable.sh dgt2
sh enable.sh weatherlink

sudo systemctl enable bsp_backup.service
sudo systemctl enable bsp_backup.timer

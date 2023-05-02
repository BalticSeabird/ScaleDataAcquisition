#!/bin/bash

sh start.sh dgt1
sh start.sh dgt2
sh start.sh weatherlink

sudo systemctl start bsp_backup.service
sudo systemctl start bsp_backup.timer
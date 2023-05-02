#!/bin/bash

sh link.sh dgt1
sh link.sh dgt2
sh link.sh weatherlink
sh link.sh weatherlink

sudo ln -sf $PWD/bsp_backup.service /etc/systemd/system/bsp_backup.service
sudo ln -sf $PWD/bsp_backup.timer /etc/systemd/system/bsp_backup.timer

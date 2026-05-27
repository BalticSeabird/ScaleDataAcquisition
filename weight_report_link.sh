#!/bin/bash

set -euo pipefail

sudo ln -sf "$PWD/weight-report.service" /etc/systemd/system/weight-report.service
sudo ln -sf "$PWD/weight-report.timer" /etc/systemd/system/weight-report.timer

sudo systemctl daemon-reload
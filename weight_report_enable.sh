#!/bin/bash

set -euo pipefail

sudo systemctl daemon-reload
sudo systemctl enable weight-report.service
sudo systemctl enable weight-report.timer

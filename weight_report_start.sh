#!/bin/bash

set -euo pipefail

sudo systemctl daemon-reload
sudo systemctl start weight-report.service
sudo systemctl start weight-report.timer

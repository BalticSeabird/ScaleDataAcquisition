# Scale Data AcQuisition (DAQ)

This is a system to recorded weight data streamed from several scale platforms for seabirds at Stora Karlsö. 
The same repo is used for continuousy logging weather data from a Davis Weatherlink weather station. 

## Weight loggers

Control unit DGT2 from [Dini Argeo](www.diniargeo.com)  
Provided by [Vetek](https://www.vetek.se/)  

## Installation

Clone this repo
````bash
git clone git@github.com:BalticSeabird/ScaleDataAcquisition.git
cd ScaleDataAcquisition
````

Setup virtual environment
````bash
./setupvenv.sh
````

## Run

### Command line
Example
````bash
./venv/bin/python scaledaq.py --host 192.168.1.205 --port 26 --no_scales 4 --output_root_path /home/erik/git/pingo/sbsp/scale/output --database_name 2023_scales_group_a.db
````
For help
````bash
./venv/bin/python scaledaq.py -h
````

### System daemon setup
Describe...

First edit (or create your own) systemd service file, 'group_a_scaledaq.service'. If you create a new file also change 'group_a_scaledaq.service' in the 'group_a_restart.service' to the new file name. 

Link the file to the system, for example
````bash
./link_scaledaq.sh
````

To enable, disable at boot
````bash
./enable_scaledaq.sh
./disable_scaledaq.sh
````

To start and stop
````bash
./start_scaledaq.sh
./stop_scaledaq.sh
````

After chnages in the service and timer files do
````bash
sudo systemctl daemon-reload
````



# Scale Data AcQuisition (DAQ)
About...  

Controll unit DGT2 from [Dini Argeo](www.diniargeo.com)  

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

Edit scaledaq_group_a.service file.
````bash
sudo cp scaledaq_group_a.service /lib/systemd/system/.
sudo chmod 644 /etc/systemd/system/scaledaq_group_a.service
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
First edit (or create your own) systemd service file, 'scaledaq_group_a.service'.

Link the file to the system, for example
````bash
sudo ln -sf /home/erik/git/pingo/sbsp/scale/scaledaq_group_a.service /etc/systemd/system/scaledaq_group_a.service
sudo systemctl daemon-reload
````

To start, stop and for status
````bash
sudo systemctl start/stop/status scaledaq_group_a.service
````

To enable, disable at boot
````bash
sudo systemctl enable/disable scaledaq_group_a.service
````


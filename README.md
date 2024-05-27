# WG-NAT-Bootstrap
This repo contains some experimental scripts to setup a Wireguard NAT forward network automatically. This allows for peers to connect to not only to other peers but also NAT devices in the same network as the peer. The scripts are tested on Debian 12 but should work on most linux distributions with some basic modifications. 

## Server Setup (Debian 12)
1. Initial Setup:
    1. `sudo apt update && sudo apt upgrade`
    2. `sudo apt install python3-netifaces python3-dnspython iptables python3-yaml wireguard wireguard-tools`
    3. `cd /opt && sudo git clone https://github.com/JustinTimperio/WG-NAT-Bootstrap.git && cd WG-NAT-Bootstrap`
    4. `sudo cp example.yaml config.yaml`
    6. Open `config.yaml` and add your users and server information
    7. `sudo python3 bootstrap.py`
2. Reconfiguring the server:
    1. Change the configuration in `config.yaml`
    2. `sudo python3 bootstrap.py --reconfigure-server`
3. Reconfiguring the clients:
    1. Add, Enable or Disable a user in `config.yaml`
    2. `sudo python3 bootstrap.py --reconfigure-clients`

## Client Setup
1. Install `wireguard` on your host system
2. Copy the config file from the server located at `/etc/wireguard/clients/<NAME>.conf`
3. Connect: 
    1. Linux:
        1. Open `/etc/wireguard/<NAME>.conf` and paste your configuration into the file 
        2. `sudo wg-quick up <NAME>.conf`
        3. `sudo systemctl enable wg-quick@<NAME>.conf`
    2. Windows:
        1. Open the Wireguard GUI and import the configuration file
        2. Disable the button that says "Block untunneled traffic"
        3. Click the toggle switch to activate the connection
    3. MacOS:
        1. Open the Wireguard GUI and import the configuration file
        2. Disable the button that says "Block untunneled traffic"
        3. Click the toggle switch to activate the connection
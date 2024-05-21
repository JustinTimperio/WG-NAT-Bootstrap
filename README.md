# WG-NAT-Bootstrap
This repo contains some experimental scripts to setup a Wireguard NAT forward network automatically. This allows for peers to connect to not only to other peers but also NAT devices in the same network as the peer. The scripts are tested on Debian 12 but should work on most linux distributions with some basic modifications. 

## Server Setup (Debian 12)
1. `sudo apt update && sudo apt upgrade`
2. `sudo apt install python3-netifaces python3-dnspython iptables`
3. `git clone https://github.com/JustinTimperio/WG-NAT-Bootstrap.git`
4. `cd WG-NAT-Bootstrap`
5. `sudo python3 bootstrap.py`


## Client Setup (Any Linux Distro)
1. Install `iptables` and `wireguard` on your system
2. Copy the config file from the server located at `/etc/wireguard/clients/client.conf`
3. Look at the configuration file and replace the interface device with the one on your system. (e.g. `eth0` -> `enp0s3`)
4. Open `/etc/wireguard/wg0.conf` and paste your configuration into the file
5. `sudo wg-quick up wg0`
6. `sudo systemctl enable wg-quick@wg0`

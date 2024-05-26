import subprocess
import requests
import os
import netifaces
import ipaddress
import dns.resolver
import yaml

def yn_frame(prompt):
    while True:
        yn = input('\033[1m' + prompt + ' (y/n):' + '\033[0m')
        if yn.lower().strip() in ['y', 'yes']:
            return True
        elif yn.lower().strip() in ['no', 'n']:
            return False
        elif yn.lower().strip() in ['quit', 'exit']:
            return None
        else:
            print('Please Respond With Yes/No! (`exit` or `quit` to Return)')

def get_network_info():
    # Get the default gateway
    gateway_info = netifaces.gateways()
    default_gateway = gateway_info['default'][netifaces.AF_INET]

    # Get the network interface of the default gateway
    interface = default_gateway[1]

    # Get the addresses of the network interface
    addresses = netifaces.ifaddresses(interface)

    # Get the IPv4 address and netmask
    ipv4_info = addresses[netifaces.AF_INET][0]
    ipv4_address = ipv4_info['addr']
    netmask = ipv4_info['netmask']

    # Calculate the subnet range
    network = ipaddress.IPv4Network(f'{ipv4_address}/{netmask}', strict=False)
    subnet_range = str(network.network_address) + '/' + str(network.prefixlen)

    # Get the DNS servers
    resolver = dns.resolver.Resolver()
    dns_servers = resolver.nameservers

    # Get the public IP address of the server
    public_ip = requests.get('https://api.ipify.org').text

    return subnet_range, dns_servers, default_gateway, public_ip, interface

def build_wireguard_client_config(conf_name, internal_ip, public_ip, listen_port, public_key):

    # Generate client private and public keys
    client_private_key = subprocess.getoutput('wg genkey')
    client_public_key = subprocess.getoutput(f'echo {client_private_key} | wg pubkey')

    # Append the client configuration to the WireGuard configuration
    peer_config = f"""

[Peer]
PublicKey = {client_public_key}
AllowedIPs = {internal_ip}/32 
    """

    # Write the configuration to a file
    with open('/etc/wireguard/wg0.conf', 'a') as f:
        f.write(peer_config)

    client_config = f"""
[Interface]
Address = {internal_ip}/32
PrivateKey = {client_private_key}
PreUp = sysctl -w net.ipv4.ip_forward=1
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE


[Peer]
PublicKey = {public_key}
Endpoint = {public_ip}:{listen_port}
AllowedIPs = 0.0.0.0/0 
PersistentKeepalive = 25
    """
    
    with open('/etc/wireguard/clients/'+conf_name+'.conf', 'w') as f:
        f.write(client_config)



def setup_wireguard_server(names, public_ip, listen_port, interface_name):

    # Generate private and public keys
    private_key = subprocess.getoutput('wg genkey')
    public_key = subprocess.getoutput(f'echo {private_key} | wg pubkey')

    # Create WireGuard configuration
    config = f"""
[Interface]
Address = 10.0.0.1/32 
SaveConfig = false 
PrivateKey = {private_key}
ListenPort = {listen_port}
PreUp = sysctl -w net.ipv4.ip_forward=1
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o {interface_name} -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o {interface_name} -j MASQUERADE
    """

    # Write the configuration to a file
    with open('/etc/wireguard/wg0.conf', 'w') as f:
        f.write(config)
    # Mark down the public key
    with open('/etc/wireguard/public_key', 'w') as f:
        f.write(public_key)

    for name in names:
        build_wireguard_client_config(name['name'], name['address'], public_ip, listen_port, public_key)
    
    # Create the Systemd service file
    subprocess.run(['systemctl', 'enable', 'wg-quick@wg0'], check=True)

    # Start the WireGuard service
    subprocess.run(['wg-quick', 'up', 'wg0'], check=True)

def deploy_wireguard_server(subnet_range, dns_servers, default_gateway, public_ip, interface_name):
    # Get the port to run WireGuard on
    port_answer = input('\033[1m' + "What port would you like to run Wireguard on? (default=51820): " + '\033[0m')
    try:
        if port_answer == "":
            print("Using default port 51820")
            port = 51820
        else:
            port = int(port_answer)
    except:
        print("Provided Port does NOT seem to be a integer!")
        return

    # Get the names of the clients from the yaml file
    with open('users.yaml') as f:
        names = yaml.load(f, Loader=yaml.FullLoader)['users']

    print("====================================")
    print("Gateway: ", default_gateway)
    print("Subnet Range: ", subnet_range)
    print("DNS Servers: ", dns_servers)
    print("Public IP: ", public_ip)
    print("Interface Name: ", interface_name)
    print("====================================")

    # Setup Wireguard Server
    setup_wireguard_server(names, public_ip, port, interface_name)

def main():

    # Check if the script is running as root
    if os.geteuid() != 0:
        print("Please run this script as root!")
        return

    if not os.path.exists('users.yaml'):
        print("Please create a users.yaml file with the names of the clients")
        return

    subnet_range, dns_servers, default_gateway, public_ip, interface_name = get_network_info()

    # Check if WireGuard is already configured 
    if os.path.exists('/etc/wireguard/wg0.conf'):
        print("WireGuard is already installed and configured!")

        if yn_frame("Do you want to reconfigure WireGuard?"):
            # Stop the WireGuard service
            subprocess.run(['systemctl', 'disable', 'wg-quick@wg0'], check=True)
            subprocess.run(['wg-quick', 'down', 'wg0'], check=False)

            # Remove the configuration files
            os.remove('/etc/wireguard/wg0.conf')
            os.removedirs('/etc/wireguard/clients')

            deploy_wireguard_server(subnet_range, dns_servers, default_gateway, public_ip, interface_name)
            return

        if yn_frame("Do you want to configure new clients?"):
            # Read the existing configuration
            with open('/etc/wireguard/wg0.conf', 'r') as f:
                config = f.read()
            with open('/etc/wireguard/public_key', 'r') as f:
                public_key = f.read()

            existing_names = []
            pub_key_found = False
            for line in config.split('\n'):
                if 'ListenPort' in line:
                    port = int(line.split('=')[1].strip())
                if 'AllowedIPs' in line:
                    existing_names.append(line.split('=')[1].strip()[:-3])

            names = yaml.load(open('users.yaml'), Loader=yaml.FullLoader)['users']
            for name in names:
                if name['address'] not in existing_names:
                    build_wireguard_client_config(name['name'], name['address'], public_ip, port, public_key)
            
            subprocess.run(['wg-quick', 'down', 'wg0'], check=True)
            subprocess.run(['wg-quick', 'up', 'wg0'], check=True)
            return

        else:
            print("Exiting, No Changes...")
            return

main()
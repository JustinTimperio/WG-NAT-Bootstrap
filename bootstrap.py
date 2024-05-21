import subprocess
import requests
import os
import netifaces
import ipaddress
import dns.resolver

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

def setup_wireguard_server(public_ip, listen_port, interface_name):

    # Generate private and public keys
    private_key = subprocess.getoutput('wg genkey')
    public_key = subprocess.getoutput(f'echo {private_key} | wg pubkey')

    # Generate client private and public keys
    client_private_key = subprocess.getoutput('wg genkey')
    client_public_key = subprocess.getoutput(f'echo {client_private_key} | wg pubkey')

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

[Peer]
PublicKey = {client_public_key}
AllowedIPs = 10.0.0.2/32
    """

    client_config = f"""
[Interface]
Address = 10.0.0.2/32
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

    # Write the configuration to a file
    with open('/etc/wireguard/wg0.conf', 'w') as f:
        f.write(config)
    
    with open('/etc/wireguard/clients/client.conf', 'w') as f:
        f.write(client_config)


    # Create the Systemd service file
    subprocess.run(['systemctl', 'enable', 'wg-quick@wg0'], check=True)

    # Start the WireGuard service
    subprocess.run(['wg-quick', 'up', 'wg0'], check=True)


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


def main():

    # Check if the script is running as root
    if os.geteuid() != 0:
        print("Please run this script as root!")
        return

    # Check if WireGuard is already configured 
    if os.path.exists('/etc/wireguard/wg0.conf') or os.path.exists('/etc/wireguard/clients/client.conf'):
        print("WireGuard is already installed and configured!")
        if yn_frame("Do you want to reconfigure WireGuard?"):
            # Stop the WireGuard service
            subprocess.run(['systemctl', 'disable', 'wg-quick@wg0'], check=True)
            subprocess.run(['wg-quick', 'down', 'wg0'], check=False)

            # Remove the configuration files
            os.remove('/etc/wireguard/wg0.conf')
            os.remove('/etc/wireguard/clients/client.conf')
        else:
            return
    else:
        # Create the WireGuard client configuration directory
        os.makedirs('/etc/wireguard/clients', exist_ok=True)


    # Get the port to run WireGuard on
    port_answer = input('\033[1m' + "What port would you like to run Wireguard on? (default=51820): " + '\033[0m')
    try:
        port = int(port_answer)
    except:
        print("Provided Port does NOT seem to be a integer!")
        return

    # Create the WireGuard client configuration directory
    os.makedirs('/etc/wireguard/clients', exist_ok=True)

    # Get the subnet range of the network interface
    subnet_range, dns_servers, default_gateway, public_ip, interface_name = get_network_info()

    print("====================================")
    print("Gateway: ", default_gateway)
    print("Subnet Range: ", subnet_range)
    print("DNS Servers: ", dns_servers)
    print("Public IP: ", public_ip)
    print("Interface Name: ", interface_name)
    print("====================================")

    # Setup Wireguard Server
    setup_wireguard_server(public_ip, port, interface_name)


main()
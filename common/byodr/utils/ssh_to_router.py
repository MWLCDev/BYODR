import logging
import paramiko

# Declaring the logger
logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s', datefmt='%Y%m%d:%H:%M:%S %p %Z')
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)


def fetch_ssid(host, port, username, password, command):
    # Create an SSH client instance
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # Connect to the SSH server
    client.connect(host, port, username, password)
    stdin, stdout, stderr = client.exec_command(command)
    output = stdout.read().decode("utf-8")
    client.close()
    return output

def get_router_arp_table():
    try:
        # Read the ARP table from /proc/net/arp
        with open('/proc/net/arp', 'r') as arp_file:
            arp_table = arp_file.read()
        
        return arp_table
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return []

def get_filtered_router_arp_table(arp_table, last_digit_of_localIP):
    try:
        filtered_arp_table = []
    
        # Split the ARP table into lines
        arp_lines = arp_table.split('\n')
        local_ip_prefix = f"192.168.{last_digit_of_localIP}."

        # Extract and add "IP address" and "Flags" to the filtered table which is what we need
        for line in arp_lines:
            columns = line.split()
            if len(columns) >= 2:
                ip = columns[0]
                flags = columns[2]
                if ip == f'{local_ip_prefix}1' or ip == f'{local_ip_prefix}2':
                    filtered_arp_table.append({'IP address': ip, 'Flags': flags})              
    
        return filtered_arp_table
    except Exception as e:
        logger.error(f"An error occurred while filtering ARP table: {str(e)}")
        return []

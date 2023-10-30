import paramiko
import logging

# Declaring the logger
logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s', datefmt='%Y%m%d:%H:%M:%S %p %Z')
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

def get_router_data(host, port, username, password, command):
    # Create an SSH client instance
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Connect to the SSH server
        client.connect(host, port, username, password)

        # Execute the 'arp' command and capture the output
        stdin, stdout, stderr = client.exec_command(command)

        # Read and print the output line by line
        output = stdout.read().decode()
        logger.info(f"ARP Table Output: <{output}>")
        
        # Process the ARP output, split it into lines, and store it in a list
        arp_table = []
        lines = output.splitlines()

        for line in lines:
            # Skip header lines
            if not line.startswith("IP address"):
                columns = line.split()
                if len(columns) == 6:
                    ip, hw_type, flags, mac, mask, device = columns
                    arp_table.append((ip, mac))

        client.close()
        return arp_table
    
    except paramiko.AuthenticationException:
        logger.error("Authentication failed. Please check your credentials.")
    except paramiko.SSHException as e:
        logger.error(f"SSH connection failed: {str(e)}")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    return []
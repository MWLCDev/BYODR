import logging
import paramiko, time, re

# Declaring the logger
logging.basicConfig(
    format="%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s",
    datefmt="%Y%m%d:%H:%M:%S %p %Z",
)
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)


class Router:
    def __init__(self, ip, username="root", password="Modem001", port=22):
        self.ip = ip
        self.username = username
        self.password = password
        self.port = int(port)  # Default value for SSH port

    def fetch_ssid(self, command):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # Connect to the SSH server
        client.connect(self.ip, self.port, self.username, self.password)
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode("utf-8")
        client.close()
        return output

    def get_router_arp_table():
        try:
            # Read the ARP table from /proc/net/arp
            with open("/proc/net/arp", "r") as arp_file:
                arp_table = arp_file.read()

            return arp_table
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return []

    def get_filtered_router_arp_table(arp_table, last_digit_of_localIP):
        try:
            filtered_arp_table = []

            # Split the ARP table into lines
            arp_lines = arp_table.split("\n")
            local_ip_prefix = f"192.168.{last_digit_of_localIP}."

            # Extract and add "IP address" and "Flags" to the filtered table which is what we need
            for line in arp_lines:
                columns = line.split()
                if len(columns) >= 2:
                    ip = columns[0]
                    flags = columns[2]
                    if ip == f"{local_ip_prefix}1" or ip == f"{local_ip_prefix}2":
                        filtered_arp_table.append({"IP address": ip, "Flags": flags})

            return filtered_arp_table
        except Exception as e:
            logger.error(f"An error occurred while filtering ARP table: {str(e)}")
            return []


class Cameras:
    def __init__(
        self, segment_network_prefix, username="admin", password="SteamGlamour4"
    ):
        self.ip_front = f"{segment_network_prefix}.64"
        self.ip_back = f"{segment_network_prefix}.65"
        self.username = username
        self.password = password

    def get_interface_info(self):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.ip_front, username=self.username, password=self.password)

        channel = client.invoke_shell()
        time.sleep(1)  # Wait for the shell to initialize
        channel.send("ifconfig eth0\n")
        time.sleep(1)
        channel.send("exit\n")
        output = channel.recv(
            65535
        ).decode()  # Huge amount of bytes to read, because it captures everything since the shell is open, and not the result of command only

        client.close()

        # Get Internet Address, Broadcast Address and Subnet Mask.
        match = re.search(r"inet addr:(\S+)  Bcast:(\S+)  Mask:(\S+)", output)
        if not match:
            return "No matching interface information found."

        # Create JSON string directly
        json_output = '{{"inet addr": "{}", "Bcast": "{}", "Mask": "{}"}}'.format(
            match.group(1), match.group(2), match.group(3)
        )

        return json_output

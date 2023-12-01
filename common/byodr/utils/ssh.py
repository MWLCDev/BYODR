import logging
import paramiko, time, re, json
from ipaddress import ip_address

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

    def fetch_ip_and_mac(self):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(self.ip, self.port, self.username, self.password)
            stdin, stdout, stderr = client.exec_command("ip neigh")
            output = stdout.read().decode("utf-8")
            error = stderr.read().decode("utf-8")
            if error:
                print("Command error output: %s", error)
        except Exception as e:
            print("Error during SSH connection or command execution: %s", e)
            return
        finally:
            client.close()

        devices = []
        for line in output.splitlines():
            #  it looks for a pattern like number.number.number.number
            #  It looks for a pattern of six groups of two hexadecimal digits that are separated by either : or -
            match = re.search(
                r"(\d+\.\d+\.\d+\.\d+).+?([0-9A-Fa-f]{2}(?:[:-][0-9A-Fa-f]{2}){5})",
                line,
            )
            if match:
                ip, mac_address = match.groups()
                devices.append({"ip": ip, "mac": mac_address})
        sorted_devices = sorted(devices, key=lambda x: ip_address(x["ip"]))

        print("Devices found: ", sorted_devices)

    def get_router_arp_table():  ######################################################
        try:
            # Read the ARP table from /proc/net/arp
            with open("/proc/net/arp", "r") as arp_file:
                arp_table = arp_file.read()

            return arp_table
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return []

    def get_filtered_router_arp_table(
        arp_table, last_digit_of_localIP
    ):  ######################################################
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

    # Functions fetch_wifi_networks, parse_iwlist_output, parse_ie_data, extract_security_info all are working together
    def fetch_wifi_networks(self):
        """
        Connects to an SSH server and retrieves a list of available Wi-Fi networks.
        Parses the output from the 'iwlist wlan0 scan' command to extract network details.

        Returns:
            list of dict: A list containing information about each network, including (ESSID, MAC, channel, security, IE information).
        """
        command = "iwlist wlan0 scan"
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            # Connect to the SSH server
            client.connect(self.ip, self.port, self.username, self.password)
            stdin, stdout, stderr = client.exec_command(command)
            output = stdout.read().decode("utf-8")

            return self.parse_iwlist_output(output)
        finally:
            client.close()

    def parse_iwlist_output(self, output):
        """Parses the output from the 'iwlist wlan0 scan' command.

        Args:
              output (str): The raw output string from the 'iwlist wlan0 scan' command.

        Returns:
            list of dict: A list of dictionaries, each representing a network with information such as (ESSID, MAC, channel, security, and IE info).
        """
        networks = []
        current_network = {}

        for line in output.splitlines():
            if "Cell" in line and "Address" in line:
                if current_network:
                    networks.append(current_network)
                    current_network = {}
                current_network["MAC"] = line.split()[-1]
            elif "ESSID:" in line:
                current_network["ESSID"] = line.split('"')[1]
            elif "Channel:" in line:
                current_network["Channel"] = line.split(":")[-1]
            elif line.strip().startswith("IE: IEEE 802.11i/WPA2 Version 1"):
                security_info = self.extract_security_info(line, output.splitlines())
                current_network["Security"] = security_info
            elif line.strip().startswith("IE: Unknown"):
                if "IE Information" not in current_network:
                    current_network["IE Information"] = {}

                ie_data = line.strip().split(": ", 2)[-1]
                ie_key, ie_value = parse_ie_data(ie_data)
                if ie_key:
                    current_network["IE Information"][ie_key] = ie_value

        # Reorder the dictionary to show ESSID first
        ordered_networks = []
        for network in networks:
            ordered_network = {
                k: network[k]
                for k in ["ESSID", "MAC", "Channel", "Security", "IE Information"]
                if k in network
            }
            ordered_networks.append(ordered_network)

        return ordered_networks

    def parse_ie_data(self, ie_data):
        """Parses and interprets a single Information Element (IE) data entry.

        Args:
            ie_data (str): A string representing an IE data entry.

        Returns:
            tuple: A key-value pair representing the IE type and its data.
            Returns (None, None) if the IE type is unrecognized.
        """
        # This function can be expanded to interpret more IE types
        ie_type = ie_data[:2]
        if ie_type == "00":
            return "Vendor Specific IE", ie_data[2:]
        elif ie_type == "01":
            return "Supported Rates", ie_data[2:]
        elif ie_type == "03":
            return "DS Parameter Set (Channel Information)", ie_data[2:]
        elif ie_type == "07":
            return "Country Information", ie_data[2:]

        return None, None  # Return None if IE type is not recognized

    def extract_security_info(self, start_line, all_lines):
        """Returns a JSON for the security information in the security line of scanned networks

        Args:
            start_line (str): The line where security information starts in the output.
            all_lines (list of str): All lines of the scan output.

        Returns:
            dict: A dictionary with security information such as WPA2 version, group cipher, pairwise ciphers, and authentication suites.
        """
        security_info = {}
        index = all_lines.index(start_line)
        for line in all_lines[index:]:
            if line.strip().startswith("IE: IEEE 802.11i/WPA2 Version 1"):
                security_info["WPA2 Version"] = line.split(":")[-1].strip()
            elif line.strip().startswith("Group Cipher"):
                security_info["Group Cipher"] = line.split(":")[-1].strip()
            elif line.strip().startswith("Pairwise Ciphers"):
                security_info["Pairwise Ciphers"] = line.split(":")[-1].strip()
            elif line.strip().startswith("Authentication Suites"):
                security_info["Authentication Suites"] = line.split(":")[-1].strip()
            elif line.strip().startswith("IE:"):
                break  # Stop at the next IE
        return security_info


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

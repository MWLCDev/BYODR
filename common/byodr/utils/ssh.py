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
        self.wifi_scanner = self.WifiNetworkScanner(self)

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
        """Get list of all connected devices to the current segment"""
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

    class WifiNetworkScanner:
        def __init__(self, router):
            self.router = router

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
                client.connect(
                    self.router.ip,
                    self.router.port,
                    self.router.username,
                    self.router.password,
                )
                stdin, stdout, stderr = client.exec_command(command)
                output = stdout.read().decode("utf-8")

                scanned_networks = self.parse_iwlist_output(output)
                # DEBUGGING
                # print(json.dumps(scanned_networks, indent=4))  # Pretty print the JSON

                # for network in scanned_networks:
                #    print(network.get("ESSID"), network.get("MAC"), end="\n")
                return (scanned_networks)
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
                    security_info = self.extract_security_info(
                        line, output.splitlines()
                    )
                    current_network["Security"] = security_info
                elif line.strip().startswith("IE: Unknown"):
                    if "IE Information" not in current_network:
                        current_network["IE Information"] = {}

                    ie_data = line.strip().split(": ", 2)[-1]
                    ie_key, ie_value = self.parse_ie_data(ie_data)
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

    def get_wifi_networks(self):
        return self.wifi_scanner.fetch_wifi_networks()

    def connect_to_network(self):
        """connect to another network from the current segment"""
        pass


class Cameras:
    """Class to deal with the SSH for the camera
    Functions: get_interface_info()
    """

    def __init__(
        self, segment_network_prefix, username="admin", password="SteamGlamour4"
    ):
        # IPS SHOULD BE DEFINED FROM THE CONFIG FILE
        self.ip_front = f"{segment_network_prefix}.64"
        self.ip_back = f"{segment_network_prefix}.65"
        self.username = username
        self.password = password

    def get_interface_info(self):
        """Fetch current network details from the camera

        Returns:
            JSON: Internet Address, Broadcast Address and Subnet Mask.
        """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.ip_front, username=self.username, password=self.password)

        channel = client.invoke_shell()
        # Wait for the shell to initialize. IMPORTANT WHEN WORKING WITH THE CAMERA
        time.sleep(1)
        channel.send("ifconfig eth0\n")
        time.sleep(1)
        channel.send("exit\n")
        # Huge amount of bytes to read, because it captures everything since the shell is open, and not the result of command only
        output = channel.recv(65535).decode()

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

    def set_camera_ip(self, new_ip, camera="front", subnet_mask="255.255.255.0"):
        """
        Set the IP address of the specified camera.

        :param new_ip: New IP address to set.
        :param camera: Specify 'front' or 'back' camera.
        :param subnet_mask: Subnet mask to use, defaults to '255.255.255.0'.
        """
        if camera not in ["front", "back"]:
            raise ValueError("Camera must be either 'front' or 'back'")

        camera_ip = self.ip_front if camera == "front" else self.ip_back

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(camera_ip, username=self.username, password=self.password)

            channel = client.invoke_shell()
            time.sleep(1)
            set_ip_command = f"setIp {new_ip}:{subnet_mask}\n"
            channel.send(set_ip_command)
            time.sleep(1)  # Wait for command to execute

            channel.send("exit\n")
            output = channel.recv(65535).decode()
            # print(output)  # Printing the output for verification
            client.close()

        except Exception as e:
            print(f"An error occurred: {e}")
            if client:
                client.close()

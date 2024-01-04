import logging
import paramiko, time, re, json
from ipaddress import ip_address
import paramiko
import traceback
import subprocess

# Declaring the logger
logging.basicConfig(
    format="%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s",
    datefmt="%Y%m%d:%H:%M:%S %p %Z",
)

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

paramiko_logger = logging.getLogger("paramiko")
paramiko_logger.setLevel(logging.CRITICAL)


class Router:
    def __init__(self, ip=None, username="root", password="Modem001", port=22):
        self.ip = ip if ip is not None else self.__get_nano_third_octet()
        self.username = username
        self.password = password
        self.port = int(port)  # Default value for SSH port
        self.wifi_scanner = self.WifiNetworkScanner(self)
        self.wifi_connect = self.ConnectToNetwork(self)

    def __get_nano_third_octet(self):
        try:
            # Fetch the IP address
            ip_address = subprocess.check_output("hostname -I | awk '{for (i=1; i<=NF; i++) if ($i ~ /^192\\.168\\./) print $i}'", shell=True).decode().strip().split()[0]

            # Trim off the last segment of the IP address
            parts = ip_address.split(".")
            network_prefix = ".".join(parts[:3]) + "."
            router_ip = f"{network_prefix}1"
            return router_ip
        except subprocess.CalledProcessError as e:
            print(f"An error occurred: {e}")
            return None

    # Protected function for internal use but can still be accessed from inner classes or subclasses
    def _execute_ssh_command(self, command, ip=None, file_path=None, file_contents=None):
        """
        Executes a command on the router via SSH and returns the result.
        Optionally, can write to a file on the router using SFTP.

        Args:
            command (str): Command to be executed on the router.
            file_path (str, optional): Path to the file to be written via SFTP.
            file_contents (str, optional): Contents to write to the file.

        Returns:
            str: The output of the command execution, or None in case of SFTP.
        """
        # In case I want to ssh to another router. I can just pass the IP for it and no need to pass the other credentials
        router_ip = ip if ip is not None else self.ip

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(router_ip, self.port, self.username, self.password)

            if file_path and file_contents is not None:
                # Handle SFTP file write operation
                with client.open_sftp() as sftp:
                    with sftp.file(file_path, "w") as file:
                        file.write(file_contents)
                client.close()
                # No command output in case of SFTP operation
                return None

            # Execute the SSH command
            stdin, stdout, stderr = client.exec_command(command)
            result = stdout.read().decode()
            error = stderr.read().decode()

            client.close()

            if error:
                raise Exception(error)

            return result

        except Exception as e:
            # Get the name of the caller function
            caller = traceback.extract_stack(None, 2)[0][2]
            print(f"Error occurred in {caller}: {e}")
            return None

    def fetch_ssid(self):
        """Get SSID of current segment"""
        output = self._execute_ssh_command("uci get wireless.@wifi-iface[0].ssid")
        return output

    def fetch_segment_ip(self):
        """Return an ip of .100"""
        output = self._execute_ssh_command("ip addr show br-lan | grep 'inet ' | awk '{print $2}' | cut -d/ -f1")
        return output

    def fetch_router_mac(self):
        output = self._execute_ssh_command("ifconfig wlan0 | grep -o -E '([[:xdigit:]]{2}:){5}[[:xdigit:]]{2}'")
        return output

    def fetch_ip_and_mac(self):
        """Get list of all connected devices to the current segment

        Example
          >>>connected_devices= fetch_ip_and_mac() \n
          data = json.loads(connected_devices)

          # Access the MAC addresses by specifying the index of each item \n
          mac_address_type1 = data[0]['MAC'] \n
          mac_address_type2 = data[1]['MAC']
        """

        output = self._execute_ssh_command("ip neigh")
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

                # Determine the label based on IP address
                label = ""
                # MicroController
                if ip.endswith(".32"):
                    label = "mc_pi"
                elif ip.endswith(".64"):
                    label = "front camera"
                elif ip.endswith(".65"):
                    label = "back camera"
                elif ip.endswith(".100"):
                    label = "mc_nano"

                device_info = {"label": label, "ip": ip, "mac": mac_address} if label else {"ip": ip, "mac": mac_address}

                devices.append(device_info)

        sorted_devices = sorted(devices, key=lambda x: ip_address(x["ip"]))
        print("Devices found: ", sorted_devices)

    @staticmethod
    def check_network_connection(target_ip):
        response = ping(target_ip, count=6, timeout=1, verbose=False)

        if response.success():
            # Calculate the total round-trip time of successful responses
            total_time = sum(resp.time_elapsed for resp in response if resp.success)
            # Calculate the average round-trip time (in milliseconds)
            average_time_ms = (total_time / len([resp for resp in response if resp.success])) * 1000
            logger.info(f"Success: Device at {target_ip} is reachable. Average speed: {average_time_ms:.2f}ms")
            return True
        else:
            logger.info(f"Failure: Device at {target_ip} is not reachable.")
            return False

    class WifiNetworkScanner:
        def __init__(self, router):
            self.router = router

        def fetch_wifi_networks(self):
            """
            Connects to an SSH server and retrieves a list of available Wi-Fi networks.
            Parses the output from the 'iwlist wlan0 scan' command to extract network details.

            Returns:
                list of dict: A list containing information about each network, including (ESSID, MAC, channel, security, IE information).
            """
            output = self.router._execute_ssh_command("iwlist wlan0 scan")
            # print(output)
            scanned_networks = self.parse_iwlist_output(output)
            # DEBUGGING
            # print(json.dumps(scanned_networks, indent=4))  # Pretty print the JSON
            # for network in scanned_networks:
            #    print(network.get("ESSID"), network.get("MAC"), end="\n")
            return scanned_networks

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
                    ie_key, ie_value = self.parse_ie_data(ie_data)
                    if ie_key:
                        current_network["IE Information"][ie_key] = ie_value

            networks = self.filter_networks_by_ssid(networks)
            # Reorder the dictionary to show ESSID first
            ordered_networks = []
            for network in networks:
                ordered_network = {k: network[k] for k in ["ESSID", "MAC", "Channel", "Security", "IE Information"] if k in network}
                ordered_networks.append(ordered_network)

            return ordered_networks

        def filter_networks_by_ssid(self, networks):
            """Filters networks by SSID prefixes.

            Args:
                networks (list of dict): List of network dictionaries.

            Returns:
                list of dict: Filtered networks with SSID starting with 'MWLC_' or 'CP_'.
            """

            filtered_networks = [net for net in networks if net["ESSID"].startswith(("MWLC_", "CP_"))]
            return filtered_networks

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

    class ConnectToNetwork:
        def __init__(self, router_instance):
            self.router = router_instance

        def driver(self, network_name, network_mac, network_forth_octet=150):
            self.network_name = network_name
            self.network_mac = network_mac
            # Will be used when joining the network of target segment
            self.network_forth_octet = network_forth_octet
            # The third octet for target network
            self.network_router_third_octet = None
            try:
                # Step 1: Add the new network to the interface and network config files
                self.__connect_to_network()
                # Step 2: Add the new network to the firewall
                self.__update_firewall_config()
                # Step 3: Get the IP of current router when it joins as a client to the target segment's router
                self.__get_IP_new_network()
                # Step 4: Remove the DHCP connection
                self.__delete_interface_DHCP_config()
                # The IP address of current router when it joins the target router as a client
                self.current_router_client_address = f"192.168.{self.network_router_third_octet}.{self.network_forth_octet}"
                # Step 5: Add the updated config to interface
                self.__update_interface_config()
                # Step 6: SSH to target router and add the static router to the current router
                self.__add_static_route()
            except Exception as e:
                logger.info(f"There was a problem while trying to connect to {self.network_name}: {e}")
            finally:
                logger.info(f"connection to {self.network_name} has been done successfully.")

        def __connect_to_network(self):
            """Add wireless network to `wireless.config` and `interface.config`

            Args:
                network_name (str): Name of new network.
                network_mac (str): MAC address for the new network.

            Example
                >> connect_to_network("CP_Davide", "{MAC_ADDRESS}")
            """
            network_name_char = self.network_name.split("_")[-1][0]

            # Convert the character to its alphabetical position
            position = ord(network_name_char.upper()) - ord("A") + 1
            network_password = f"Orangebachcps1n{position}"

            wireless_config = f"""\n
config wifi-iface '1'
        option key '{network_password}'
        option ssid '{self.network_name}'
        option encryption 'psk2'
        option device 'radio0'
        option mode 'sta'
        option bssid '{self.network_mac}'
        option network '{self.network_name}'
        option skip_inactivity_poll '0'
        option _bgscan_enabled '0'
        option ieee80211r '0'
        option wds '0'
        option disassoc_low_ack '0'
        option short_preamble '0'
"""

            interface_DHCP_config = f"""\n
config interface '{self.network_name}'
        option proto 'dhcp'
        option metric '5'
        option area_type 'wan'
        option device 'wlan0'
        option name '{self.network_name}'
        option force_link '0'
"""
            configs = [("/etc/config/wireless", wireless_config), ("/etc/config/network", interface_DHCP_config)]

            try:
                for config_file, config_data in configs:
                    current_config = self.router._execute_ssh_command(f"cat {config_file}")

                    if config_data not in current_config:
                        self.router._execute_ssh_command(f'echo "{config_data}" >> {config_file}')
                        logger.info(f"Added {self.network_name} section in {config_file}")
                    else:
                        logger.info(f"{self.network_name} section already exists in {config_file}")

            except Exception as e:
                logger.info(f"An error occurred while adding {self.network_name} network: {e}")
            finally:
                self.router._execute_ssh_command("wifi reload")

        def __update_firewall_config(self):
            firewall_config_path = "/etc/config/firewall"
            updated_config = ""

            current_config = self.router._execute_ssh_command(f"cat {firewall_config_path}")
            for line in current_config.split("\n"):
                if "config zone" in line and "'3'" in line:
                    updated_config += line + "\n"
                    continue

                if "option network" in line and "wan" in line:
                    updated_line = re.sub(r"option network '(.+?)'", f"option network '\\1 {self.network_name}'", line)
                    updated_config += updated_line + "\n"
                    continue

                updated_config += line + "\n"
            try:
                self.router._execute_ssh_command(command=None, file_path=firewall_config_path, file_contents=updated_config)
            except Exception as e:
                logger.info(f"An error occurred while updating the firewall config with {self.network_name} network: {e}")
            finally:
                self.router._execute_ssh_command("wifi reload")
                logger.info(f"updated the firewall config with the new network {self.network_name}")

        def __get_IP_new_network(self):
            """Get the third octet of IP that is being used in the new segment's network after joining it as a client"""
            time.sleep(30)
            # To return the full IP ("ifconfig wlan0-1 | grep 'inet addr' | awk '{print $2}' | cut -d':' -f2")
            self.network_router_third_octet = self.router._execute_ssh_command("ifconfig wlan0-1 | grep 'inet addr' | awk '{print $2}' | cut -d':' -f2 | cut -d'.' -f3")
            logger.info(f"Third octet of current segment in {self.network_name} network is {self.network_router_third_octet}")

        def __delete_interface_DHCP_config(self):
            # Read the interface file
            file_content = self.router._execute_ssh_command(f"cat /etc/config/network")

            # Split the file into sections based on empty lines
            sections = file_content.split("\n\n")
            updated_content = []
            section_found = False

            for section in sections:
                if f"config interface '{self.network_name}'" in section:
                    section_found = True
                else:
                    updated_content.append(section)

            if section_found:
                # Join the remaining sections
                new_file_content = "\n\n".join(updated_content).strip() + "\n"

                # Prepare the temp file path and content
                temp_file = f"/tmp/network.conf"
                try:
                    # Write the updated content back to the file
                    self.router._execute_ssh_command(f'echo "{new_file_content}" > {temp_file}')

                    # Move the temp file to overwrite the original
                    self.router._execute_ssh_command(f"mv {temp_file} /etc/config/network")
                except Exception as e:
                    logger.info(f"An error occurred while deleting DHCP interface for network {self.network_name}: {e}")
                finally:
                    logger.info(f"{self.network_name} DHCP section deleted successfully from interface.")
            else:
                logger.info(f"No DHCP section found for {self.network_name} in the interface configuration.")

        def __update_interface_config(self):
            """Update /etc/config/network with the new config that has a static ip in it"""
            self.network_router_ip = ".".join(self.router.ip.split(".")[:2] + [str(self.network_router_third_octet)] + self.router.ip.split(".")[3:])

            interface_static_config = f"""\n
config interface '{self.network_name}'
        option metric '6'
        option area_type 'wan'
        option ipaddr '{self.current_router_client_address}'
        option netmask '255.255.255.0'
        option delegate '1'
        option force_link '0'
        option proto 'static'
        option name '{self.network_name}'
        option gateway '{self.network_router_ip}'
"""
            try:
                # Retrieve current network configuration
                current_network_config = self.router._execute_ssh_command("cat /etc/config/network")

                # Check if the configuration already exists
                if interface_static_config.strip() not in current_network_config:
                    # Append the configuration if it doesn't exist
                    commands = [f'echo "{interface_static_config}" >> /etc/config/network', "wifi reload"]
                    for command in commands:
                        self.router._execute_ssh_command(command)
                else:
                    logger.info(f"Static IP configuration for {self.network_name} already exists.")
            except Exception as e:
                logger.info(f"An error occurred while updating interface static config for {self.network_name} network: {e}")
            finally:
                logger.info(f"Finished processing interface static config for {self.network_name} network")

        def __add_static_route(self):
            # Sleeping time until the current router pends all the changes
            sleeping_time = 60
            logger.info(f"will wait {sleeping_time} seconds to make the static route to {self.network_name}. The connection needs to be working first")
            time.sleep(sleeping_time)

            # Gets the IP until the third dot
            network_prefix = ".".join(self.router.ip.split(".")[:3]) + "."
            current_segment_ip = f"{network_prefix}0"

            static_route_config = f"""\n
config route '1'
        option table '254'
        option netmask '255.255.255.0'
        option interface 'lan'
        option gateway '{self.current_router_client_address}'
        option target '{current_segment_ip}'
        option metric '1'
"""

            try:
                # Retrieve current network configuration
                current_network_config = self.router._execute_ssh_command("cat /etc/config/network")

                # Check if the static route configuration already exists
                if static_route_config.strip() not in current_network_config:
                    # Append the configuration if it doesn't exist
                    commands = [f'echo "{static_route_config}" >> /etc/config/network', "wifi reload"]
                    for command in commands:
                        self.router._execute_ssh_command(command)
                else:
                    logger.info(f"Static route configuration for {self.network_name} already exists.")
            except Exception as e:
                logger.info(f"An error occurred while making static route for {self.network_name} network: {e}")
            finally:
                logger.info(f"Finished processing static route for {self.network_name} network")

    def connect_to_network(self, network_name, network_mac, network_forth_octet=150):
        # Delegating the call to the ConnectToNetwork instance
        return self.wifi_connect.driver(network_name, network_mac, network_forth_octet)

    def delete_network(self, keyword):
        """Remove network from `wireless.config` or `network.config`
        Args:
            keyword (str): The keyword to look for

         Example:
            >> delete_network("CP_Davide")`.

        """
        # It works by splitting these two files into sections based on the empty line. Then look for the section that has the keyword in it, make a temp file without the section that has the keyword, move the temp file instead of the original one
        try:
            for dir_location in ["wireless", "network", "firewall"]:
                # Read the content of config file
                output = self._execute_ssh_command(f"cat /etc/config/{dir_location}")
                file_content = output
                if dir_location != "firewall":
                    # Split the file into sections based on empty lines
                    sections = file_content.split("\n\n")
                    updated_content = ""
                    section_to_delete = None

                    for section in sections:
                        if keyword in section:
                            section_to_delete = section
                            break
                        else:
                            updated_content += section + "\n\n"

                    if section_to_delete:
                        # Prepare the temp file path and content
                        temp_file = f"/tmp/{dir_location}.conf"
                        updated_content = updated_content.replace(section_to_delete, "").strip()

                        # Write the updated content back to the file using SFTP
                        self._execute_ssh_command(None, file_path=temp_file, file_contents=updated_content)

                        # Move the temp file to overwrite the original
                        self._execute_ssh_command(f"mv {temp_file} /etc/config/{dir_location}")
                        print(f"{keyword} section deleted successfully from {dir_location}.")
                    else:
                        print(f"{keyword} not found in any {dir_location} section.")
                else:
                    # New functionality for firewall
                    if keyword in file_content:
                        updated_content = file_content.replace(keyword, "").strip()
                        temp_file = f"/tmp/{dir_location}.conf"

                        # Write the updated content back to the file using SFTP
                        self._execute_ssh_command(None, file_path=temp_file, file_contents=updated_content)

                        # Move the temp file to overwrite the original
                        self._execute_ssh_command(f"mv {temp_file} /etc/config/{dir_location}")
                        print(f"{keyword} deleted successfully from {dir_location}.")
                    else:
                        print(f"{keyword} not found in {dir_location}.")
        except Exception as e:
            print("An error occurred:", e)
        finally:
            self._execute_ssh_command(f"wifi reload")


class Cameras:
    """Class to deal with the SSH for the camera
    Functions: get_interface_info()
    """

    def __init__(self, segment_network_prefix, username="admin", password="SteamGlamour4"):
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
        json_output = '{{"inet addr": "{}", "Bcast": "{}", "Mask": "{}"}}'.format(match.group(1), match.group(2), match.group(3))

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


class Nano:
    @staticmethod
    def get_ip_address():
        try:
            ip_addresses = (
                subprocess.check_output(
                    "hostname -I | awk '{for (i=1; i<=NF; i++) if ($i ~ /^192\\.168\\./) print $i}'",
                    shell=True,
                )
                .decode()
                .strip()
            )
            # Split in case there are multiple local IP addresses
            return ip_addresses
        except subprocess.CalledProcessError as e:
            print(f"An error occurred: {e}")
            return None

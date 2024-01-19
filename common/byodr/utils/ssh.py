# TESTED AND WORKING ON
# Firmware version :RUT9_R_00.07.06.1
# Firmware build date: 2024-01-02 11:11:13
# Internal modem firmware version: SLM750_4.0.6_EQ101
# Kernel version: 5.4.259


import json
import logging
import re
import subprocess
import time
import traceback
from ipaddress import ip_address

import paramiko
from pythonping import ping

# Declaring the logger
logging.basicConfig(
    format="%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(lineno)d %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S %p",
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
        self.wifi_delete = self.WifiNetworkDeletion(self)
        self.fetch_ip_from_mac = self.FetchIpFromMac(self)
        self.client = None
        self.__open_ssh_connection()

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

    def __open_ssh_connection(self):
        """
        Opens an SSH connection to the router.
        """
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(self.ip, self.port, self.username, self.password)
        except Exception as e:
            logger.error(f"Failed to open SSH connection: {e}")
            self.client = None

    def _execute_ssh_command(self, command, ip=None, file_path=None, file_contents=None, suppress_error_log=False):
        """
        Executes a command on the router via SSH and returns the result.
        Optionally, can write to a file on the router using SFTP.
        """
        router_ip = ip if ip is not None else self.ip
        temp_client = None

        try:
            if router_ip != self.ip:
                # Establish a temporary connection for a different router
                temp_client = paramiko.SSHClient()
                temp_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                temp_client.connect(router_ip, self.port, self.username, self.password)
                client = temp_client
            else:
                # Check and use the persistent connection for the primary router
                if not self.client or not self.client.get_transport() or not self.client.get_transport().is_active():
                    self.__open_ssh_connection()
                client = self.client

            if file_path and file_contents is not None:
                # Handle SFTP file write operation
                with client.open_sftp() as sftp:
                    with sftp.file(file_path, "w") as file:
                        file.write(file_contents)
                # No command output in case of SFTP operation
                return None

            # Execute the SSH command
            stdin, stdout, stderr = client.exec_command(command)
            result = stdout.read().decode().strip()
            error = stderr.read().decode().strip()

            if error:
                raise Exception(error)

            return result

        except Exception as e:
            if not suppress_error_log:
                # Log the error
                caller = traceback.extract_stack(None, 2)[0][2]
                logger.info(f"Error occurred in {caller}: {e}")
            return None

        finally:
            # Close the temporary client if it was used
            if router_ip != self.ip and temp_client:
                temp_client.close()

    def close_ssh_connection(self):
        """
        Closes the SSH connection to the router.
        """
        if self.client:
            self.client.close()
            self.client = None

    def fetch_ssid(self):
        """Get SSID of current segment"""
        output = None
        # The loop is to keep calling the ssh function until it returns a value
        while output is None:
            output = self._execute_ssh_command("uci get wireless.@wifi-iface[0].ssid", suppress_error_log=True)
            if output is None:
                time.sleep(1)
        return output

    def fetch_router_mac(self):
        output = None
        while output is None:
            output = self._execute_ssh_command("ifconfig wlan0 | grep -o -E '([[:xdigit:]]{2}:){5}[[:xdigit:]]{2}'", suppress_error_log=True)
            if output is None:
                time.sleep(1)
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

    def change_wifi_visibility(self, desired_state):
        try:
            # Get current state for the Wifi network
            ssh_output = self._execute_ssh_command("uci get wireless.default_radio0.hidden").strip()

            # Determine the current state: '0' for discoverable, '1' for hidden
            is_currently_hidden = ssh_output == "1"

            # Convert desired_state to boolean ('True' or 'False' string to a boolean value)
            desired_state_bool = desired_state.lower() == "true"

            # Check if the current state is different from the desired state
            if (is_currently_hidden and desired_state_bool) or (not is_currently_hidden and not desired_state_bool):
                # If the WiFi is hidden and should be discoverable, or vice versa
                new_state = "0" if desired_state_bool else "1"
                self._execute_ssh_command(f"uci set wireless.default_radio0.hidden={new_state}; uci commit wireless; wifi reload")

                new_state_str = "discoverable" if desired_state_bool else "hidden"
                logger.info(f"Wifi network visibility changed to {new_state_str}")
        except Exception as e:
            logger.error(f"Error in changing WiFi visibility: {e}")

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
            return False

    class FetchIpFromMac:
        def __init__(self, router):
            self.router = router
            self.networks = None

        def driver(self, mac_address):
            wireless_config_path = "/etc/config/wireless"
            network_config_path = "/etc/config/network"

            try:
                # Fetch wireless configuration and find the network interface
                wireless_config = self.router._execute_ssh_command(f"cat {wireless_config_path}")
                network_interface = self._parse_wireless_config(wireless_config, mac_address)
                if not network_interface:
                    return False

                # Fetch network configuration and find the gateway IP
                network_config = self.router._execute_ssh_command(f"cat {network_config_path}")
                target_ip = self._parse_network_config(network_config, network_interface)
                if target_ip:
                    # Split the IP and replace the fourth octet with '100'
                    ip_parts = target_ip.split(".")
                    target_nano_ip = ".".join(ip_parts[:3] + ["100"])

                    return [target_ip, target_nano_ip]

            except Exception as e:
                logging.error(f"An error occurred: {e}")
                return None

        def _parse_wireless_config(self, config, mac_address):
            lines = config.split("\n")
            current_section = None
            for line in lines:
                if line.startswith("config wifi-iface"):
                    current_section = {}
                elif "option bssid" in line and mac_address in line:
                    current_section["mac_found"] = True
                elif "option network" in line and current_section.get("mac_found"):
                    return line.split("'")[1]  # # option network 'ifWan2' will return (ifWan2)
            return None

        def _parse_network_config(self, config, network_interface):
            lines = config.split("\n")
            current_section = None
            for line in lines:
                if line.startswith(f"config interface '{network_interface}'"):
                    current_section = True
                elif "option gateway" in line and current_section:
                    return line.split("'")[1]  # Extracting gateway IP
            return None

    def get_ip_from_mac(self, mac_address):
        return self.fetch_ip_from_mac.driver(mac_address)

    class WifiNetworkScanner:
        def __init__(self, router):
            self.router = router
            self.networks = None

        def fetch_wifi_networks(self):
            """
            Connects to an SSH server and retrieves a list of available Wi-Fi networks.
            Parses the output from the 'iwlist wlan0 scan' command to extract network details.

            Returns:
                list of dict: A list containing information about each network, including (ESSID and MAC).
            """
            output = self.router._execute_ssh_command("iwlist wlan0 scan")
            self.parse_iwlist_output(output)
            self.filter_teltonika_networks()

            # DEBUGGING
            # print(json.dumps(self.networks, indent=4))  # Pretty print the JSON
            # for network in self.networks:
            #    print(network.get("ESSID"), network.get("MAC"), end="\n")
            return self.networks

        def parse_iwlist_output(self, output):
            """Parses the output from the 'iwlist wlan0 scan' command.
            Args:
                  output (str): The raw output string from the 'iwlist wlan0 scan' command.

            Returns:
                list of dict: A list of dictionaries, each representing a network with information such as (ESSID and MAC).
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

            # Reorder the dictionary to show ESSID first
            ordered_networks = []
            for network in networks:
                ordered_network = {k: network[k] for k in ["ESSID", "MAC"] if k in network}
                ordered_networks.append(ordered_network)

            self.networks = ordered_networks

        def filter_teltonika_networks(self):
            """
            Filters the list of networks to include only those with MAC addresses belonging to Teltonika.

            Args:
                networks (list of dict): List of networks to be filtered.

            Returns:
                list of dict: Filtered list of networks.
            """
            teltonika_prefixes = ["20:97:27", "00:1E:42"]
            filtered_networks = [network for network in self.networks if any(network["MAC"].startswith(prefix) for prefix in teltonika_prefixes)]
            self.networks = filtered_networks

    def get_wifi_networks(self):
        return self.wifi_scanner.fetch_wifi_networks()

    class ConnectToNetwork:
        """Connect to a network using the SSID and mac address for it"""

        def __init__(self, router_instance):
            self.router = router_instance
            # Full IP of the target router
            self.network_router_ip = None
            # The IP address of current router when it joins the target router as a client
            self.current_router_client_address = None
            self.wireless_config_content = None
            self.interface_config_content = None

        def driver(self, network_name, network_mac, network_forth_octet):
            start_time = time.time()
            # REMOVE THE REBOOT RESTART, THE FIREWALL RESTARTING COMMAND IS WORKING FINE
            self.network_name = network_name
            self.network_mac = network_mac
            # Will be used when joining the network of target segment
            self.network_forth_octet = network_forth_octet
            try:
                # Step 1: Add the new network to the interface and network config files
                self.__connect_to_network()
                # Step 2: Get the IP of current router when it joins as a client to the target segment's router
                self.__get_IP_new_network()
                # Step 3: Remove the DHCP connection
                self.__delete_interface_DHCP_config()
                # Step 4: Add the updated config to interface
                self.__update_interface_config()
                # Step 5: Add the new network to the firewall
                self.__update_firewall_config()
                # Step 6: SSH to target router and add the static router to the current router
                self.__add_static_route()
            except Exception as e:
                end_time = time.time()
                elapsed_time = end_time - start_time
                logger.info(f"Trying to connect to {self.network_name} failed after {elapsed_time:.2f} seconds with error: {e}")

            else:
                end_time = time.time()
                elapsed_time = end_time - start_time
                logger.info(f"Connection to {self.network_name} has been done successfully in {elapsed_time:.2f} seconds.")
                self.router.close_ssh_connection()

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

                        updated_config = current_config + config_data

                        if config_file == "/etc/config/wireless":
                            self.wireless_config_content = updated_config
                        elif config_file == "/etc/config/network":
                            self.interface_config_content = updated_config
                    else:
                        logger.info(f"{self.network_name} section already exists in {config_file}")

            except Exception as e:
                logger.info(f"An error occurred while adding {self.network_name} network: {e}")
            finally:
                self.router._execute_ssh_command("wifi reload")

        def __get_IP_new_network(self):
            """Get the third octet of IP that is being used in the new segment's network after joining it as a client"""
            network_router_third_octet_command = "ifconfig wlan0-1 | grep 'inet addr' | awk '{print $2}' | cut -d':' -f2 | cut -d'.' -f3"
            while True:
                # Executing the command to get the IP address
                self.network_router_third_octet = self.router._execute_ssh_command(network_router_third_octet_command, suppress_error_log=True)
                if self.network_router_third_octet is None:
                    continue

                if self.network_router_third_octet.isdigit():
                    logger.info(f"Third octet of current segment in {self.network_name} network is {self.network_router_third_octet}")
                    self.network_router_third_octet = self.network_router_third_octet.replace(" ", "")
                    # There are lots of split in it to make sure the used ip is dynamic to the current segment. It can start with 192.168. or any other digits
                    self.current_router_client_address = ".".join(self.router.ip.split(".")[:2] + [str(self.network_router_third_octet)] + [str(self.network_forth_octet)])
                    self.network_router_ip = ".".join(self.router.ip.split(".")[:2] + [str(self.network_router_third_octet)] + self.router.ip.split(".")[3:])
                    break
                else:
                    continue

        def __delete_interface_DHCP_config(self):
            sections = self.interface_config_content.split("\n\n")
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
                    self.router._execute_ssh_command(f"mv {temp_file} /etc/config/network")
                    self.interface_config_content = new_file_content
                except Exception as e:
                    logger.info(f"An error occurred while deleting DHCP interface for network {self.network_name}: {e}")
                finally:
                    logger.info(f"{self.network_name} DHCP section deleted successfully from interface.")
            else:
                logger.info(f"No DHCP section found for {self.network_name} in the interface configuration.")

        def __update_interface_config(self):
            """Update /etc/config/network with the new config that has a static ip in it"""

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
        option device 'wlan0'
"""
            try:
                # Check if the configuration already exists
                if interface_static_config.strip() not in self.interface_config_content:
                    # Append the configuration if it doesn't exist
                    self.router._execute_ssh_command(f'echo "{interface_static_config}" >> /etc/config/network; wifi reload')
                else:
                    logger.info(f"Static IP configuration for {self.network_name} already exists.")
            except Exception as e:
                logger.info(f"An error occurred while updating interface static config for {self.network_name} network: {e}")
            else:
                logger.info(f"Finished adding static interface config for {self.network_name} network")

        def __update_firewall_config(self):
            firewall_config_path = "/etc/config/firewall"
            updated_config = ""

            current_config = self.router._execute_ssh_command(f"cat {firewall_config_path}")
            for line in current_config.split("\n"):
                if "config zone" in line and "'3'" in line:
                    updated_config += line + "\n"
                    continue

                if "option network" in line and "wan" in line:
                    # Check if self.network_name is already in the line
                    if self.network_name not in line:
                        # pattern=> what to replace, replacement=> with what, original_string=> where
                        # This is a RegEx for both pattern and replacement for it.
                        updated_line = re.sub(r"option network '(.+?)'", f"option network '\\1 {self.network_name}'", line)
                        updated_config += updated_line + "\n"
                    else:
                        # If self.network_name is already there, just add the line as is
                        updated_config += line + "\n"
                    continue

                updated_config += line + "\n"
            try:
                self.router._execute_ssh_command(command=None, file_path=firewall_config_path, file_contents=updated_config)
            except Exception as e:
                logger.info(f"An error occurred while updating the firewall config with {self.network_name} network: {e}")
            else:
                logger.info(f"Updated the firewall config with the new network {self.network_name}")
                # connecting and disconnecting with target router. To set the target router with the static route
                logger.info("Will disconnect and connect with the target router")
                self.router.change_wifi_visibility("False")
                self.router.change_wifi_visibility("True")

        def __add_static_route(self):
            while not self.router.check_network_connection(self.network_router_ip):
                continue

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
                current_network_config = self.router._execute_ssh_command(command="cat /etc/config/network", ip=self.network_router_ip)

                # Check if the static route configuration already exists
                if static_route_config.strip() not in current_network_config:
                    # Append the configuration if it doesn't exist
                    self.router._execute_ssh_command(f'echo "{static_route_config}" >> /etc/config/network; wifi reload;', ip=self.network_router_ip)
                else:
                    logger.info(f"Static route configuration for {self.network_name} already exists.")
            except Exception as e:
                logger.info(f"An error occurred while making static route for {self.network_name} network: {e}")
            else:
                logger.info(f"Finished processing static route for {self.network_name} network")

    def connect_to_network(self, network_name, network_mac, network_forth_octet=150):
        """Delegating the call to the ConnectToNetwork instance"""
        return self.wifi_connect.driver(network_name, network_mac, network_forth_octet)

    class WifiNetworkDeletion:
        def __init__(self, router):
            self._router = router
            self.networks = None
            # The IP address of current router as a client in the network of the target router
            self.current_router_client_address = None
            self.network_router_ip = None

        def driver(self, keyword):
            self.network_name = keyword
            # Delete the connection with target segment
            self.delete_network_profile()
            pass

        def delete_network_profile(self):
            """Remove network from `wireless.config` or `network.config`"""
            try:
                for dir_location in ["wireless", "network"]:
                    self._process_directory(dir_location)

                # Process the firewall directory separately
                self._process_firewall_directory()

            except Exception as e:
                logger.error("An error occurred:", e)
            finally:
                self._router._execute_ssh_command("wifi reload")

        def _process_directory(self, dir_location):
            """Process wireless or network directory."""
            output = self._router._execute_ssh_command(f"cat /etc/config/{dir_location}")
            file_content = output

            sections = file_content.split("\n\n")
            updated_content = ""
            section_to_delete = None

            for section in sections:
                if self.network_name in section:
                    section_to_delete = section
                    self._extract_ip_address(section)
                    break
                else:
                    updated_content += section + "\n\n"

            if section_to_delete:
                self._update_config_file(dir_location, section_to_delete, updated_content)

            else:
                logger.info(f"{self.network_name} not found in {dir_location}.")

        def _process_firewall_directory(self):
            """Process firewall directory."""
            dir_location = "firewall"
            output = self._router._execute_ssh_command(f"cat /etc/config/{dir_location}")
            file_content = output

            if self.network_name in file_content:
                updated_content = file_content.replace(self.network_name, "").strip()
                temp_file = f"/tmp/{dir_location}.conf"

                self._router._execute_ssh_command(None, file_path=temp_file, file_contents=updated_content)
                self._router._execute_ssh_command(f"mv {temp_file} /etc/config/{dir_location}")
                logger.info(f"{self.network_name} deleted successfully from {dir_location} config.")
            else:
                logger.info(f"{self.network_name} not found in {dir_location}.")

        def _extract_ip_address(self, section):
            """Extract IP address from a section."""
            for line in section.split("\n"):
                if "option ipaddr" in line:
                    ip_address = line.split("'")[1]
                    # Will return 192.168.X.150
                    self.current_router_client_address = ip_address
                    ip_parts = ip_address.split(".")
                    ip_parts[-1] = "1"
                    modified_ip_address = ".".join(ip_parts)
                    self.network_router_ip = modified_ip_address
                    logger.info(f"Current router's IP as client in {self.network_name} is {self.current_router_client_address}")
                    self.static_route()
                    break

        def _update_config_file(self, dir_location, section_to_delete, updated_content, ip=None):
            """Update the configuration file."""
            temp_file = f"/tmp/{dir_location}.conf"
            updated_content = updated_content.replace(section_to_delete, "").strip()

            self._router._execute_ssh_command(None, file_path=temp_file, file_contents=updated_content, ip=ip)
            self._router._execute_ssh_command(f"mv {temp_file} /etc/config/{dir_location}", ip=ip)
            logger.info(f"{self.network_name} section deleted successfully from {dir_location}.")

        def static_route(self):
            """SSH to target router and delete static route with current segment from it"""
            dir_location = "network"
            try:
                # Retrieve current network configuration
                current_network_config = self._router._execute_ssh_command(command=f"cat /etc/config/{dir_location}", ip=self.network_router_ip)
                # Split the file into sections based on empty lines
                sections = current_network_config.split("\n\n")
                updated_content = ""
                section_to_delete = None

                for section in sections:
                    if "option gateway" in section and self.current_router_client_address in section:
                        section_to_delete = section
                        break
                    else:
                        updated_content += section + "\n\n"

                if section_to_delete:
                    # Use the existing method to update the config file
                    self._update_config_file(dir_location, section_to_delete, updated_content, ip=self.network_router_ip)
                    logger.info(f"{self.network_name} gateway deleted successfully from {dir_location}.")
                else:
                    logger.info(f"Gateway with address {self.current_router_client_address} not found in any {dir_location} section.")

            except Exception as e:
                logger.error(f"An error occurred while deleting static route with {self.network_name} network: {e}")
            else:
                logger.info(f"Deleted static route with {self.network_name} network")
            pass

    def delete_network(self, network_name):
        return self.wifi_delete.driver(network_name)


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

# TESTED AND WORKING ON
# Firmware version :RUT9_R_00.07.06.1
# Firmware build date: 2024-01-02 11:11:13
# Internal modem firmware version: SLM750_4.0.6_EQ101
# Kernel version: 5.4.259


import logging
import subprocess
import time
import traceback

import paramiko

# Declaring the logger
logging.basicConfig(format="%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(lineno)d %(message)s", datefmt="%Y-%m-%d %H:%M:%S %p")

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

    def __close_ssh_connection(self):
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

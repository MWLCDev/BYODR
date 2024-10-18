import subprocess


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

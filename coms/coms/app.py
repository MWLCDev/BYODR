import logging
from byodr.utils.ip_getter import get_ip_number
from byodr.utils.ssh_to_router import get_router_arp_table, get_filtered_router_arp_table
from .server import start_server
from .client import connect_to_server


# Declaring the logger
logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s', datefmt='%Y%m%d:%H:%M:%S %p %Z')
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)


if __name__ == "__main__":

    # Getting the 3rd digit of the IP of the local device
    local_third_ip_digit = get_ip_number()

    while True:

        arp_list = get_router_arp_table()  
        logger.info(f"Output whole list:\n<{arp_list}> from 192.168.{local_third_ip_digit}.1")

        filtered_list = get_filtered_router_arp_table(arp_list, local_third_ip_digit)

        # Created a string for logging due to messy output i had before
        log_string = "IP address".ljust(20) + "Flags\n"
        for entry in filtered_list:
            log_string += entry['IP address'].ljust(20) + entry['Flags'] + "\n"

        logger.info(f"Output filtered list:\n{log_string}from 192.168.{local_third_ip_digit}.1")

    # Here we statically assume that if a segment has an ip of 192.168.2.0, its the lead
    if local_third_ip_digit == "2":
        logger.info(f"Starting the server code...")
        start_server()

    # All other ips will be followers
    else:
        logger.info(f"Starting the client code...")
        connect_to_server()

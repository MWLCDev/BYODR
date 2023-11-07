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

    arp_list = get_router_arp_table()  
    filtered_list = get_filtered_router_arp_table(arp_list, local_third_ip_digit)

    # To be able too see a nice table on logger
    log_string = "IP address".ljust(20) + "Flags\n"
    for entry in filtered_list:
        log_string += entry['IP address'].ljust(20) + entry['Flags'] + "\n"

    logger.info(f"Output filtered list:\n{log_string}from 192.168.{local_third_ip_digit}.1")

    # Since robot includes at least 2 segments. 
    # First one will be server all the time and second one will be a server for the follower one of itself
    start_server()

    # All other ips will be clients except the first segment of the robot
    if local_third_ip_digit != '1':
        logger.info(f"Starting the client code...")
        connect_to_server()

import logging
import socket
import time
from byodr.utils.ip_getter import get_ip_number


logger = logging.getLogger(__name__)
log_format = "%(levelname)s: %(filename)s %(funcName)s %(message)s"

# Getting the 3rd digit of the IP of the local device
local_third_ip_digit = get_ip_number()

# Setting the lead's IP, assuming that it will always be -1 less than the local one
lead_third_ip_digit = str ( int(local_third_ip_digit) - 1 )

# Setting the follower's IP, assuming that it will always be +1 more than the local one
follower_third_ip_digit = str ( int(local_third_ip_digit) + 1 )



def main():
    logger.info("Running test service")



    # The lead segment's IP address
    HOST = "192.168." + lead_third_ip_digit + ".100"

    # The port used by the server on the lead segment
    PORT = 1111

    while(True):
        logger.info(f"Printing server's credentials: {HOST}:{PORT}")
        time.sleep(3)

    # with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    #     s.connect((HOST, PORT))
    #     s.sendall(b"Hello, world")
    #     data = s.recv(1024)

    # print(f"Received {data!r}")


if __name__ == "__main__":
    logging.basicConfig(format=log_format)
    logging.getLogger().setLevel(logging.INFO)
    main()
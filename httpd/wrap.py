#!/usr/bin/env python
from __future__ import absolute_import

import argparse
import logging
import os
import re
import shutil
import subprocess
import configparser

logger = logging.getLogger(__name__)

log_format = '%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s'


# Declaring the function to get the IP here, because for some reason,
# it cannot have access to the common/byodr folder where the util functions reside
def get_ip_number():
    config = configparser.ConfigParser()
    config.read("/config/config.ini")
    front_camera_ip = config["camera"]["front.camera.ip"]
    parts = front_camera_ip.split('.')
    
    return parts[2] 


# Reads the haproxy.conf file
def _check_config(config_file):
    with open(config_file, 'r') as _file:
        contents = _file.read()
    if 'version 0.66.0' in contents:
        logger.info("The proxy configuration is up to date.")
    else:
        # Not all routers are at the default ip.
        _ip = re.findall("rover.*:9101", contents)[0][6:-5]
        _ssl = ('ssl crt' in contents)
        #haproxy is a load balancer
        with open('haproxy_ssl.template' if _ssl else 'haproxy.template', 'r') as _template:
            with open(config_file, 'w') as _file:
                _file.write(_template.read().replace('192.168.' + get_ip_number() + '.32', _ip))
        logger.info("Updated the existing proxy configuration using ip '{}'.".format(_ip))


def main():
    parser = argparse.ArgumentParser(description='Http proxy server.')
    parser.add_argument('--config', type=str, default='/config/haproxy.conf', help='Configuration file.')
    args = parser.parse_args()

    config_file = args.config

    # Check if the file exists
    if os.path.exists(config_file):
        _check_config(config_file)
    
    # If it doesnt exist, we create one from an existing template
    else:
        shutil.copyfile('haproxy.template', config_file)
        logger.info("Created a new non ssl proxy configuration.")
    subprocess.call(['/usr/sbin/haproxy', '-f', config_file])


if __name__ == "__main__":
    logging.basicConfig(format=log_format, datefmt='%Y%m%d:%H:%M:%S %p %Z')
    logging.getLogger().setLevel(logging.INFO)
    main()

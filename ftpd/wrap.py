#!/usr/bin/env python
from __future__ import absolute_import

import logging
import os
import subprocess

logger = logging.getLogger(__name__)

log_format = "%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s"

_MAIN_COMMAND = ["/usr/sbin/pure-ftpd", "-P", "localhost", "-p", "30000:30009", "-l", "puredb:/etc/pureftpd/pureftpd.pdb", "-E", "-j", "-R"]


def main():
    pw_file = os.path.join(os.path.sep, "etc", "pureftpd", "pureftpd.passwd")
    if not os.path.exists(pw_file):
        try:
            subprocess.check_call(["/app/create_user.sh"])
            logger.info("Created the default ftp user.")
        except subprocess.CalledProcessError as e:
            logger.error("Failed to create user: {}".format(e))
        except PermissionError as e:
            logger.error("Permission denied: {}".format(e))
    try:
        subprocess.check_call(_MAIN_COMMAND)
    except subprocess.CalledProcessError as e:
        logger.error("Failed to start FTP service: {}".format(e))
    except PermissionError as e:
        logger.error("Permission denied: {}".format(e))


if __name__ == "__main__":
    logging.basicConfig(format=log_format, datefmt="%Y%m%d:%H:%M:%S %p %Z")
    logging.getLogger().setLevel(logging.INFO)
    main()

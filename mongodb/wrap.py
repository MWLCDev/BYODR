#!/usr/bin/env python
from __future__ import absolute_import

import logging
import os
import subprocess

logger = logging.getLogger(__name__)

log_format = "%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s"


def main():
    pw_file = os.path.join(os.path.sep, "config", "mongo-root")
    if not os.path.exists(pw_file):
        # Change the file mode of current process, to ensure the file is created without any permissions for group or others
        os.umask(0)
        # Creates the file with write permission only for the owner (0o600 means read/write permissions for owner, and no permissions for others).
        with open(os.open(pw_file, os.O_CREAT | os.O_WRONLY, 0o600), "w") as fh:
            # Writes the string 'robot' to the file.
            fh.write("robot")
        # Logs an info message "Created the default mongo user."
        logger.info("Created the default mongo user.")
        # "--syslog": log to the system logger
        # "--wiredTigerCacheSizeGB": set the WiredTiger internal cache size in GB
        # "--bind_ip": specifies the IP address MongoDB listens on (127.0.0.1 is the localhost)
    subprocess.call(
        [
            "mongod",
            "--syslog",
            "--wiredTigerCacheSizeGB",
            "0.20",
            "--bind_ip",
            "127.0.0.1",
        ]
    )


if __name__ == "__main__":
    logging.basicConfig(format=log_format, datefmt="%Y%m%d:%H:%M:%S %p %Z")
    logging.getLogger().setLevel(logging.INFO)
    main()

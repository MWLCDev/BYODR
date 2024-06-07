#!/bin/sh

# Check if the user already exists
if ! pure-pw show rob > /dev/null 2>&1; then
    # Adding the user silently
    (echo rob; echo rob) | pure-pw useradd rob -m -u ftpuser -d /home/ftpuser > /dev/null 2>&1
    echo "User 'rob' created."
else
    echo "User 'rob' already exists. No need to create."
fi

# Use the official Ubuntu 20.04 base image
FROM ubuntu:20.04

# Set environment variables to avoid prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install required system packages
RUN apt-get update && \
  apt-get install -y gnupg curl python3 python3-pip software-properties-common

# Add the MongoDB repository for version 4.4
RUN curl -fsSL https://www.mongodb.org/static/pgp/server-4.4.asc | apt-key add - && \
  echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/4.4 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-4.4.list

# Update package list and install MongoDB
RUN apt-get update && \
  apt-get install -y mongodb-org=4.4.18 mongodb-org-server=4.4.18 mongodb-org-shell=4.4.18 mongodb-org-mongos=4.4.18 mongodb-org-tools=4.4.18


# Set environment variables for MongoDB
ENV MONGO_INITDB_ROOT_USERNAME=admin
ENV MONGO_INITDB_ROOT_PASSWORD=robot

# Expose MongoDB default port
EXPOSE 27017

# Copy the Python script and any other necessary files into the container
COPY ./mongodb /app/mongodb
WORKDIR /app/mongodb


# Set the entrypoint to run the Python script that manages MongoDB
CMD ["python3", "wrap.py"]
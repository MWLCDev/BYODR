# # Use an official Raspberry Pi OS image as the base
# FROM balenalib/raspberrypi4-64-debian-python:3.9-buster-build-20240429
# Use the official Raspberry Pi OS base image
FROM balenalib/raspberrypi4-64-debian-python:3.9-bullseye-build-20240429

# Install dependencies
RUN apt-get update && apt-get install -y \
  python3-dev \
  libgstreamer1.0-dev \
  libgstreamer-plugins-base1.0-dev \
  libgstreamer-plugins-bad1.0-dev \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-ugly \
  gstreamer1.0-libav \
  gstreamer1.0-tools \
  gstreamer1.0-x \
  gstreamer1.0-alsa \
  gstreamer1.0-gl \
  libgirepository1.0-dev \
  libcairo2-dev \
  curl \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install pip using get-pip.py
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
  python3 get-pip.py && \
  rm get-pip.py

# Upgrade pip and install setuptools and wheel
RUN python3 -m pip install --upgrade pip setuptools wheel

# Install PyGObject
RUN python3 -m pip install PyGObject tornado numpy six pyzmq

# Copy your application files
COPY ./BYODR_utils/common/ /app/BYODR_utils/common/
COPY ./BYODR_utils/PI_specific/ /app/BYODR_utils/PI_specific/
COPY ./stream /app/stream

# Set PYTHONPATH environment variable
ENV PYTHONPATH "/app:${PYTHONPATH}"

# Set the working directory
WORKDIR /app/stream



# # Set the default command to keep the container running
# CMD ["sleep", "infinity"]

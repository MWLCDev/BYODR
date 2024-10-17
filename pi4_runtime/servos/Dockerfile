# Use the balenalib image with Python 3.10 pre-installed
FROM balenalib/raspberrypi4-64-ubuntu-python:3.10-focal-20240429

ENV UDEV=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
  build-essential \
  git \
  usbutils \
  i2c-tools \
  python3-cachetools \
  python3-smbus \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir pymodbus pyusb pytest crccheck RPi.GPIO  numpy six pyzmq cython pythoncrc pyserial gpiozero

RUN git clone https://github.com/LiamBindle/PyVESC.git \
  && cd PyVESC \
  && sed -i 's/return f"{self.comm_fw_version}.{self.fw_version_major}.{self.fw_version_minor}"/return "{self.comm_fw_version}.{self.fw_version_major}.{self.fw_version_minor}"/' pyvesc/VESC/messages/getters.py \
  && python3 setup.py build \
  && python3 setup.py install

# Copy application files
COPY ./BYODR_utils/common/ /app/BYODR_utils/common/
COPY ./BYODR_utils/PI_specific/ /app/BYODR_utils/PI_specific/

COPY ./servos /app/servos
ENV PYTHONPATH "/app:${PYTHONPATH}"

WORKDIR /app/servos

CMD ["python", "app.py"]
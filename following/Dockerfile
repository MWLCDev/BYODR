FROM ultralytics/ultralytics:latest-jetson
#FROM ultralytics/ultralytics:latest-arm64


RUN apt-get update && apt-get install -y \
  build-essential \
  python3-dev \
  python3-pip

# Install necessary Python libraries
RUN python3 -m pip install --upgrade pip
# libraries from utils libraries
RUN python3 -m pip install numpy pyzmq

# Copy your application files
COPY ./common/ /common/
COPY ./following/ /app/
WORKDIR /app

# Set PYTHONPATH environment variable
ENV PYTHONPATH "${PYTHONPATH}:/common"

# Command to run your application
CMD ["python3", "app.py"]
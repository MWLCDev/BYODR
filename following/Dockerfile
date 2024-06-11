FROM  mwlvdev/jetson-nano-ubuntu:bionic-torch1.10-cp38-cuda10.2-TRT


RUN apt-get update && apt-get install -y \
  build-essential \
  python3-dev \
  python3-pip

# Install necessary Python libraries
RUN /bin/bash -c "source /venv/bin/activate && pip install --no-cache --upgrade pip"
# libraries from utils libraries
RUN /bin/bash -c "source /venv/bin/activate && pip install --no-cache pip install numpy pyzmq lap simple-pid"

# Copy your application files
COPY ./common/ /common/
COPY ./following/ /app/
WORKDIR /app

# Set PYTHONPATH environment variable
ENV PYTHONPATH "${PYTHONPATH}:/common"

# Command to run your application
CMD ["/bin/bash", "-c", "source /venv/bin/activate && python3 app.py"]
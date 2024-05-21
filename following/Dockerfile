FROM  mwlvdev/jetson-nano-ubuntu:bionic-torch1.10-cp38-cuda10.2-TRT

#(AM to Mb: I think you should remove these. The whole docker image is running inside a python env made in 3.8. what you are installing here is 3.6)
RUN apt-get update && apt-get install -y \
  build-essential \
  python3-dev \
  python3-pip

# Install necessary Python libraries inside the python env
RUN /bin/bash -c "source /venv/bin/activate && pip install --no-cache --upgrade pip"
# libraries from utils libraries
RUN /bin/bash -c "source /venv/bin/activate && pip install --no-cache pip install numpy pyzmq lap simple-pid"

COPY ./common/ /common/
COPY ./following/ /app/
WORKDIR /app

# Set PYTHONPATH environment variable
ENV PYTHONPATH "${PYTHONPATH}:/common"

# Command to run app.py inside the python env
CMD ["/bin/bash", "-c", "source /venv/bin/activate && python3 app.py"]
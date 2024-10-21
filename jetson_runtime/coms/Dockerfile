FROM centipede2donald/ubuntu-bionic:python36-opencv32-gstreamer10

RUN apt-get update && apt-get install -y \
  build-essential \
  libssl-dev \
  libffi-dev \
  python3-dev \
  python3-pip \
  libxml2-dev \
  libxslt1-dev \
  unzip  

RUN python3 -m pip install -U pip
RUN pip3 install paramiko pythonping


# Copy application files
COPY ./BYODR_utils/common/ /app/BYODR_utils/common/
COPY ./BYODR_utils/JETSON_specific/ /app/BYODR_utils/JETSON_specific/

COPY ./coms /app/coms
ENV PYTHONPATH "/app:${PYTHONPATH}"
WORKDIR /app/coms/coms

# CMD ["ls"]
CMD ["python3", "app.py","--name", "coms"]
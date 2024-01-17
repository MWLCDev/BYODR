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
RUN pip3 install paramiko

COPY ./common common/
COPY ./coms app/
WORKDIR /app

ENV PYTHONPATH "${PYTHONPATH}:/common"
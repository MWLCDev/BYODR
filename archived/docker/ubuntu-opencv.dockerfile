# docker build -f <name> -t centipede2donald/ubuntu-bionic:python27-opencv32 .
# docker buildx build --platform linux/arm64,linux/amd64 --push -f <name> -t centipede2donald/ubuntu-bionic:python27-opencv32 .
FROM ubuntu:bionic

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python-dev \
    python-opencv \
    python-pandas \
    python-pip \
    python-setuptools \
    python-wheel \
    python-zmq \
 && rm -rf /var/lib/apt/lists/*

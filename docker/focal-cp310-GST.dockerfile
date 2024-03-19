# docker buildx create --name mynewbuilder --use
# docker buildx use mybuilder
# docker buildx build --platform linux/arm64,linux/amd64 -t mwlvdev/jetson-nano-ubuntu:focal-cp310-GST . --push
FROM ubuntu:focal-20240123

# Set a non-interactive frontend
ENV DEBIAN_FRONTEND noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libbz2-dev \
    liblzma-dev \
    libxml2-dev \
    libxmlsec1-dev \
    libssl-dev \    
    zlib1g-dev \    
    wget \
    python-dev \
    nano \
    openssh-client \
    lm-sensors \
    software-properties-common

# Download Python 3.10, compile it, and install
RUN cd /tmp && \
    wget https://www.python.org/ftp/python/3.10.0/Python-3.10.0.tgz && \
    tar -xzf Python-3.10.0.tgz && \
    cd Python-3.10.0 && \
    ./configure --enable-optimizations && \
    make -j 18 && \
    make altinstall

# Remove the Python source and temporary files
RUN rm -rf /tmp/Python-3.10.0 /tmp/Python-3.10.0.tgz

# Update pip for Python 3.10
RUN python3.10 -m ensurepip && \
    python3.10 -m pip install --upgrade pip

# Set Python 3.10 as the default Python version
RUN update-alternatives --install /usr/bin/python python /usr/local/bin/python3.10 1 && \
    update-alternatives --set python /usr/local/bin/python3.10 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/local/bin/python3.10 1 && \
    update-alternatives --set python3 /usr/local/bin/python3.10


# Install additional dependencies for pygobject
RUN apt-get install -y --no-install-recommends \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-doc \
    gstreamer1.0-tools \
    gstreamer1.0-x \
    gstreamer1.0-alsa \
    gstreamer1.0-gl \
    gstreamer1.0-gtk3 \
    gstreamer1.0-qt5 \
    python3-gi\
    python-gi-dev\
    python3-gst-1.0\
    python-gobject\
    libgtk-3-dev\
    gstreamer1.0-pulseaudio \
    libreadline-dev \
    zlib1g-dev \
    libgirepository1.0-dev build-essential \
    libbz2-dev\
    libssl-dev\ 
    libsqlite3-dev\ 
    curl\
    llvm\ 
    libncurses5-dev \
    python3-gi-cairo\
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libcairo2-dev\
    gir1.2-gtk-3.0\
    libgstreamer1.0-0 &&\
    apt-get -y clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python packages using pip
RUN python3.10 -m pip install cachetools jsoncomment requests pytest pymodbus geographiclib numpy zmq six configparser PyGObject


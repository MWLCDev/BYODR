# docker build -f tf113-jp43.dockerfile -t centipede2donald/nvidia-jetson:jp43-cp27-tf113-2 .
FROM balenalib/jetson-nano-ubuntu:bionic as buildstep

WORKDIR /app

# Download with the nvidia sdk manager
COPY /cuda-repo-l4t-10-0*.deb .
COPY /libcudnn7_*.deb .

ENV DEBIAN_FRONTEND noninteractive

RUN dpkg -i cuda-repo-l4t-10-0-local-10.0.326_1.0-1_arm64.deb && \
    apt-key add /var/cuda-repo-10-0-local-10.0.326/*.pub && \
    apt-get update && \
    apt-get install -y cuda-toolkit-10-0 ./libcudnn7_7.6.3.28-1+cuda10.0_arm64.deb && \
    rm -rf *.deb && \
    dpkg --remove cuda-repo-l4t-10-0-local-10.0.326 && \
    dpkg -P cuda-repo-l4t-10-0-local-10.0.326 && \
    echo "/usr/lib/aarch64-linux-gnu/tegra" > /etc/ld.so.conf.d/nvidia-tegra.conf && \
    ldconfig

RUN rm -rf /usr/local/cuda-10.0/doc

FROM balenalib/jetson-nano-ubuntu:bionic as final

COPY --from=buildstep /usr/local/cuda-10.0 /usr/local/cuda-10.0
COPY --from=buildstep /usr/lib/aarch64-linux-gnu /usr/lib/aarch64-linux-gnu
COPY --from=buildstep /usr/local/lib /usr/local/lib

WORKDIR /app

COPY /nvidia_drivers.tbz2 .
COPY /config.tbz2 .

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install lbzip2 -y && \
    tar xjf nvidia_drivers.tbz2 -C / && \
    tar xjf config.tbz2 -C / --exclude=etc/hosts --exclude=etc/hostname && \
    echo "/usr/lib/aarch64-linux-gnu/tegra" > /etc/ld.so.conf.d/nvidia-tegra.conf && ldconfig && \
    apt-get install -y --no-install-recommends \
    libhdf5-serial-dev \
    hdf5-tools \
    libhdf5-dev \
    build-essential \
    python-dev \
    python-opencv \
    python-pandas \
    python-pip \
    python-setuptools \
    python-wheel \
    python-zmq \
    python-h5py \
    zlib1g-dev zip \
    libjpeg8-dev \
    liblapack-dev \
    libblas-dev \
    gfortran \
    wget && \
    apt-get -y clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf *.tbz2

RUN pip install "jsoncomment==0.3.3" && \
  pip install "numpy==1.16.6" && \
  pip install "pytest==4.6.11"

# From https://developer.download.nvidia.com/compute/redist/jp/v411/tensorflow-gpu
COPY /tensorflow_gpu-1.13.0* .

RUN pip install tensorflow_gpu-1.13.0rc0+nv19.2-cp27-cp27mu-linux_aarch64.whl && \
    rm -rf tensorflow*.whl && \
    rm -rf /root/.cache

ENV LD_LIBRARY_PATH=/usr/local/cuda-10.0/lib64
ENV LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/local/cuda-10.0/targets/aarch64-linux/lib
ENV LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/lib/aarch64-linux-gnu
ENV LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/lib/aarch64-linux-gnu/tegra

WORKDIR /
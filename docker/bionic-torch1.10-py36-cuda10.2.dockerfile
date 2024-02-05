# This pytorch version is strictly built with cp36. I did try to have a cp310 version
#    [torch-1.10.0-cp39-cp39-manylinux2014_aarch64.whl](https://files.pythonhosted.org/packages/03/f6/67e0ef29a03fd1cf585bdec03eb3aaf9f00498474f5c7b59f83d9779a7f1/torch-1.10.0-cp39-cp39-manylinux2014_aarch64.whl) but it didn't work with CUDA. 

# Some links I used while making this image 
# find supported versions between pytorch and torchvision => https://catalog.ngc.nvidia.com/orgs/nvidia/containers/l4t-pytorch
# https://forums.developer.nvidia.com/t/pytorch-for-jetson/72048
# https://developer.nvidia.com/embedded/jetson-linux-archive
# Supported OS to run CUDA => https://developer.nvidia.com/cuda-10.2-download-archive?target_os=Linux&target_arch=x86_64&target_distro=Ubuntu (most of the other OS do not have optimized version with Balena os)
# Download wheel version for pytorch (in case of updating) => https://download.pytorch.org/whl/torch/
# find optimized builds made for Nano on Balena => Nvidia Jetson Nano SD-CARD in https://docs.balena.io/reference/base-images/base-images-ref/
# numpy build https://gitlab.com/pdboef/tensorrt-balena/-/blob/master/Dockerfile.tensorrt and https://github.com/zrzka/python-wheel-aarch64/releases
# for tensorflow https://gitlab.com/pdboef/tensorrt-balena/-/tree/master from https://forums.balena.io/t/jetson-nano-image-with-tensorrt-for-python-projects/19272
# main optimized blena docker image => https://github.com/balena-io-library/base-images/blob/master/balena-base-images/device-base/jetson-nano/ubuntu/bionic/run/Dockerfile
# the python optimized image =>https://github.com/balena-io-library/base-images/blob/master/balena-base-images/python/jetson-nano/ubuntu/bionic/3.9.16/run/Dockerfile

#Images to switch between
# FROM balenalib/jetson-nano-ubuntu-python:bionic 
# FROM balenalib/jetson-nano-ubuntu-python:3.6-bionic-run 

# Image name : jetson-nano-torch1.10-py36-cuda10.2
# FROM balenalib/jetson-nano-ubuntu:bionic
FROM balenalib/jetson-nano-ubuntu:bionic

# Combine ENV statements and don't prompt with any configuration questions
ENV DEBIAN_FRONTEND=noninteractive \
  CUDA_HOME=/usr/local/cuda-10.2 \
  UDEV=1

# Update to 32.7 repository, add Universe repository, and install required packages
RUN sed -i 's/r32.6 main/r32.7 main/g' /etc/apt/sources.list.d/nvidia.list && \
  apt-get update -qq && \
  apt-get install -y --no-install-recommends software-properties-common && \
  add-apt-repository universe && \
  apt-get install -y --no-install-recommends lbzip2 git wget unzip jq xorg tar python3 libegl1 binutils \
  python3-gi python3-dev python3-gst-1.0 python3-pip \
  nvidia-l4t-cuda nvidia-cuda libopenmpi-dev cuda-toolkit-10-2 \
  cuda-samples-10-2 libcudnn8 libopenblas-base libomp-dev python3-zmq

# Clean up in a separate RUN command to enforce your requirement
RUN apt-get clean && \
  rm -rf /var/lib/apt/lists/* /usr/local/cuda-10.2/doc

RUN pip3 install --upgrade pip --quiet

# Install BSP binaries for L4T 32.7.2 if they don't exist and perform cleanup
RUN if [ ! -f jetson-210_linux_r32.7.2_aarch64.tbz2 ]; then \
  wget -q https://developer.nvidia.com/embedded/l4t/r32_release_v7.2/t210/jetson-210_linux_r32.7.2_aarch64.tbz2; \
  fi && \
  if [ -f jetson-210_linux_r32.7.2_aarch64.tbz2 ]; then \
  tar xf jetson-210_linux_r32.7.2_aarch64.tbz2 && \
  cd Linux_for_Tegra && \
  sed -i 's/config.tbz2\"/config.tbz2\" --exclude=etc\/hosts --exclude=etc\/hostname/g' apply_binaries.sh && \
  sed -i 's/install --owner=root --group=root \"${QEMU_BIN}\" \"${L4T_ROOTFS_DIR}\/usr\/bin\/\"/#install --owner=root --group=root \"${QEMU_BIN}\" \"${L4T_ROOTFS_DIR}\/usr\/bin\/\"/g' nv_tegra/nv-apply-debs.sh && \
  sed -i 's/chroot . \//  /g' nv_tegra/nv-apply-debs.sh && \
  ./apply_binaries.sh -r / --target-overlay && cd .. && \
  rm -rf jetson-210_linux_r32.7.2_aarch64.tbz2 Linux_for_Tegra; \
  fi && \
  echo "/usr/lib/aarch64-linux-gnu/tegra" > /etc/ld.so.conf.d/nvidia-tegra.conf && ldconfig

# PyTorch installation with quiet flag to suppress progress output
ARG PYTORCH_URL=https://nvidia.box.com/shared/static/fjtbno0vpo676a25cgvuqc1wty0fkkg6.whl
ARG PYTORCH_WHL=torch-1.10.0-cp36-cp36m-linux_aarch64.whl
RUN wget -q --no-check-certificate ${PYTORCH_URL} -O ${PYTORCH_WHL} && \
  pip3 install ${PYTORCH_WHL} --quiet && \
  rm ${PYTORCH_WHL}

# Numpy installation with quiet flag
ARG WHL_URL_PREFIX=https://github.com/zrzka/python-wheel-aarch64/releases/download/jetson-nano-1.1
RUN curl -LO ${WHL_URL_PREFIX}/numpy-1.16.4-cp36-cp36m-linux_aarch64.whl && \
  python3 -m pip install numpy-1.16.4-cp36-cp36m-linux_aarch64.whl --quiet && \
  rm numpy-1.16.4-cp36-cp36m-linux_aarch64.whl
# Files inside yolo config directory will be referred to as /workspace/ultralytics/ultralytics/cfg/models/v8/ 
# building command ==> docker buildx build --platform linux/arm64,linux/amd64 -t mwlvdev/jetson-nano-ubuntu:bionic-torch1.10-cp38-cuda10.2 . --push
# Start from the base image
FROM balenalib/jetson-nano-ubuntu:bionic

# Environment variables for non-interactive installation and path configuration
ENV DEBIAN_FRONTEND noninteractive
ENV PATH="/workspace/ultralytics/venv/bin:$PATH"

# Add Kitware GPG key to avoid errors on apt-get update
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 1A127079A92F09ED

# Add Kitware GPG key, update sources list for Nvidia, and install dependencies
RUN apt-get update && \
  # Update to 32.7 repository in case the base image is using 32.6
  sed -i 's/r32.6 main/r32.7 main/g' /etc/apt/sources.list.d/nvidia.list && \
  apt-get install -y --no-install-recommends cuda-toolkit-10-2 cuda-samples-10-2 libcudnn8 lbzip2 xorg wget tar libegl1 git \
  python3.8 python3.8-venv python3.8-dev python3-pip \
  libopenmpi-dev libomp-dev libopenblas-dev libblas-dev libeigen3-dev libcublas-dev && \
  # Clean up
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

# Download and install BSP binaries for L4T 32.7.2, and perform configurations
RUN wget https://developer.nvidia.com/embedded/l4t/r32_release_v7.2/t210/jetson-210_linux_r32.7.2_aarch64.tbz2 && \
  tar xf jetson-210_linux_r32.7.2_aarch64.tbz2 && \
  cd Linux_for_Tegra && \
  sed -i 's/config.tbz2\"/config.tbz2\" --exclude=etc\/hosts --exclude=etc\/hostname/g' apply_binaries.sh && \
  sed -i 's/install --owner=root --group=root \"${QEMU_BIN}\" \"${L4T_ROOTFS_DIR}\/usr\/bin\/\"/#install --owner=root --group=root \"${QEMU_BIN}\" \"${L4T_ROOTFS_DIR}\/usr\/bin\/\"/g' nv_tegra/nv-apply-debs.sh && \
  sed -i 's/chroot . \//  /g' nv_tegra/nv-apply-debs.sh && \
  ./apply_binaries.sh -r / --target-overlay && cd .. && \
  rm -rf jetson-210_linux_r32.7.2_aarch64.tbz2 Linux_for_Tegra && \
  echo "/usr/lib/aarch64-linux-gnu/tegra" > /etc/ld.so.conf.d/nvidia-tegra.conf && ldconfig

# Setup the working environment
WORKDIR /workspace

# Clone the YOLOv8 repository and setup Python environment
RUN git clone https://github.com/ultralytics/ultralytics.git && \
  cd ultralytics && \
  python3.8 -m venv venv && \
  pip install -U pip wheel gdown && \
  # Download pre-built PyTorch and TorchVision packages and install
  gdown https://drive.google.com/uc?id=1hs9HM0XJ2LPFghcn7ZMOs5qu5HexPXwM && \
  gdown https://drive.google.com/uc?id=1m0d8ruUY8RvCP9eVjZw4Nc8LAwM8yuGV && \
  pip install torch-*.whl torchvision-*.whl && \
  rm torch-*.whl torchvision-*.whl && \
  # Install the Python package for YOLOv8
  pip install .
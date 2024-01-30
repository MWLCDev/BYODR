FROM balenalib/jetson-nano-ubuntu:bionic

# Don't prompt with any configuration questions
ENV DEBIAN_FRONTEND=noninteractive
ENV CUDA_HOME=/usr/local/cuda-10.2
ENV UDEV=1
ENV PYTHONPATH="${PYTHONPATH}:/common"

# Update to 32.7 repository, add Universe repository, and install required packages in a single RUN to minimize layers
RUN sed -i 's/r32.6 main/r32.7 main/g' /etc/apt/sources.list.d/nvidia.list && \
  apt-get update -qq && \
  apt-get install -y --no-install-recommends software-properties-common && \
  add-apt-repository universe && \
  apt-get install -y --no-install-recommends lbzip2 git wget unzip jq xorg tar python3 libegl1 binutils \
  python3-gi python3-dev python3-gst-1.0 python3-pip \
  nvidia-l4t-cuda nvidia-cuda libopenmpi-dev cuda-toolkit-10-2 \
  cuda-samples-10-2 libcudnn8 libopenblas-base libomp-dev && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/* && \
  rm -rf /usr/local/cuda-10.2/doc

# Upgrade pip quietly
RUN pip3 install --upgrade pip --quiet

# Install BSP binaries for L4T 32.7.2 if they don't exist
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
  rm -rf jetson-210_linux_r32.7.2_aarch64.tbz2 && \
  rm -rf Linux_for_Tegra && \
  echo "/usr/lib/aarch64-linux-gnu/tegra" > /etc/ld.so.conf.d/nvidia-tegra.conf && ldconfig; \
  fi

# ----------------------------------------------------------
# PyTorch (for JetPack 4.6.1)
# ----------------------------------------------------------
#  PyTorch v1.9.0 https://nvidia.box.com/shared/static/h1z9sw4bb1ybi0rm3tu8qdj8hs05ljbm.whl (torch-1.9.0-cp36-cp36m-linux_aarch64.whl)
ARG PYTORCH_URL=https://nvidia.box.com/shared/static/fjtbno0vpo676a25cgvuqc1wty0fkkg6.whl
ARG PYTORCH_WHL=torch-1.10.0-cp36-cp36m-linux_aarch64.whl

# Install PyTorch quietly
RUN wget -q --no-check-certificate ${PYTORCH_URL} -O ${PYTORCH_WHL} && \
  pip3 install ${PYTORCH_WHL} --quiet && \
  rm ${PYTORCH_WHL}

# Libraries only for image that's not ultralytics
# ____________________________________________________
#RUN python3 -m pip install ultralytics
#RUN apt-get install -y \
#    libavcodec-dev \
#    libgstreamer1.0
#RUN python3 -m pip install opencv-python
#RUN python3 -m pip --no-cache install "opencv-python-headless<4.3" \
#    && pip3 --no-cache install "opencv-python-headless<4.3"
# ____________________________________________________

# Set Working Directory and Command
COPY ./following/ /app/
WORKDIR /app
CMD ["python3", "app.py"]

FROM ultralytics/ultralytics:8.2.48-jetson-jetpack4

# Don't prompt with any configuration questions
ENV DEBIAN_FRONTEND noninteractive

# Install some utils
RUN apt-get update && apt-get install -y lbzip2 git wget unzip jq xorg tar python3 libegl1 binutils xz-utils bzip2 build-essential python3-dev python3-pip

ENV UDEV=1

# Download and install BSP binaries for L4T 32.7.3, note new nonstandard URL
RUN \
  cd /tmp/ && wget https://developer.nvidia.com/downloads/remetpack-463r32releasev73t210jetson-210linur3273aarch64tbz2 && \
  tar xf remetpack-463r32releasev73t210jetson-210linur3273aarch64tbz2 && rm remetpack-463r32releasev73t210jetson-210linur3273aarch64tbz2 && \
  cd Linux_for_Tegra && \
  sed -i 's/config.tbz2\"/config.tbz2\" --exclude=etc\/hosts --exclude=etc\/hostname/g' apply_binaries.sh && \
  sed -i 's/install --owner=root --group=root \"${QEMU_BIN}\" \"${L4T_ROOTFS_DIR}\/usr\/bin\/\"/#install --owner=root --group=root \"${QEMU_BIN}\" \"${L4T_ROOTFS_DIR}\/usr\/bin\/\"/g' nv_tegra/nv-apply-debs.sh && \
  sed -i 's/chroot . \//  /g' nv_tegra/nv-apply-debs.sh && \
  ./apply_binaries.sh -r / --target-overlay && cd .. \
  rm -rf Linux_for_Tegra && \
  echo "/usr/lib/aarch64-linux-gnu/tegra" > /etc/ld.so.conf.d/nvidia-tegra.conf && ldconfig


RUN pip3 install --upgrade pyzmq lap simple-pid

# Copy application files
COPY ./BYODR_utils/common/ /app/BYODR_utils/common/
COPY ./BYODR_utils/JETSON_specific/ /app/BYODR_utils/JETSON_specific/

COPY ./following /app/following
ENV PYTHONPATH "/app:${PYTHONPATH}"

WORKDIR /app/following


# Command to run your application
CMD ["python3", "app.py"]
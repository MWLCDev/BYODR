# docker buildx build --platform linux/arm64,linux/amd64 -t mwlvdev/jetson-nano-ubuntu:bionic-torch1.10-cp38-cuda10.2-TRT . --push
# Use a base image with Jetson Nano support
FROM balenalib/jetson-nano-ubuntu:bionic

# Environment variables for non-interactive installation and path configuration
ENV DEBIAN_FRONTEND=noninteractive \
    PATH="/workspace/venv/bin:$PATH" \
    LD_LIBRARY_PATH="/usr/local/cuda/lib64:/usr/local/cuda/targets/aarch64-linux/lib:/usr/lib/aarch64-linux-gnu:/usr/lib/aarch64-linux-gnu/tegra:/usr/local/cuda/extras/CUPTI/lib64:/usr/lib/aarch64-linux-gnu/tegra:${LD_LIBRARY_PATH}"

# Install dependencies
RUN apt-get update && \
    sed -i 's/r32.6 main/r32.7 main/g' /etc/apt/sources.list.d/nvidia.list && \
    apt-get install -y --no-install-recommends \
    cuda-toolkit-10-2 cuda-samples-10-2 libcudnn8 lbzip2 xorg wget tar libegl1 git \
    python3.8 python3.8-venv python3.8-dev python3-pip libopenmpi-dev libomp-dev \
    libopenblas-dev libblas-dev libeigen3-dev libcublas-dev gcc apt-transport-https \
    ca-certificates curl protobuf-compiler libprotobuf-dev cmake && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install BSP binaries for L4T 32.7.2 and configure
RUN wget https://developer.nvidia.com/embedded/l4t/r32_release_v7.2/t210/jetson-210_linux_r32.7.2_aarch64.tbz2 && \
    tar xf jetson-210_linux_r32.7.2_aarch64.tbz2 && cd Linux_for_Tegra && \
    sed -i 's/config.tbz2"/config.tbz2" --exclude=etc\/hosts --exclude=etc\/hostname/g' apply_binaries.sh && \
    sed -i 's/install --owner=root --group-root "${QEMU_BIN}" "${L4T_ROOTFS_DIR}\/usr\/bin\/"/#install --owner=root --group-root "${QEMU_BIN}" "${L4T_ROOTFS_DIR}\/usr\/bin\/"/g' nv_tegra/nv-apply-debs.sh && \
    sed -i 's/chroot . \//  /g' nv_tegra/nv-apply-debs.sh && \
    ./apply_binaries.sh -r / --target-overlay && cd .. && \
    rm -rf jetson-210_linux_r32.7.2_aarch64.tbz2 Linux_for_Tegra && \
    echo "/usr/lib/aarch64-linux-gnu/tegra" > /etc/ld.so.conf.d/nvidia-tegra.conf && ldconfig

# Ensure pip is up-to-date
RUN wget https://bootstrap.pypa.io/get-pip.py -O get-pip.py && python3.8 get-pip.py && rm get-pip.py

# Create and activate virtual environment, then install the package
RUN python3.8 -m venv /venv && /venv/bin/pip install --upgrade pip

# Add NVIDIA repository for TensorRT and install
RUN curl -s -L https://repo.download.nvidia.com/jetson/jetson-ota-public.asc | apt-key add - && \
    echo "deb https://repo.download.nvidia.com/jetson/common r32.7 main" > /etc/apt/sources.list.d/nvidia-l4t-apt-source.list && \
    echo "deb https://repo.download.nvidia.com/jetson/t194 r32.7 main" >> /etc/apt/sources.list.d/nvidia-l4t-apt-source.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    libnvinfer-dev=8.2.1-1+cuda10.2 libnvinfer-plugin-dev=8.2.1-1+cuda10.2 \
    python3-libnvinfer=8.2.1-1+cuda10.2 libnvinfer8 libnvinfer-plugin8 libopencv-python && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Download and install TensorRT wheel
RUN wget -O /tmp/tensorrt-8.2.0.6-cp38-none-linux_aarch64.whl https://forums.developer.nvidia.com/uploads/short-url/hASzFOm9YsJx6VVFrDW1g44CMmv.whl && \
    /venv/bin/pip install /tmp/tensorrt-8.2.0.6-cp38-none-linux_aarch64.whl && rm /tmp/tensorrt-8.2.0.6-cp38-none-linux_aarch64.whl

# Downloads to user config dir
RUN mkdir -p /root/.config/Ultralytics && \
    wget https://github.com/ultralytics/assets/releases/download/v0.0.0/Arial.ttf -O /root/.config/Ultralytics/Arial.ttf && \
    wget https://github.com/ultralytics/assets/releases/download/v0.0.0/Arial.Unicode.ttf -O /root/.config/Ultralytics/Arial.Unicode.ttf

# Set the working directory and install Ultralytics YOLOv8
WORKDIR /workspace
RUN /venv/bin/pip install wheel gdown ultralytics

# Download files from Google Drive
RUN /bin/bash -c "source /venv/bin/activate && \
    gdown https://drive.google.com/uc?id=1hs9HM0XJ2LPFghcn7ZMOs5qu5HexPXwM && \
    gdown https://drive.google.com/uc?id=1m0d8ruUY8RvCP9eVjZw4Nc8LAwM8yuGV && \
    pip install torch-*.whl torchvision-*.whl && \
    rm torch-*.whl torchvision-*.whl"

# Download and install ONNX Runtime GPU wheel
RUN wget -O onnxruntime_gpu-1.8.0-cp38-cp38-linux_aarch64.whl "https://nvidia.box.com/shared/static/gjqofg7rkg97z3gc8jeyup6t8n9j8xjw.whl" && \
    /venv/bin/pip install onnxruntime_gpu-1.8.0-cp38-cp38-linux_aarch64.whl && rm onnxruntime_gpu-1.8.0-cp38-cp38-linux_aarch64.whl

# Install additional Python packages
RUN /venv/bin/pip install --no-cache tqdm matplotlib pyyaml psutil pandas numpy==1.23.5

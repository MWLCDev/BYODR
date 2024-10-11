FROM mmastrac/gst-omx-rpi

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get --allow-releaseinfo-change update && apt-get install -y \
  nano \
  v4l-utils \
  python3-gi \
  python3-numpy \
  python3-six \
  python3-tornado \
  && apt-get -y clean && rm -rf /var/lib/apt/lists/*


# Copy application files
COPY ./BYODR_utils/common/ /app/BYODR_utils/common/
COPY ./BYODR_utils/PI_specific/ /app/BYODR_utils/PI_specific/

COPY ./stream /app/stream
ENV PYTHONPATH "/app:${PYTHONPATH}"

WORKDIR /app/stream

CMD ["sleep", "infinity"]
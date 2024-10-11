FROM centipede2donald/raspbian-stretch:gst-omx-rpi-0.50.2


# Copy application files
COPY ./BYODR_utils/common/ /app/BYODR_utils/common/
COPY ./BYODR_utils/PI_specific/ /app/BYODR_utils/PI_specific/

COPY ./stream /app/stream
ENV PYTHONPATH "/app:${PYTHONPATH}"

WORKDIR /app/stream


CMD ["sleep", "infinity"]
FROM centipede2donald/ubuntu-bionic:python36-opencv32-gstreamer10

RUN pip3 install simple-pid Jetson.GPIO
RUN pip3 install "pyusb==1.0.2"
RUN pip3 install "tornado==6.1"

# Copy application files
COPY ./BYODR_utils/common/ /app/BYODR_utils/common/
COPY ./BYODR_utils/JETSON_specific/ /app/BYODR_utils/JETSON_specific/

COPY ./pilot app/pilot
ENV PYTHONPATH "/app:${PYTHONPATH}"

WORKDIR /app/pilot

CMD ["python3", "app.py"]
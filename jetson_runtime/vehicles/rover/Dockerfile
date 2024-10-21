FROM mwlvdev/jetson-nano-ubuntu:focal-cp310-GST

# Update pip and install compatible versions of pysnmp and pyasn1
RUN pip3 install --upgrade pip && \
  pip3 install pysnmp==4.4.12 pyasn1==0.4.8 paramiko pythonping


COPY ./BYODR_utils/common/ /app/BYODR_utils/common/
COPY ./BYODR_utils/JETSON_specific/ /app/BYODR_utils/JETSON_specific/

COPY ./vehicles/rover app/vehicles/rover
ENV PYTHONPATH "/app:${PYTHONPATH}"

WORKDIR /app/vehicles/rover


CMD ["python3.10", "app.py"]
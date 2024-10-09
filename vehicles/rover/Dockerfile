FROM mwlvdev/jetson-nano-ubuntu:focal-cp310-GST

# Update pip and install compatible versions of pysnmp and pyasn1
RUN pip3 install --upgrade pip && \
  pip3 install pysnmp==4.4.12 pyasn1==0.4.8

COPY ./common common/
COPY ./vehicles/rover app/
WORKDIR /app
ENV PYTHONPATH "${PYTHONPATH}:/common"
CMD ["python3.10", "app.py"]
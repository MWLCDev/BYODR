FROM tensorflow/tensorflow:1.13.2-gpu

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python-opencv \
    python-pip \
    python-scipy \
    python-setuptools \
    python-zmq \
 && apt-get -y clean && rm -rf /var/lib/apt/lists/*

RUN pip install "jsoncomment==0.3.3" && \
  pip install "Equation==1.2.1" && \
  pip install "pytest==4.6.11"

COPY ./common common/
COPY ./inference app/
WORKDIR /app

COPY ./build/*.pb /models/
COPY ./build/*.ini /models/

ENV PYTHONPATH "${PYTHONPATH}:/common"

CMD ["python", "app.py"]
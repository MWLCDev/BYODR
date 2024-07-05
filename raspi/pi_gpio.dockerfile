FROM centipede2donald/raspbian-stretch:pigpio-zmq-byodr-0.25.0

RUN pip3 install RPi.GPIO 


ENV PYTHONPATH "${PYTHONPATH}:/common"

COPY ./ app/

WORKDIR /app
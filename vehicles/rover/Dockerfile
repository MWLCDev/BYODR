FROM mwlvdev/jetson-nano-ubuntu:focal-cp310-GST


COPY ./common common/
COPY ./vehicles/rover app/
WORKDIR /app

ENV PYTHONPATH "${PYTHONPATH}:/common"

CMD ["python3.10", "app.py"]

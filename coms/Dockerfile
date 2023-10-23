FROM centipede2donald/ubuntu-bionic:python36-opencv32-gstreamer10

COPY ./common common/
COPY ./coms app/
WORKDIR /app

ENV PYTHONPATH "${PYTHONPATH}:/common"

CMD ["python3", "app.py"]
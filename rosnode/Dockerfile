FROM ros:foxy

RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 4B63CF8FDE49746E98FA01DDAD19BAB3CBF125EA
# Using new GPG key 

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-zmq \
    nano \
    wget

COPY ./common common/
COPY ./rosnode app/
WORKDIR /app

ENV PYTHONPATH "${PYTHONPATH}:/common"

CMD ["python3", "app.py"]
FROM centipede2donald/ubuntu-bionic:python36-opencv32-gstreamer10


RUN apt-get update && apt-get install -y \
  build-essential \
  libssl-dev \
  libffi-dev \
  python3-dev \
  python3-pip \
  libxml2-dev \
  libxslt1-dev \
  unzip  
# /\ unzip utility
RUN python3 -m pip install -U pip

RUN pip3 install pymongo
RUN pip3 install tornado
RUN pip3 install folium
RUN pip3 install Flask
RUN pip3 install flask_socketio
RUN pip3 install paramiko


COPY ./common common/
COPY ./teleop app/
WORKDIR /app

EXPOSE 8080 5000

ENV PYTHONPATH "${PYTHONPATH}:/common"
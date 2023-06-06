FROM centipede2donald/ubuntu-bionic:python36-opencv32-gstreamer10


RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    python3-pip \
    libxml2-dev \
    libxslt1-dev

RUN pip3 install pymongo
RUN pip3 install tornado
RUN pip3 install Cython
RUN pip3 install "markupsafe==1.1.1"
RUN pip3 install "branca==0.5.0"
RUN pip3 install Flask
RUN pip3 install "folium==0.13"
RUN pip3 install "pandas==1.0.3"
RUN pip3 install gpx_converter

COPY ./common common/
COPY ./teleop app/
WORKDIR /app



EXPOSE 9100
EXPOSE 3000

CMD ["python", "./htm/server.py"]

ENV PYTHONPATH "${PYTHONPATH}:/common"
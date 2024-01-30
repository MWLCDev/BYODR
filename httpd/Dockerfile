FROM centipede2donald/ubuntu-bionic:python27-opencv32-gstreamer10
#The service is built on top of Ubuntu Bionic with Python 2.7, OpenCV 3.2, and GStreamer 1.0 pre-installed

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
  haproxy \
  npm \
  && apt-get -y clean && rm -rf /var/lib/apt/lists/*

RUN npm install -g mapport

#The entry point for the Docker container is set to run haproxy with a configuration file /app/haproxy.conf. 
#This means that when the container starts, it will initiate HAProxy with the given configuration in haproxy.conf.

COPY ./httpd app/
WORKDIR /app

CMD ["/usr/sbin/haproxy", "-f", "/app/haproxy.conf"]
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

RUN pip3 install pymongo tornado folium Flask flask_socketio paramiko user-agents pysnmp pyasn1 pyasn1-modules

# Ignore deprecation problem from cryptography 
#/usr/local/lib/python3.6/dist-packages/pymongo/pyopenssl_context.py:26: CryptographyDeprecationWarning: Python 3.6 is no longer supported by the Python core team. Therefore, support for it is deprecated in cryptography. The next release of cryptography will remove support for Python 3.6.
# from cryptography.x509 import load_der_x509_certificate as _load_der_x509_certificate
ENV PYTHONWARNINGS "ignore::UserWarning"

COPY ./common common/
COPY ./teleop app/
WORKDIR /app

EXPOSE 8080 5000

ENV PYTHONPATH "${PYTHONPATH}:/common"

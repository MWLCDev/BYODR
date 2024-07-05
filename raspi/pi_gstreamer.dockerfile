FROM centipede2donald/raspbian-stretch:gst-omx-rpi-0.50.2


COPY ./ app/
WORKDIR /app

ENV PYTHONPATH "${PYTHONPATH}:/common"

CMD ["sleep", "infinity"]
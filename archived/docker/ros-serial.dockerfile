# docker build -f <name> -t centipede2donald/ros-melodic:rosserial .
FROM ros:melodic

RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-melodic-rosserial \
 && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["/ros_entrypoint.sh"]
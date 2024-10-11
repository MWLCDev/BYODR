FROM centipede2donald/nvidia-jetson:jp441-nano-cp36-oxrt-3

# Copy application files
COPY ./BYODR_utils/common/ /app/BYODR_utils/common/
COPY ./BYODR_utils/JETSON_specific/ /app/BYODR_utils/JETSON_specific/

COPY ./build/ /app/models/

COPY ./inference /app/inference
ENV PYTHONPATH "/app:${PYTHONPATH}"

WORKDIR /app/inference


CMD ["python3", "-m", "inference.app", "--user", "/sessions/models", "--routes", "/sessions/routes", "--internal","/app/models"]

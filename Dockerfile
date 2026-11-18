FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
COPY . /opt/ngui
RUN uv pip install --system /opt/ngui
ENV NGUI_HOME=/data NGUI_HOST=0.0.0.0 NGUI_PORT=8080 PYTHONUNBUFFERED=1
VOLUME /data
EXPOSE 8080
CMD ["ngui", "run"]

FROM apache/airflow:3.3.0-python3.14

USER root
RUN apt-get update && apt-get install -y --no-install-recommends git \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow
COPY docker/requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
# syntax=docker/dockerfile:1.2
FROM python:3.11 AS builder

WORKDIR /app
COPY . /app
RUN pip install setuptools wheel
RUN python setup.py sdist bdist_wheel

FROM jupyter/base-notebook

WORKDIR /usr/src/app

# Define placeholders for secrets
ARG GEE_CLIENT_EMAIL
ARG GEE_PRIVATE_KEY
ARG GLOFAS_KEY
ARG GLOFAS_URL
ARG MODIS_NRT_TOKEN
ARG LOCALTILESERVER_CLIENT_PREFIX='proxy/{port}'

# Utilizing secrets to set environment variables securely
RUN --mount=type=secret,id=GEE_CLIENT_EMAIL \
    GEE_CLIENT_EMAIL=$(cat /run/secrets/GEE_CLIENT_EMAIL) && export GEE_CLIENT_EMAIL
RUN --mount=type=secret,id=GEE_PRIVATE_KEY \
    GEE_PRIVATE_KEY=$(cat /run/secrets/GEE_PRIVATE_KEY) && export GEE_PRIVATE_KEY
RUN --mount=type=secret,id=GLOFAS_KEY \
    GLOFAS_KEY=$(cat /run/secrets/GLOFAS_KEY) && export GLOFAS_KEY
RUN --mount=type=secret,id=GLOFAS_URL \
    GLOFAS_URL=$(cat /run/secrets/GLOFAS_URL) && export GLOFAS_URL
RUN --mount=type=secret,id=MODIS_NRT_TOKEN \
    MODIS_NRT_TOKEN=$(cat /run/secrets/MODIS_NRT_TOKEN) && export MODIS_NRT_TOKEN

ENV LOCALTILESERVER_CLIENT_PREFIX=$LOCALTILESERVER_CLIENT_PREFIX

USER root

# Install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    gdal-bin \
    python3-gdal
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/dist /usr/src/app/dist
COPY --from=builder /app/requirements.txt /usr/src/app/
COPY --from=builder /app/README.md /usr/src/app/
COPY --from=builder /app/mcimageprocessing/config/sample.config.yaml /usr/src/app/mcimageprocessing/config/
COPY --from=builder /app/mcimageprocessing/notebook_demo.ipynb /usr/src/app/mcimageprocessing/

RUN chown -R 1000:1000 /usr/src/app
USER jovyan

ENV GDAL_VERSION=3.4.3 \
    C_INCLUDE_PATH=/usr/include/gdal \
    CPLUS_INCLUDE_PATH=/usr/include/gdal

RUN pip install --no-cache-dir numpy==1.26.3
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir /usr/src/app/dist/*.whl

ENV CONFIG_DIR=/usr/src/app/mcimageprocessing/config
EXPOSE 8888
CMD ["start-notebook.sh", "--NotebookApp.token=''", "--NotebookApp.password=''", "--NotebookApp.allow_origin='*'", "--NotebookApp.base_url=/"]

# syntax=docker/dockerfile:1.2
FROM python:3.11 AS builder

WORKDIR /app
COPY . /app
RUN pip install setuptools wheel
RUN python setup.py sdist bdist_wheel

FROM jupyter/base-notebook

WORKDIR /usr/src/app

# Install system dependencies
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    gdal-bin \
    python3-gdal \
    openssl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy necessary files from the builder stage
COPY --from=builder /app/dist /usr/src/app/dist
COPY --from=builder /app/requirements.txt /usr/src/app/
COPY --from=builder /app/README.md /usr/src/app/
COPY --from=builder /app/mcimageprocessing/config/sample.config.yaml /usr/src/app/mcimageprocessing/config/
COPY --from=builder /app/mcimageprocessing/notebook_demo.ipynb /usr/src/app/mcimageprocessing/

# Install Python packages
RUN pip install --no-cache-dir numpy==1.26.3
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir /usr/src/app/dist/*.whl

# Set ownership to the jovyan user (Jupyter default user)
RUN chown -R 1000:1000 /usr/src/app

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

USER jovyan

# Environment variables
ENV GDAL_VERSION=3.4.3 \
    C_INCLUDE_PATH=/usr/include/gdal \
    CPLUS_INCLUDE_PATH=/usr/include/gdal \
    CONFIG_DIR=/usr/src/app/mcimageprocessing/config

# Expose the port Jupyter will run on
EXPOSE 8888

# Add the entrypoint script

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["start-notebook.sh", "--NotebookApp.token=''", "--NotebookApp.password=''", "--NotebookApp.allow_origin='*'", "--NotebookApp.base_url=/"]

# Stage 2: Create the final Jupyter Notebook image
FROM jupyter/base-notebook

# Set the working directory in the container
WORKDIR /usr/src/app

# Switch to the root user to install dependencies
USER root

# Install GDAL dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    gdal-bin \
    python3-gdal

# Clean up APT when done to reduce image size
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the built distribution packages from the builder stage
COPY --from=builder /app/dist /usr/src/app/dist

# Copy the requirements.txt file
COPY --from=builder /app/requirements.txt /usr/src/app/

# Other necessary files
COPY --from=builder /app/README.md /usr/src/app/
COPY --from=builder /app/mcimageprocessing/config/sample.config.yaml /usr/src/app/mcimageprocessing/config/sample.config.yaml
COPY --from=builder /app/mcimageprocessing/notebook_demo.ipynb /usr/src/app/mcimageprocessing/notebook_demo.ipynb

RUN chown -R 1000:1000 /usr/src/app

# Switch back to the default Jupyter user
USER jovyan

# Set environment variables for GDAL
ENV GDAL_VERSION=3.4.3 \
    C_INCLUDE_PATH=/usr/include/gdal \
    CPLUS_INCLUDE_PATH=/usr/include/gdal

# Install numpy explicitly before other requirements
RUN pip install --no-cache-dir numpy==1.26.3

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install the package from the distribution files
RUN pip install --no-cache-dir /usr/src/app/dist/*.whl

ENV CONFIG_DIR=/usr/src/app/mcimageprocessing/config

# Make port 8888 available to the world outside this container
EXPOSE 8888

# Use the start-notebook.sh script from the base image to start the server
# It properly handles token authentication and other settings
CMD ["start-notebook.sh", "--NotebookApp.token=''", "--NotebookApp.password=''", "--NotebookApp.allow_origin='*'", "--NotebookApp.base_url=/"]

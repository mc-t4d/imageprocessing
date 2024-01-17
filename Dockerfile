FROM jupyter/base-notebook

# Set the working directory in the container
WORKDIR /usr/src/app

USER root

# Install GDAL dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libgdal-dev \
    gdal-bin \
    python3-gdal

USER jovyan

# Set environment variables for GDAL
ENV GDAL_VERSION 3.4.3
ENV C_INCLUDE_PATH /usr/include/gdal
ENV CPLUS_INCLUDE_PATH /usr/include/gdal

# Copy the current directory contents into the container at /usr/src/app
COPY . /usr/src/app

# Install any needed packages specified in requirements.txt
RUN pip install  -r requirements.txt

RUN pip install -e .

# Make port 8888 available to the world outside this container
EXPOSE 8888

# Run jupyter notebook when the container launches
CMD ["jupyter", "notebook", "--ip='*'", "--port=8888", "--no-browser", "--allow-root"]

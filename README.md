Readme
======

# mcimageprocessing

Overview of the Package

This package provides a comprehensive solution for geospatial data processing and analysis, primarily designed to work within a Jupyter Notebook environment. It is equipped with a robust set of tools and functionalities, making it highly suitable for a wide range of applications in geospatial analysis, environmental monitoring, and data visualization.

Find full documentation of the package functions [here on our docs page](https://mc-t4d.github.io/imageprocessing/).

## Key Features

### Jupyter Notebook Integration

Interactive Widgets: The package includes a variety of interactive widgets for Jupyter Notebooks, allowing users to select, input, and manipulate data in an intuitive way.
Dynamic Data Visualization: It supports dynamic data visualization and mapping capabilities, enabling users to visualize geospatial data directly within their notebooks.
API Integration: Integrates with various geospatial APIs including GloFas, Google Earth Engine (GEE), MODIS NRT Flood Data, WorldPop, and the Global Flood Database, providing access to a vast array of data sources.

### Geospatial Data Handling

Geometry Processing: The package offers functions to handle and process geometries, including conversion between different formats (e.g., GeoJSON to Earth Engine geometries).
Raster Data Processing: Includes tools for handling raster data such as clipping, masking, converting between different formats, and generating Cloud-Optimized GeoTIFFs (COGs).
Data Download and Processing: Facilitates the downloading and processing of data from various sources, ensuring compatibility and ease of use within the geospatial data analysis workflow.

### Programmatic Component

Beyond its integration with Jupyter Notebook, the package also provides a programmatic component. This allows for scripting and automation of tasks, making it versatile for both interactive and batch processing workflows.
Functions within this component are designed to be modular and reusable, supporting a wide range of geospatial data processing tasks.

### Customizable and Extendable

Users can easily extend the package's functionalities according to their specific needs, thanks to its modular design.
It supports custom widget creation and the ability to add new functionalities or integrate additional data sources.

### User-Centric Design

The design focuses on ease of use, making geospatial data analysis accessible to users with varying levels of expertise.
Provides clear, intuitive interfaces and documentation, reducing the learning curve for new users.

### Additional Notes

While the package is rich in features for geospatial data handling, users should be aware of the dependencies and requirements for various integrated APIs.
Regular updates and community contributions can expand the package’s capabilities, keeping it relevant and up-to-date with the latest trends in geospatial data analysis.

### Config File Creation
A configuration file is required to run the package. A sample config file is located in the package at the following path: _mcimageprocessing/config/config_sample.yaml_. This file should be copied and renamed to _config.yaml_, and the necessary parameters should be filled in. Note that for `.yaml` files, you do not need `" "` around your values.

**For GEE, the following parameters are required:**
client email: The service account email address
private_key: The private key provided in the service account credential file provided by Google.

Login info is provided with the package download, but if you would like to create your own account, please visit [this website](https://code.earthengine.google.com/register) to register for a free Google Earth Engine account and [this page](https://developers.google.com/earth-engine/guides/service_account) for help on creating a service account, email, and key.

**For GloFas, the following parameters are required:**
url: The GloFas API URL associated with the account you created
key: The API key associated with the account you created

The API url and key are provided with the package download, but if you would like to have your own credentials, sign up for a GloFAS account [here](https://cds.climate.copernicus.eu/user/register?destination=%2F%23!%2Fhome).  For your CDS url and API key, log in to your account and go to [this page](https://cds.climate.copernicus.eu/api-how-to), following the instructions for "Linux users" (as the container is a Linux image). You should see your url and key populate on the right-hand side.

**For Modis NRT Flood Data, the following parameters are required:**
token: The token provided by NASA for accessing the API associated with your account.

The API key is included with the package download, but if you would like to have your own credentials, sign up for an EarthData account [here](https://urs.earthdata.nasa.gov/users/new)
and upon login, go to 'My Profile' > 'Generate Token' to get your token. The token lasts 2 months so will need to be updated periodically.

### Using Docker

**Running the Docker Container and Connecting to Jupyter Notebook**

This guide will walk you through the process of building and running a Docker container from the provided Dockerfile, connecting to the Jupyter Notebook server hosted within the container, and setting up a linked storage between your local machine and the Docker container.
Prerequisites

Ensure Docker is installed on your machine and running. If not, download and install Docker from the [official website](https://www.docker.com/get-started/).

**Building the Docker Image**

Navigate to the Directory: Open a terminal and navigate to the directory containing your Dockerfile.

Build the Image: Execute the following command, replacing [image-name] with your desired image name:



    docker build -t [image-name] .

This command builds a Docker image based on the Dockerfile in the current directory and tags it with the name you specify.

**Running the Docker Container**

Create a Local Directory for Data: On your host machine, create a directory where you wish to store data that will be shared with the Docker container.

Run the Container: Use the following command to run your Docker container, replacing [image-name] with the name of your built image, and [path-to-local-data-dir] with the path to the directory you created:


    docker run -e DECRYPTION_KEY=[decryption key provided by T4D] -p 8888:8888 --network host -v [path-to-local-data-dir]:/usr/src/app/data [image-name]

-e is the encryption key provided by T4D to decrypt the configuration file. The configuration file contains all of the necessary Mercy Corps tokens and api keys required for this application.
-v [path-to-local-data-dir]:/usr/src/app/data mounts the local directory to the /usr/src/app/data directory in the container, creating a shared storage space.
-p 8888:8888 maps port 8888 of the container to port 8888 of your host machine, allowing you to access the Jupyter Notebook server.

**Connecting to the Jupyter Notebook Server**

Access the Jupyter Notebook: Once the container is running, open a web browser and visit http://localhost:8888.

Use the Token: When prompted, enter the token provided in the terminal logs of the Docker container. This token is required for first-time access to the Jupyter Notebook server.

Once you are in the Jupyter Server, you'll need to follow the "Config File Creation" instructions above, creating a _config.yaml_ file in the Jupyter environment that includes your API keys. If you have done this locally before creating the container, you can just copy the contents of that file into the new file.

From here, you can create a new notebook or use the _notebook_demo.ipynb_ file for quick-start access to the user interface.

**Data Storage and Access**

Data Synchronization: Any files saved in the local directory [path-to-local-data-dir] on your host machine will be accessible from within the Docker container at /usr/src/app/data, and vice versa.

Downloading Data: When downloading data via the Jupyter Notebook, save it to the /usr/src/app/data directory within the notebook environment to ensure it's also available on your local machine.

**Stopping the Container**

To stop the Jupyter Notebook server and the Docker container, simply use the Ctrl+C command in the terminal where the container is running, or run docker stop [container-id] from any terminal.

**Troubleshooting**

If you encounter any issues, check the Docker container logs using docker logs [container-id].
Ensure your Dockerfile is correctly set up and all necessary services are installed and configured as expected.

### Installing the Package using pip and setup.py

To install the `mcimageprocessing` package through pip using a `setup.py` file, follow these steps:

1. **Clone or Download the Package Source Code**

First, you need to have the source code on your local machine. You can clone the source code using the following command:

    git clone https://github.com/mc-t4d/imageprocessing.git

Alternatively, download the source code as a ZIP file and extract it to a directory on your computer.

2. **Navigate to the Package Directory**

Make sure you are in the directory containing the `setup.py` file this should be in the base folder of the cloned repo.
This file contains the package metadata and dependencies needed for installation.
Run the following command in your terminal if you are not already in the base folder:

    cd imageprocessing


3. **Install the Package**

Use `pip` to install the package. Run the following command to install the package along with its dependencies:

    pip install .


If you prefer to install the package in "editable" mode (useful for development purposes), where changes to the source code will immediately affect the installed package, use the following command:

    pip install -e .


4. **Verify the Installation**

After installation, you can verify that the package is installed correctly by checking its presence in the list of installed packages:

    pip list | grep mcimageprocessing


This command should list `mcimageprocessing` along with its version, indicating that the package is installed.

In order to decrypt the configuration file, you will need to ensure openssl is installed on your machine.  If it is not, you can install it using the following command:

    linux: sudo apt-get install openssl
    mac: brew install openssl
    windows: download the installer from the [official website](https://slproweb.com/products/Win32OpenSSL.html)

then run the following command to decrypt the configuration file:

    linux: openssl enc -aes-256-cbc -d -in mcimageprocessing/config/config.enc -out mcimageprocessing/config/config.yaml -k [decryption key provided by T4D]
    mac: openssl enc -aes-256-cbc -d -in mcimageprocessing/config/config.enc -out mcimageprocessing/config/config.yaml -k [decryption key provided by T4D]
    windows: openssl enc -aes-256-cbc -d -in mcimageprocessing/config/config.enc -out mcimageprocessing/config/config.yaml -k [decryption key provided by T4D]

This will create a _config.yaml_ file in the _config_ directory that you can use to store your API keys, pre-populated with the keys provided by T4D.

5. **Testing the Installation**

You can test whether the package is working properly by running some of its functions or scripts. If the package provides a command-line interface or scripts, try executing them to ensure everything is functioning as expected.

6. **Updating the Package**

If the source code of the package is updated, you can upgrade the installed package by navigating to the package directory and running:

    pip install --upgrade .


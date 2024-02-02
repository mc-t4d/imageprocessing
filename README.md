# mcimageprocessing



Overview of the Package

This package provides a comprehensive solution for geospatial data processing and analysis, primarily designed to work within a Jupyter Notebook environment. It is equipped with a robust set of tools and functionalities, making it highly suitable for a wide range of applications in geospatial analysis, environmental monitoring, and data visualization.

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
A configuration file is required to run the package. A sample config file is located in the package at the following path: _mcimageprocessing/config/config_sample.yaml_. This file should be copied and renamed to _config.yaml_, and the necessary parameters should be filled in.

**For GEE, the following parameters are required:**
client email: The service account email address
private_key: The private key provided in the service account credential file provided by Google.

**For GloFas, the following parameters are required:**
url: The GloFas API URL associated with the account you created
key: The API key associated with the account you created

**For Modis NRT Flood Data, the following parameters are required:**
token: The token provided by NASA for accessing the API associated with your account.


### Using Docker
--------

**Running the Docker Container and Connecting to Jupyter Notebook**

This guide will walk you through the process of building and running a Docker container from the provided Dockerfile, connecting to the Jupyter Notebook server hosted within the container, and setting up a linked storage between your local machine and the Docker container.
Prerequisites

Ensure Docker is installed on your machine. If not, download and install Docker from the official website.

**Building the Docker Image**

Navigate to the Directory: Open a terminal and navigate to the directory containing your Dockerfile.

Build the Image: Execute the following command, replacing [image-name] with your desired image name:



    docker build -t [image-name] .

This command builds a Docker image based on the Dockerfile in the current directory and tags it with the name you specify.

**Running the Docker Container**

Create a Local Directory for Data: On your host machine, create a directory where you wish to store data that will be shared with the Docker container.

Run the Container: Use the following command to run your Docker container, replacing [image-name] with the name of your built image, and [path-to-local-data-dir] with the path to the directory you created:


    docker run -p 8888:8888 -v [path-to-local-data-dir]:/usr/src/app/data [image-name]

-p 8888:8888 maps port 8888 of the container to port 8888 of your host machine, allowing you to access the Jupyter Notebook server.
-v [path-to-local-data-dir]:/usr/src/app/data mounts the local directory to the /usr/src/app/data directory in the container, creating a shared storage space.

**Connecting to the Jupyter Notebook Server**

Access the Jupyter Notebook: Once the container is running, open a web browser and visit http://localhost:8888.

Use the Token: When prompted, enter the token provided in the terminal logs of the Docker container. This token is required for first-time access to the Jupyter Notebook server.

**Data Storage and Access**

Data Synchronization: Any files saved in the local directory [path-to-local-data-dir] on your host machine will be accessible from within the Docker container at /usr/src/app/data, and vice versa.

Downloading Data: When downloading data via the Jupyter Notebook, save it to the /usr/src/app/data directory within the notebook environment to ensure it's also available on your local machine.

**Stopping the Container**

To stop the Jupyter Notebook server and the Docker container, simply use the Ctrl+C command in the terminal where the container is running, or run docker stop [container-id] from any terminal.

**Troubleshooting**

If you encounter any issues, check the Docker container logs using docker logs [container-id].
Ensure your Dockerfile is correctly set up and all necessary services are installed and configured as expected.



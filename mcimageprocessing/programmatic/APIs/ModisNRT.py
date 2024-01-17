import pandas as pd

from shapely.geometry import Point
from pyproj import Proj, transform
import re
import requests
from bs4 import BeautifulSoup
import datetime
from osgeo import ogr, osr, gdal
import rasterio
import numpy as np
from shapely.geometry import shape
import geopandas as gpd
from rasterio.features import shapes
import ee
import json
from mcimageprocessing.programmatic.APIs.EarthEngine import EarthEngineManager
import pkg_resources

ee_auth_path = pkg_resources.resource_filename('mcimageprocessing', 'ee_auth_file.json')

with open(ee_auth_path, "r") as f:
    ee_auth_json = f.read().strip()

ee_auth = json.loads(ee_auth_json)

# Initialize Earth Engine credentials
credentials = ee.ServiceAccountCredentials(
    email=ee_auth['client_email'],
    key_data=ee_auth['private_key']
)

ee.Initialize(credentials)

ee_instance = EarthEngineManager(authentication_file=ee_auth_path)

class ModisNRT:
    """
    :class: ModisNRT
    This class provides functions to interact with the MODIS NRT (Near Real-Time) data.

    Initialization Parameters:
        None

    Attributes:
        modis_tile_size (float): MODIS sinusoidal tile size in meters.
        modis_download_token (str): Token for MODIS NRT download.
        modis_nrt_api_root_url (str): Root URL for MODIS NRT API.
        headers (dict): Headers for API requests.
        nrt_band_options (dict): Dictionary mapping MODIS band names to their index values.

    Methods:
        calculate_modis_tile_index(x, y)
            Calculate MODIS tile indices for given sinusoidal coordinates.

        get_modis_tile(geometry)
            Calculate which MODIS tiles a given geometry falls into.

        get_modis_nrt_file_list(tiles, modis_nrt_params)
            Get a list of MODIS NRT files for the given tiles.

        process_hdf_file(hdf_file, subdataset_index, tif_list=None)
            Process an HDF file and convert it to a GeoTIFF.
    """

    def __init__(self):
        self.modis_tile_size = 1111950.5196666667  # MODIS sinusoidal tile size in meters
        self.modis_download_token = '''eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJlbWFpbF9hZGRyZXNzIjoibmlja0BrbmRjb25zdWx0aW5nLm9yZyIsImlzcyI6IkFQUyBPQXV0aDIgQXV0aGVudGljYXRvciIsImlhdCI6MTcwNDY5NDk1NSwibmJmIjoxNzA0Njk0OTU1LCJleHAiOjE4NjIzNzQ5NTUsInVpZCI6Im5oc3VyZjYwIiwidG9rZW5DcmVhdG9yIjoibmhzdXJmNjAifQ.OFsGT01-7VmQUXKhKZUx_GK3AQ5RMz3oSI9AdJmYDlQ'''
        self.modis_nrt_api_root_url = 'https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/archives/allData/61/MCDWD_L3_NRT/'
        self.headers = {'Authorization': f'Bearer {self.modis_download_token}'}  # Token for MODIS NRT download
        self.modis_proj = Proj("+proj=sinu +R=6371007.181 +nadgrids=@null +wktext")

        self.nrt_band_options = {'Water Counts 1-Day 250m Grid_Water_Composite': 0,
                                 'Water Counts CS 1-Day 250m Grid_Water_Composite': 1,
                                 'Valid Counts 1-Day 250m Grid_Water_Composite': 2,
                                 'Valid Counts CS 1-Day 250m Grid_Water_Composite': 3,
                                 'Flood 1-Day 250m Grid_Water_Composite': 4,
                                 'Flood 1-Day CS 250m Grid_Water_Composite': 5,
                                 'Water Counts 2-Day 250m Grid_Water_Composite': 6,
                                 'Valid Counts 2-Day 250m Grid_Water_Composite': 7,
                                 'Flood 2-Day 250m Grid_Water_Composite': 8,
                                 'Water Counts 3-Day 250m Grid_Water_Composite': 9,
                                 'Valid Counts 3-Day 250m Grid_Water_Composite': 10,
                                 'Flood 3-Day 250m Grid_Water_Composite': 11}


    def calculate_modis_tile_index(self, x, y):
        """
        Calculate MODIS tile index based on the given x and y coordinates.

        :param x: The x coordinate.
        :param y: The y coordinate.
        :return: The MODIS tile index as a tuple (h, v).
        """
        h = int((x + 20015109.354) // self.modis_tile_size)
        v = int((10007554.677 - y) // self.modis_tile_size)  # Adjust for Northern Hemisphere
        return h, v

    def get_modis_tile(self, geometry):
        """
        :param geometry: The input geometry can be either a Shapely Point, a bounding box list [minx, miny, maxx, maxy], or a DataFrame with bbox columns.
        :return: A set of Modis tiles covered by the given geometry.
        """
        tiles_covered = set()

        if isinstance(geometry, Point):
            x, y = transform(Proj(proj='latlong'), self.modis_proj, geometry.x, geometry.y)
            tiles_covered.add(self.calculate_modis_tile_index(x, y))
        elif isinstance(geometry, list) and len(geometry) == 4:
            for corner in [(geometry[0], geometry[1]), (geometry[0], geometry[3]),
                           (geometry[2], geometry[1]), (geometry[2], geometry[3])]:
                x, y = transform(Proj(proj='latlong'), self.modis_proj, *corner)
                tiles_covered.add(self.calculate_modis_tile_index(x, y))
        elif isinstance(geometry, pd.DataFrame):
            bbox = geometry.iloc[0]  # Assuming you want to process the first row
            for corner in [(bbox['minx'], bbox['miny']), (bbox['minx'], bbox['maxy']),
                           (bbox['maxx'], bbox['miny']), (bbox['maxx'], bbox['maxy'])]:
                x, y = transform(Proj(proj='latlong'), self.modis_proj, *corner)
                tiles_covered.add(self.calculate_modis_tile_index(x, y))
        else:
            raise TypeError(
                "Input must be a Shapely Point, a bounding box list [minx, miny, maxx, maxy], or a DataFrame with bbox columns.")

        return tiles_covered

    def get_modis_nrt_file_list(self, tiles, modis_nrt_params):
        """
        :param tiles: A list of tuples representing the MODIS tiles to retrieve files for. Each tuple should contain the horizontal (h) and vertical (v) coordinates of the tile.
        :param modis_nrt_params: A dictionary containing the parameters for the MODIS Near Real-Time (NRT) data. This dictionary should include the 'date' key with a datetime object representing
        * the date for which the files should be retrieved.
        :return: A list of matching file names from the MODIS NRT API.

        """

        matching_files = []
        for tile in tiles:
            h = f"{tile[0]:02d}"
            v = f"{tile[1]:02d}"
            year = modis_nrt_params['date'].year
            doy = f"{modis_nrt_params['date'].timetuple().tm_yday:03d}"
            base_url_folder = f"{self.modis_nrt_api_root_url}{year}/{doy}/"
            file_pattern = rf"MCDWD_L3_NRT\.A{year}{doy}\.h{h}v{v}\.061\.\d+\.hdf"

            response = requests.get(base_url_folder)
            html_content = response.text

            soup = BeautifulSoup(html_content, 'html.parser')

            links = soup.find_all('a')

            # Check if the request was successful
            for link in links:
                href = link.get('href')
                if re.search(file_pattern, href):
                    matching_files.append(href)

        print('All Files Collected')

        return matching_files

    def process_hdf_file(self, hdf_file, subdataset_index, tif_list=None):
        """
        Process an HDF file and convert a subdataset to GeoTIFF format.

        :param hdf_file: The path to the HDF file.
        :param subdataset_index: The index of the subdataset to be processed.
        :param tif_list: (Optional) A list to store the paths of generated GeoTIFF files.

        :return: None

        Example usage:
        ```
        process_hdf_file('input.hdf', 0, tif_list=['output.tif'])
        ```
        """
        hdf_dataset = gdal.Open(hdf_file, gdal.GA_ReadOnly)
        subdatasets = hdf_dataset.GetSubDatasets()

        # Select a subdataset
        subdataset = subdatasets[subdataset_index][0]

        # Open the subdataset
        ds = gdal.Open(subdataset, gdal.GA_ReadOnly)

        # Define output path for the GeoTIFF
        output_tiff = hdf_file.replace('.hdf', '.tif')

        # Convert to GeoTIFF
        gdal.Translate(output_tiff, ds)

        # Close the dataset
        ds = None

        if tif_list is not None:
            tif_list.append(output_tiff)

    def download_and_process_modis_nrt(self, url, folder_path, hdf_files_to_process, subdataset, tif_list=None):
        """
        :param geometry: The input geometry can be either a Shapely Point, a bounding box list [minx, miny, maxx, maxy], or a DataFrame with bbox columns.
        :param modis_nrt_params: A dictionary containing the parameters for the MODIS Near Real-Time (NRT) data. This dictionary should include the 'date' key with a datetime object representing
        the date for which the files should be retrieved.
        :param subdataset_index: The index of the subdataset to be processed.
        :param tif_list: (Optional) A list to store the paths of generated GeoTIFF files.
        :return: None

        Example usage:
        ```
        download_and_process_modis_nrt(Point(0, 0), {'date': datetime.datetime(2020, 1, 1)}, 0, tif_list=['output.tif'])
        ```
        """

        response = requests.get(url, headers=self.headers, stream=True)
        if response.status_code == 200:
            print(f"downloading {url}")
            filename = f"{folder_path}{url.split('/')[-1]}"  # Extracts the filename
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            hdf_files_to_process.append(filename)
            subdataset_index = self.nrt_band_options[subdataset]

            for hdf_file in hdf_files_to_process:

                self.process_hdf_file(hdf_file, subdataset_index, tif_list=tif_list)

    def merge_tifs(self, tif_list, output_tif):
        """
        Merge a list of GeoTIFF files into a single GeoTIFF.

        :param tif_list: A list of GeoTIFF files to merge.
        :param output_tif: The path to the output GeoTIFF file.
        :return: None
        """
        gdal.Warp(output_tif, tif_list)

    def get_modis_nrt_dates(self):
        response = requests.get(
            'https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/details/allData/61/MCDWD_L3_NRT?fields=all&formats=json')
        json_response = response.json()['content']
        years = [x['name'] for x in json_response if x['name'] != 'Recent']
        dates = []
        for year in years:
            date_response = requests.get(
                f'https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/details/allData/61/MCDWD_L3_NRT/{year}?fields=all&formats=json')
            date_response_json = date_response.json()['content']
            for date in date_response_json:
                dates.append(self.convert_to_date(f'{year}{date["name"]}'))
        return dates

    def convert_to_date(self, date_string):
        # Extract the year and the day of the year from the string
        year = int(date_string[:4])
        day_of_year = int(date_string[4:])

        # Calculate the date by adding the day of the year to the start of the year
        date = datetime.datetime(year, 1, 1) + datetime.timedelta(days=day_of_year - 1)

        return date

    def calculate_population_in_flood_area(self, raster_path):
        with rasterio.open(raster_path) as src:
            band = src.read(1)  # Read the first band

        # Create a mask where the pixel value is 3
        mask = band == 3
        if not np.any(mask):
            return 'No flood area detected'

        # Vectorize the mask
        mask_shapes = shapes(band, mask=mask, transform=src.transform)

        # Create geometries and their associated raster values
        geometries = []
        raster_values = []
        for geom, value in mask_shapes:
            if value == 3.0:
                geometries.append(shape(geom))
                raster_values.append(value)

        # Create a GeoDataFrame with geometry and raster value columns
        gdf = gpd.GeoDataFrame({'geometry': geometries, 'raster_value': raster_values})

        # Set the CRS from the raster
        gdf.crs = src.crs

        ee_geometries = gdf['geometry'].apply(self.shapely_to_ee)

        multi_geom = ee.Geometry.MultiPolygon(list(ee_geometries))

        image, geometry, scale = ee_instance.get_image(multi_date=True, start_date=f'2020-01-01',
                                                       end_date=f'2020-12-31',
                                                       image_collection='WorldPop/GP/100m/pop', band='population',
                                                       geometry=multi_geom, aggregation_method='max')


        return f'Population impacted: {"{:,}".format(round(ee_instance.get_image_sum(image, geometry, scale)))}'

    def shapely_to_ee(self, geometry, crs='EPSG:4326'):
        """Convert a shapely geometry to a GEE geometry."""
        geojson = gpd.GeoSeries([geometry]).set_crs(crs).to_json()
        geojson_dict = json.loads(geojson)
        ee_geometry = ee.Geometry(geojson_dict['features'][0]['geometry'])
        return ee_geometry

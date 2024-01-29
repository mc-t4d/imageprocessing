import datetime
import json
import os
import re
from typing import Dict, Any, List
from typing import Optional, Set, Tuple, Union

import ee
import geopandas as gpd
import ipyfilechooser as fc
import ipywidgets as widgets
import numpy as np
import pandas as pd
import rasterio
import requests
from bs4 import BeautifulSoup
from osgeo import gdal
from pyproj import Proj, transform
from rasterio.features import shapes
from shapely.geometry import Point
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from mcimageprocessing import config_manager
from mcimageprocessing.programmatic.APIs.EarthEngine import EarthEngineManager
from mcimageprocessing.programmatic.APIs.GPWv4 import GPWv4
from mcimageprocessing.programmatic.APIs.WorldPop import WorldPop
from mcimageprocessing.programmatic.shared_functions.utilities import process_and_clip_raster


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

    population_source_options=['WorldPop', 'GPWv4']
    nrt_band_options = {'Water Counts 1-Day 250m Grid_Water_Composite': 0,
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
    modis_proj = Proj("+proj=sinu +R=6371007.181 +nadgrids=@null +wktext")
    modis_tile_size = 1111950.5196666667  # MODIS sinusoidal tile size in meters
    modis_nrt_api_root_url = 'https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/archives/allData/61/MCDWD_L3_NRT'
    date_type_options = ['Single Date', 'Date Range', 'All Available Images']
    population_source_variables=['Residential Population', "Age and Sex Structures"]
    population_source_year_options=[x for x in range(2000, 2021)]

    def __init__(self, ee_manager: Optional[EarthEngineManager] = None):
        """
        Initialize the object.

        :param ee_manager: Optional parameter of type EarthEngineManager. An instance of the EarthEngineManager class. If not provided, a new instance will be created.
        """
        self.modis_download_token = config_manager.config['KEYS']['MODIS_NRT']['token']  # Token for MODIS NRT download
        self.headers = {'Authorization': f'Bearer {self.modis_download_token}'}  # Token for MODIS NRT download
        self.ee_instance = ee_manager if ee_manager else EarthEngineManager()
        self.worldpop_instance = WorldPop()
        self.gpwv4_instance = GPWv4()

    def calculate_modis_tile_index(self, x: float, y: float) -> tuple[int, int]:
        """
        Calculate the MODIS tile index for the given coordinates.

        :param x: The X-coordinate of the location.
        :param y: The Y-coordinate of the location.
        :return: A tuple containing the horizontal and vertical indices of the MODIS tile.

        Example Usage:
            >>> x = 123456.789
            >>> y = 987654.321
            >>> index = calculate_modis_tile_index(x, y)
            >>> print(index)
            (12, 34)
        """
        h = int((x + 20015109.354) // self.modis_tile_size)
        v = int((10007554.677 - y) // self.modis_tile_size)  # Adjust for Northern Hemisphere
        return h, v

    def get_modis_tile(self, geometry: Union[Point, list, pd.DataFrame]) -> Set[tuple[int, int]]:
        """
            Method to calculate the MODIS tile indices covered by a given geometry.

            :param geometry: The geometry for which to calculate the MODIS tile indices. Must be a Shapely Point, a bounding box list [minx, miny, maxx, maxy], or a DataFrame with bbox columns
        *.
            :type geometry: Union[Point, list, pd.DataFrame]
            :return: A set of MODIS tile indices covered by the geometry.
            :rtype: Set[tuple[int, int]]
            :raises TypeError: If the input geometry is not of the expected types.

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

    def get_modis_nrt_file_list(self, tiles: List[Tuple[int, int]], modis_nrt_params: Dict[str, datetime.datetime]) -> \
    List[str]:
        """
        :param tiles: List of tuples representing the tiles (integer values for h and v)
        :param modis_nrt_params: Dictionary containing the necessary parameters for Modis NRT (date)
        :return: List of matching file URLs

        This method takes in a list of tiles and Modis NRT parameters and returns a list of file URLs that match the specified criteria. It loops through each tile, constructs the base URL folder
        *, and generates a file pattern based on the year, day of year, and tile coordinates. It then sends a request to the base URL folder and parses the HTML content using BeautifulSoup.
        * It finds all the links in the HTML content and checks if they match the file pattern. If a link matches the pattern, it is added to the list of matching files. Finally, the method
        * prints a message and returns the list of matching file URLs.
        """

        matching_files = []
        for tile in tiles:
            h = f"{tile[0]:02d}"
            v = f"{tile[1]:02d}"
            year = modis_nrt_params['date'].year
            doy = f"{modis_nrt_params['date'].timetuple().tm_yday:03d}"
            base_url_folder = f"{self.modis_nrt_api_root_url}/{year}/{doy}/"
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

    def process_hdf_file(self, hdf_file: str, subdataset_index: int, tif_list: Optional[List[str]] = None) -> None:
        """
        Process HDF file and convert the selected subdataset to GeoTIFF format.

        :param hdf_file: Path to the HDF file.
        :param subdataset_index: Index of the subdataset to be converted.
        :param tif_list: Optional list to store the paths of the converted GeoTIFF files.
        :return: None

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

    def download_and_process_modis_nrt(self, url: str, folder_path: str, hdf_files_to_process: List[str],
                                       subdataset: str, tif_list: Optional[List[str]] = None) -> None:
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

    def merge_tifs(self, tif_list: List[str], output_tif: str) -> None:
        """
        Merge a list of GeoTIFF files into a single GeoTIFF.

        :param tif_list: A list of GeoTIFF files to merge.
        :param output_tif: The path to the output GeoTIFF file.
        :return: None
        """
        gdal.Warp(output_tif, tif_list)

    def get_modis_nrt_dates(self) -> List[datetime.datetime]:
        """
        Returns a list of datetime objects representing the available MODIS NRT (Near Real Time) dates.

        :return: A list of datetime.datetime objects representing the available MODIS NRT dates.
        """
        response = requests.get(
            f'{self.modis_nrt_api_root_url}?fields=all&formats=json')
        json_response = response.json()['content']
        years = [x['name'] for x in json_response if x['name'] != 'Recent']
        dates = []
        for year in years:
            date_response = requests.get(
                f'{self.modis_nrt_api_root_url}/{year}?fields=all&formats=json')
            date_response_json = date_response.json()['content']
            for date in date_response_json:
                dates.append(self.convert_to_date(f'{year}{date["name"]}'))
        return dates

    def convert_to_date(self, date_string: str) -> datetime.datetime:
        """
        Converts a date string to a datetime object.

        :param date_string: The date string in the format "YYYYDDD", where YYYY is the year and DDD is the day of the year.
        :return: The converted datetime object representing the given date.

        Example:
            >>> convert_to_date("2020121")
            datetime.datetime(2020, 5, 1)
        """
        # Extract the year and the day of the year from the string
        year = int(date_string[:4])
        day_of_year = int(date_string[4:])

        # Calculate the date by adding the day of the year to the start of the year
        date = datetime.datetime(year, 1, 1) + datetime.timedelta(days=day_of_year - 1)

        return date

    def read_raster_and_create_mask(self, raster_path: str, mask_value = 3):
        """
        Reads a raster file and creates a binary mask based on a specified mask value.

        :param raster_path: The path to the raster file.
        :param mask_value: The value to use as the mask. Default is 3.
        :return: A tuple containing the raster source and the binary mask.

        .. note::
            - The raster file should be in a format supported by `rasterio <https://rasterio.readthedocs.io/en/latest/>`_.
            - The method returns ``None`` if no pixels in the raster match the specified mask value.

        Example usage:
            >>> raster_path = "path/to/raster.tif"
            >>> mask_value = 3
            >>> source, mask = read_raster_and_create_mask(raster_path, mask_value)

        """
        with rasterio.open(raster_path) as src:
            band = src.read(1)  # Read the first band

        # Create a mask where the pixel value is 3 (flood area)
        mask = band == mask_value
        if not np.any(mask):
            return None, None

        return src, mask

    def vectorize_mask_and_create_geometries(self, src, mask, mask_value=3.0):
        """
        :param src: The raster source file to extract geometries from.
        :param mask: A boolean numpy array representing the binary mask to apply on the raster.
        :param mask_value: The value in the mask to consider as True. Defaults to 3.0.
        :return: A GeoDataFrame containing the vectorized geometries and their corresponding raster values.
        """
        mask_shapes = shapes(src.read(1), mask=mask, transform=src.transform)

        geometries = []
        raster_values = []
        for geom, value in mask_shapes:
            if value == mask_value:
                geometries.append(shape(geom))
                raster_values.append(value)

        gdf = gpd.GeoDataFrame({'geometry': geometries, 'raster_value': raster_values})
        gdf.crs = src.crs

        return gdf

    def calculate_population_in_flood_area(self, raster_path: str, year: int, population_data_type: str, population_data_source: str, folder_output: str) -> str:
        """
        :param raster_path: (str) The path to the raster file containing flood area data.
        :param year: (int) The year for which the population data is needed.
        :param population_data_type: (str) The type of population data source to use. Can be 'Google Earth Engine' or any other valid data source.
        :param population_data_source: (str) The specific population data source to use. Can be 'Residential Population' or any other valid source depending on the data type.
        :param folder_output: (str) The output folder where the results will be saved.
        :return: (str) A string indicating the population impacted by the flood area.

        """
        src, mask = self.read_raster_and_create_mask(raster_path, mask_value=3)

        if not np.any(mask):
            return 'No flood area detected'

        gdf = self.vectorize_mask_and_create_geometries(src, mask, mask_value=3.0)

        ee_geometries = gdf['geometry'].apply(self.shapely_to_ee)

        multi_geom = ee.Geometry.MultiPolygon(list(ee_geometries))

        if population_data_type == 'Google Earth Engine':

            if population_data_source == 'Residential Population':

                worldpop_params = {
                    'api_source': population_data_type,
                    'year': year,
                    'datatype': population_data_source,
                    'statistics_only': False,
                    'add_image_to_map': False,
                    'create_sub_folder': False,
                    'folder_output': folder_output,
                    'band': 'population'
                }

                try:
                    image = self.worldpop_instance.process_api(geometry=multi_geom, distinct_values=None, index=None, params=worldpop_params)
                except Exception as e:
                    print(f"{e}")


                return f'Population impacted: {"{:,}".format(round(self.ee_instance.get_image_sum(image, multi_geom, 100)))}'


            else:
                worldpop_params = {
                    'api_source': population_data_type,
                    'year': year,
                    'datatype': population_data_source,
                    'statistics_only': True,
                    'add_image_to_map': False,
                    'create_sub_folder': False,
                    'folder_output': folder_output,
                }

                image = self.worldpop_instance.process_api(geometry=multi_geom, distinct_values=None, index=None, params=worldpop_params)

                return f'Population impacted: {image}'

                # return f'Population impacted: {stats}'

                # return f'Population impacted: {"{:,}".format(round(ee_instance.get_image_sum(image, multi_geom, 100)))}'


            # image, geometry, scale = ee_instance.get_image(multi_date=True, start_date=f'{year}-01-01',
            #                                                end_date=f'{year}-12-31',
            #                                                image_collection='WorldPop/GP/100m/pop', band='population',
            #                                                geometry=multi_geom, aggregation_method='max')
        else:

            gpwv4_params = {
                'year': year,
                'datatype': population_data_source,
                'statistics_only': True,
                'add_image_to_map': False,
                'create_sub_folder': False,
                'folder_output': folder_output,
                'band': [option['band'] for option in self.gpwv4_instance.data_type_options if option['layer'] == population_data_source][0]
            }
            print(gpwv4_params)
            self.gpwv4_instance.process_api(multi_geom, distinct_values=None, index=None, params=gpwv4_params)



    def shapely_to_ee(self, geometry: BaseGeometry, crs: str = 'EPSG:4326') -> ee.Geometry:
        """
        :param geometry: The Shapely geometry object to be converted to Earth Engine Geometry.
        :type geometry: shapely.geometry.base.BaseGeometry

        :param crs: The Coordinate Reference System (CRS) of the input geometry. Defaults to 'EPSG:4326'.
        :type crs: str

        :return: The Earth Engine Geometry object created from the input Shapely geometry.
        :rtype: ee.Geometry

        """
        geojson = gpd.GeoSeries([geometry]).set_crs(crs).to_json()
        geojson_dict = json.loads(geojson)
        ee_geometry = ee.Geometry(geojson_dict['features'][0]['geometry'])
        return ee_geometry


    def get_tiles(self, bbox: Any) -> List[Any]:
        """
        Get the tiles for the given bounding box.

        :param bbox: The bounding box.
        :type bbox: Any
        :return: The list of tiles.
        :rtype: List[Any]
        """
        tiles = self.get_modis_tile(bbox)
        print(f'Processing tiles: {tiles}')
        return tiles

    def find_matching_files(self, tiles: List[Any], modis_nrt_params: Dict[str, Any]) -> List[str]:
        """
        Find matching files based on the given tiles and MODIS NRT parameters.

        :param tiles: A list of tiles.
        :type tiles: List[Any]

        :param modis_nrt_params: A dictionary of MODIS NRT parameters.
        :type modis_nrt_params: Dict[str, Any]

        :return: A list of matching file names.
        :rtype: List[str]
        """
        return self.get_modis_nrt_file_list(tiles, modis_nrt_params)

    def download_and_process_files(self, matching_files: List[str], modis_nrt_params: Dict[str, Any]) -> (List[str], List[str]):
        """
        Download and process the given files.

        :param matching_files: List of files to be downloaded and processed.
        :param modis_nrt_params: Dictionary containing modis nrt parameters.
        :type matching_files: List[str]
        :type modis_nrt_params: Dict[str, Any]
        :return: Tuple containing lists of hdf files to process and tif files.
        :rtype: Tuple[List[str], List[str]]
        """
        hdf_files_to_process = []
        tif_list = []
        for url in matching_files:
            self.download_and_process_modis_nrt(url, modis_nrt_params['folder_path'], hdf_files_to_process, subdataset=modis_nrt_params['nrt_band'], tif_list=tif_list)
        return hdf_files_to_process, tif_list

    def finalize_processing(self, merged_output: str, geometry: Any, modis_nrt_params: Dict[str, Any]) -> None:
        """
        :param merged_output: The path to the merged output raster file.
        :param geometry: The geometry object representing the area of interest.
        :param modis_nrt_params: A dictionary containing the parameters for MODIS NRT processing.
        :return: None

        This method finalizes the processing by calling the 'process_and_clip_raster' function to process and clip the merged output raster file based on the provided geometry and MODIS NRT
        * parameters. Afterward, it prints 'Processing Complete!' to indicate the completion of the processing. If the 'calculate_population' flag is set to True in the modis_nrt_params, it
        * calls the 'calculate_population_in_flood_area' method to calculate the population impacted by the flood in the clipped output raster file. Finally, it prints the population impacted
        *.

        Example usage:

        ```
        finalize_processing('/path/to/merged_output.tif', geometry_object, {
            'calculate_population': True,
            'folder_path': '/path/to/output',
            'population_year': 2021,
            'population_type': 'total',
            'population_data_type': 'density'
        })
        ```
        """
        process_and_clip_raster(merged_output, geometry, modis_nrt_params, self.ee_instance)
        print('Processing Complete!')
        if modis_nrt_params['calculate_population']:
            clipped_output = f'{modis_nrt_params["folder_path"]}/merged_clipped.tif'
            pop_impacted = self.calculate_population_in_flood_area(clipped_output, modis_nrt_params['population_year'], modis_nrt_params['population_type'], modis_nrt_params['population_data_type'],
                                                                   modis_nrt_params['folder_path'])
            print(pop_impacted)

    def cleanup_files(self, tif_list: List[str], hdf_files_to_process: List[str], modis_nrt_params: Dict[str, Any]) -> None:
        """
        Removes files from the given lists if `keep_individual_tiles` parameter is False.

        :param tif_list: A list of TIFF file paths.
        :param hdf_files_to_process: A list of HDF file paths.
        :param modis_nrt_params: A dictionary of MODIS NRT parameters.
            - 'keep_individual_tiles': A boolean indicating whether to keep individual tiles or not.

        :return: None
        """
        if not modis_nrt_params['keep_individual_tiles']:
            for file in tif_list + hdf_files_to_process:
                try:
                    os.remove(file)
                except FileNotFoundError:
                    pass

    def merge_files(self, tif_list: List[str], folder: str) -> str:
        """
        Merge the given list of TIFF files into a single merged file.

        :param tif_list: List of paths to TIFF files to be merged.
        :param folder: Folder where the merged file will be saved.
        :return: Path to the merged TIFF file.

        Example Usage:
            tif_list = ['file1.tif', 'file2.tif', 'file3.tif']
            folder = '/path/to/folder'
            merged_file = merge_files(tif_list, folder)
        """
        merged_output = os.path.join(folder, 'merged.tif')
        self.merge_tifs(tif_list, merged_output)
        return merged_output

    def create_sub_folder(self, modis_nrt_params: Dict[str, Any]) -> str:
        """
        Creates a sub-folder based on the given parameters.

        :param modis_nrt_params: A dictionary containing the parameters.
               - 'create_sub_folder' (bool): Indicates whether to create a sub-folder or not.
               - 'folder_path' (str): The path to the main folder.
        :return: The path of the created sub-folder.
        :rtype: str
        """
        if modis_nrt_params['create_sub_folder']:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            print(modis_nrt_params['folder_path'])
            print(timestamp)
            folder = os.path.join(modis_nrt_params['folder_path'], timestamp)
            os.makedirs(folder, exist_ok=True)
            modis_nrt_params['folder_path'] = folder
        return modis_nrt_params['folder_path']


class ModisNRTNotebookInterface(ModisNRT):

    def __init__(self, ee_manager: Optional[EarthEngineManager] = None):
        """
        Initialize the class.

        :param ee_manager: An instance of the EarthEngineManager class. If not provided,
                           a new instance will be created.
        """
        super().__init__(ee_manager)  # Initialize the base WorldPop class
        self.out = widgets.Output()  # For displaying logs, errors, etc.
        # Initialize widgets
        self.create_widgets_for_modis_nrt()

    def on_single_or_date_range_change_modis_nrt(self, change: Dict[str, Any]) -> Any:
        """
        Handle the change event for the single or date range dropdown in the MODIS NRT widget.

        :param change: The change event.
        :type change: dict

        :return: The value of the single or date range dropdown.
        :rtype: any
        """

        single_or_date_range_value = change['new']

        if single_or_date_range_value == 'Single Date':
            # Create the DatePicker widget with constraints
            self.date_picker_modis_nrt = widgets.Dropdown(
                options=[(f"{x.year}-{x.month}-{x.day}", x) for x in self.modis_nrt_available_dates],
                description='Select Date:',
                disabled=False,
            )
            self.modis_nrt_date_vbox.children = [self.date_picker_modis_nrt]

        elif single_or_date_range_value == 'Date Range':
            # Create the DatePicker widgets with constraints
            self.date_picker_modis_nrt = widgets.HBox([
                widgets.DatePicker(
                    description='Select Start Date:',
                    disabled=False,
                    value=min(self.modis_nrt_available_dates),  # Default value
                    min=min(self.modis_nrt_available_dates),  # Minimum value
                    max=max(self.modis_nrt_available_dates)  # Maximum value (assumes 31 days in max month)
                ),

                widgets.DatePicker(
                    description='Select End Date:',
                    disabled=False,
                    value=max(self.modis_nrt_available_dates),  # Default value
                    min=min(self.modis_nrt_available_dates),  # Minimum value
                    max=max(self.modis_nrt_available_dates)  # Maximum value (assumes 31 days in max month)
                )])

            self.modis_nrt_date_vbox.children = [self.date_picker_modis_nrt]

        elif single_or_date_range_value == 'All Available Images':
            self.modis_nrt_date_vbox.children = []

        return single_or_date_range_value

    def on_population_source_change(self, change):
        """
        :param change: dictionary containing the new value of the population source
        :return: None
        """
        try:
            print("Entered on_population_source_change")  # Debug print
            new_population_source = change['new']
            print(f"Population source changed to {new_population_source}")  # Debug print

            # Update population_source_variable and population_source_year based on the new_population_source
            if new_population_source == 'WorldPop':
                self.population_source_variable.options = self.worldpop_instance.data_type_options
                self.population_source_year.options = [x for x in self.worldpop_instance.year_options]

            elif new_population_source == 'GPWv4':
                self.population_source_variable.options = {x['name']: x['layer'] for x in self.gpwv4_instance.data_type_options if x['name'] != 'Population Density'}
                self.population_source_year.options = [x for x in self.gpwv4_instance.year_options]

            # Debug prints to verify the updates
            print(f"Updated variable options: {self.population_source_variable.options}")
            print(f"Updated year options: {self.population_source_year.options}")

            # Ensure the value is set to one of the available options
            self.population_source_variable.value = self.population_source_variable.options[0]
            self.population_source_year.value = self.population_source_year.options[0]
        except Exception as e:
            print(f"Error in on_population_source_change: {e}")

    def get_modis_nrt_dates(self) -> List[datetime.date]:
        """
        Retrieves the MODIS NRT dates from the NASA API.

        :return: A list of datetime.date objects representing the MODIS NRT dates.
        """
        response = requests.get(
            f'https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/details/allData/61/MCDWD_L3_NRT?fields=all&formats=json')
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

    def create_widgets_for_modis_nrt(self) -> List[widgets.Widget]:
        """
        Create widgets for MODIS NRT.

        :return: A list of widgets.
        """
        with self.out:
            self.modis_nrt_available_dates = self.get_modis_nrt_dates()

            self.single_or_date_range_modis_nrt = widgets.ToggleButtons(
                options=self.date_type_options,
                disabled=False,
                value='Single Date',
                tooltips=['Single Date', 'Date Range', 'All Available Images'],
            )

            self.modis_nrt_band_selection = widgets.Dropdown(
                options=[x for x in self.nrt_band_options.keys()],
                description='Band:',
                disabled=False,
                value='Flood 3-Day 250m Grid_Water_Composite',
                style={'description_width': 'initial'},
            )

            self.modis_nrt_date_vbox = widgets.VBox([])
            self.on_single_or_date_range_change_modis_nrt({'new': self.single_or_date_range_modis_nrt.value})

            self.single_or_date_range_modis_nrt.observe(
                lambda change: self.on_single_or_date_range_change_modis_nrt(change),
                names='value'
            )

            self.calculate_population = widgets.Checkbox(
                value=False,
                description='Calculate Population in Flood Area: ',
                disabled=False,
                indent=False
            )

            self.population_source = widgets.Dropdown(
                options=self.population_source_options,
                description='Population Source:',
                disabled=False,
                value='WorldPop',
                style={'description_width': 'initial'},
            )

            self.population_source_variable = widgets.Dropdown(
                options=self.population_source_variables,
                description='Population Variable:',
                disabled=False,
                value='Residential Population',
                style={'description_width': 'initial'},
            )

            self.population_source_year = widgets.Dropdown(
                options=self.population_source_year_options,
                description='Population Year:',
                disabled=False,
                value=2020,
                style={'description_width': 'initial'},
            )

            self.population_source_grid = widgets.Accordion([widgets.TwoByTwoLayout(
                top_left=self.calculate_population,
                top_right=self.population_source,
                bottom_left=self.population_source_variable,
                bottom_right=self.population_source_year
            )])

            self.population_source_grid.set_title(0, 'Population Options')

            self.add_image_to_map = widgets.Checkbox(description='Add Image to Map')
            self.create_sub_folder = widgets.Checkbox(description='Create Sub-folder')
            self.filechooser = fc.FileChooser(os.getcwd(), show_only_dirs=True)
            self.clip_to_geometry = widgets.Checkbox(
                value=True,
                description='Clip Image to Geometry Bounds',
                disabled=False,
                indent=False
            )

            self.keep_individual_tiles = widgets.Checkbox(
                value=False,
                description='Keep Individual Tiles',
                disabled=False,
                indent=False
            )

            self.end_of_vbox_items = widgets.Accordion([widgets.TwoByTwoLayout(
                top_left=self.create_sub_folder,
                top_right=self.clip_to_geometry,
                bottom_left=self.keep_individual_tiles,
                bottom_right=self.add_image_to_map
            )])

            self.end_of_vbox_items.set_title(0, 'Options')

            self.population_source.observe(self.on_population_source_change, names='value')

            # Return a list of widgets
            return [self.modis_nrt_band_selection, self.single_or_date_range_modis_nrt, self.modis_nrt_date_vbox,
                    self.filechooser, self.population_source_grid, self.end_of_vbox_items]

    def process_api(self, geometry: Any, distinct_values: Any, index: int, bbox, params=None) -> None:
        """
        Process API method to perform specific operations.

        :param geometry: The geometry for the operation.
        :param distinct_values: The distinct values for the operation.
        :param index: The index value for the operation.
        :param bbox: The bounding box for the operation.
        :param params: The optional parameters for the operation.
        :return: The path of the processed file.

        """



        if params['create_sub_folder']:
            folder = f"{params['folder_path']}/{str(datetime.datetime.now()).replace('-', '').replace('_', '').replace(':', '').replace('.', '')}/"
            os.mkdir(folder)

            params['folder_path'] = folder
            print(params['folder_path'])
        tiles = self.get_modis_tile(bbox)
        with self.out:
            self.out.clear_output()
            print(f'Processing tiles: {tiles}')
        matching_files = self.get_modis_nrt_file_list(tiles, params)

        hdf_files_to_process = []
        tif_list = []
        start=1
        for url in matching_files:
            self.download_and_process_modis_nrt(url, params['folder_path'], hdf_files_to_process, subdataset=self.modis_nrt_band_selection.value, tif_list=tif_list)
            start += 1

        merged_output = f'{folder}merged.tif'
        self.merge_tifs(tif_list, merged_output)
        for file in tif_list + hdf_files_to_process:
            if params['keep_individual_tiles']:
                pass
            else:
                try:
                    os.remove(file)
                except FileNotFoundError:
                    pass
        try:
            process_and_clip_raster(merged_output, geometry, params, self.ee_instance)
        except Exception as e:
            print(f"{e}")
        clipped_output = f'{folder}merged_clipped.tif'
        if params['calculate_population']:
            try:
                pop_impacted = self.calculate_population_in_flood_area(clipped_output,
                                                                       params['population_year'],
                                                                       params['population_data_type'],
                                                                       params['population_type'],
                                                                       params['folder_path'])
                print(pop_impacted)
            except Exception as e:
                print(f"{e}")

        return f'{folder}merged_clipped.tif'





    def gather_parameters(self) -> Dict[str, Any]:
        """
        :return: A dictionary containing the parameters for the method.

        The dictionary will have the following keys and values:
        - If `single_or_date_range_modis_nrt` is set to 'Single Date':
            - 'date': The selected date from `date_picker_modis_nrt`
            - 'multi_date': False
            - 'folder_path': The selected folder path from `filechooser`
            - 'create_sub_folder': The value of `create_sub_folder`
            - 'clip_to_geometry': The value of `clip_to_geometry`
            - 'keep_individual_tiles': The value of `keep_individual_tiles`
            - 'add_image_to_map': The value of `add_image_to_map`
            - 'calculate_population': The value of `calculate_population`
            - 'nrt_band': The value of `modis_nrt_band_selection`
            - 'population_year': The value of `population_source_year`
            - 'population_type': The value of `population_source_variable`
            - 'population_data_type': The value of `population_source`
        - If `single_or_date_range_modis_nrt` is set to 'Date Range':
            - 'start_date': The selected start date from `date_picker_modis_nrt`
            - 'end_date': The selected end date from `date_picker_modis_nrt`
            - 'multi_date': True
            - 'folder_path': The selected folder path from `filechooser`
            - 'create_sub_folder': The value of `create_sub_folder`
            - 'clip_to_geometry': The value of `clip_to_geometry`
            - 'keep_individual_tiles': The value of `keep_individual_tiles`
            - 'add_image_to_map': The value of `add_image_to_map`
            - 'calculate_population': The value of `calculate_population`
            - 'nrt_band': The value of `modis_nrt_band_selection`
            - 'population_year': The value of `population_source_year`
            - 'population_type': The value of `population_source_variable`
            - 'population_data_type': The value of `population_source`
        - If `single_or_date_range_modis_nrt` is neither 'Single Date' nor 'Date Range', returns None.

        """

        if self.single_or_date_range_modis_nrt.value == 'Single Date':
            date = self.date_picker_modis_nrt.value
            return {
                'date': date,
                'multi_date': False,
                'folder_path': self.filechooser.selected,
                'create_sub_folder': self.create_sub_folder.value,
                'clip_to_geometry': self.clip_to_geometry.value,
                'keep_individual_tiles': self.keep_individual_tiles.value,
                'add_image_to_map': self.add_image_to_map.value,
                'calculate_population': self.calculate_population.value,
                'nrt_band': self.modis_nrt_band_selection.value,
                'population_year': self.population_source_year.value,
                'population_type': self.population_source_variable.value,
                'population_data_type': self.population_source.value
            }
        elif self.single_or_date_range_modis_nrt.value == 'Date Range':
            start_date = self.date_picker_modis_nrt.children[0].value
            end_date = self.date_picker_modis_nrt.children[1].value
            return {
                'start_date': start_date,
                'end_date': end_date,
                'multi_date': True,
                'folder_path': self.filechooser.selected,
                'create_sub_folder': self.create_sub_folder.value,
                'clip_to_geometry': self.clip_to_geometry.value,
                'keep_individual_tiles': self.keep_individual_tiles.value,
                'add_image_to_map': self.add_image_to_map.value,
                'calculate_population': self.calculate_population.value,
                'nrt_band': self.modis_nrt_band_selection.value,
                'population_year': self.population_source_year.value,
                'population_type': self.population_source_variable.value,
                'population_data_type': self.population_source.value,
            }
        else:
            pass


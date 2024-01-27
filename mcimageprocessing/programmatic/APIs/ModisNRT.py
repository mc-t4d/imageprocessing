import pandas as pd

from typing import Union, Set, List, Tuple, Dict, Optional
from shapely.geometry import Point
from pyproj import Proj, transform
import re
import requests
from bs4 import BeautifulSoup
import datetime
from osgeo import ogr, osr, gdal
from shapely.geometry.base import BaseGeometry
import rasterio
import numpy as np
from shapely.geometry import shape
import geopandas as gpd
import ipywidgets as widgets
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from rasterio.features import shapes
import ee
import json
import os
from mcimageprocessing.programmatic.APIs.EarthEngine import EarthEngineManager
from mcimageprocessing.programmatic.APIs.WorldPop import WorldPop
from mcimageprocessing.programmatic.shared_functions.shared_utils import process_and_clip_raster
import pkg_resources
from mcimageprocessing import config_manager
import ipyfilechooser as fc
import os
import re

import requests
from bs4 import BeautifulSoup
from osgeo import gdal

from typing import Dict, Any, List
from mcimageprocessing.programmatic.shared_functions.shared_utils import process_and_clip_raster

# Initialize Earth Engine credentials
# credentials = ee.ServiceAccountCredentials(
#     email=config_manager.config['KEYS']['GEE']['client_email'],
#     key_data=config_manager.config['KEYS']['GEE']['private_key']
# )
#
# ee.Initialize(credentials)
#
# ee_instance = EarthEngineManager()

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
        self.modis_download_token = config_manager.config['KEYS']['MODIS_NRT']['token']  # Token for MODIS NRT download
        self.headers = {'Authorization': f'Bearer {self.modis_download_token}'}  # Token for MODIS NRT download
        self.ee_instance = ee_manager if ee_manager else EarthEngineManager()

    def calculate_modis_tile_index(self, x: float, y: float) -> tuple[int, int]:
        """
        Calculate MODIS tile index based on the given x and y coordinates.

        :param x: The x coordinate.
        :param y: The y coordinate.
        :return: The MODIS tile index as a tuple (h, v).
        """
        h = int((x + 20015109.354) // self.modis_tile_size)
        v = int((10007554.677 - y) // self.modis_tile_size)  # Adjust for Northern Hemisphere
        return h, v

    def get_modis_tile(self, geometry: Union[Point, list, pd.DataFrame]) -> Set[tuple[int, int]]:
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

    def get_modis_nrt_file_list(self, tiles: List[Tuple[int, int]], modis_nrt_params: Dict[str, datetime.datetime]) -> \
    List[str]:
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
        # Extract the year and the day of the year from the string
        year = int(date_string[:4])
        day_of_year = int(date_string[4:])

        # Calculate the date by adding the day of the year to the start of the year
        date = datetime.datetime(year, 1, 1) + datetime.timedelta(days=day_of_year - 1)

        return date

    def calculate_population_in_flood_area(self, raster_path: str, year: int, population_data_type: str, population_data_source: str, folder_output: str) -> str:
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

        print(population_data_type, year, population_data_source)

        if population_data_source == 'Google Earth Engine':

            worldpop = WorldPop()

            if population_data_type == 'Residential Population':

                worldpop_params = {
                    'api_source': population_data_source,
                    'year': year,
                    'datatype': population_data_type,
                    'statistics_only': False,
                    'add_image_to_map': False,
                    'create_sub_folder': False,
                    'folder_output': folder_output,
                }

                image = worldpop.process_worldpop_api(multi_geom, None, None, worldpop_params)

                return f'Population impacted: {"{:,}".format(round(ee_instance.get_image_sum(image, multi_geom, 100)))}'

                # return f'Population impacted: {image}'


            else:
                worldpop_params = {
                    'api_source': population_data_source,
                    'year': year,
                    'datatype': population_data_type,
                    'statistics_only': True,
                    'add_image_to_map': False,
                    'create_sub_folder': False,
                    'folder_output': folder_output,
                }

                image = worldpop.process_worldpop_api(multi_geom, None, None, worldpop_params)

                return f'Population impacted: {image}'

                # return f'Population impacted: {stats}'

                # return f'Population impacted: {"{:,}".format(round(ee_instance.get_image_sum(image, multi_geom, 100)))}'


            # image, geometry, scale = ee_instance.get_image(multi_date=True, start_date=f'{year}-01-01',
            #                                                end_date=f'{year}-12-31',
            #                                                image_collection='WorldPop/GP/100m/pop', band='population',
            #                                                geometry=multi_geom, aggregation_method='max')
        else:
            pass


        # return f'Population impacted: {"{:,}".format(round(ee_instance.get_image_sum(image, multi_geom, 100)))}'

    def shapely_to_ee(self, geometry: BaseGeometry, crs: str = 'EPSG:4326') -> ee.Geometry:
        """Convert a shapely geometry to a GEE geometry."""
        geojson = gpd.GeoSeries([geometry]).set_crs(crs).to_json()
        geojson_dict = json.loads(geojson)
        ee_geometry = ee.Geometry(geojson_dict['features'][0]['geometry'])
        return ee_geometry

    def process_modis_nrt_api(self, geometry: Any, distinct_values: Any, index: int, params: dict, bbox) -> None:
        modis_nrt_params = params

        print(modis_nrt_params)

        folder = self.create_sub_folder(modis_nrt_params)
        tiles = self.get_tiles(bbox)
        matching_files = self.find_matching_files(tiles, modis_nrt_params)

        hdf_files_to_process, tif_list = self.download_and_process_files(matching_files, modis_nrt_params)
        merged_output = self.merge_files(tif_list, folder)

        self.cleanup_files(tif_list, hdf_files_to_process, modis_nrt_params)
        self.finalize_processing(merged_output, geometry, modis_nrt_params)

    def get_tiles(self, bbox: Any) -> List[Any]:
        tiles = self.get_modis_tile(bbox)
        print(f'Processing tiles: {tiles}')
        return tiles

    def find_matching_files(self, tiles: List[Any], modis_nrt_params: Dict[str, Any]) -> List[str]:
        return self.get_modis_nrt_file_list(tiles, modis_nrt_params)

    def download_and_process_files(self, matching_files: List[str], modis_nrt_params: Dict[str, Any]) -> (List[str], List[str]):
        hdf_files_to_process = []
        tif_list = []
        for url in matching_files:
            self.download_and_process_modis_nrt(url, modis_nrt_params['folder_path'], hdf_files_to_process, subdataset=modis_nrt_params['nrt_band'], tif_list=tif_list)
        return hdf_files_to_process, tif_list

    def finalize_processing(self, merged_output: str, geometry: Any, modis_nrt_params: Dict[str, Any]) -> None:
        process_and_clip_raster(merged_output, geometry, modis_nrt_params, ee_instance)
        print('Processing Complete!')
        if modis_nrt_params['calculate_population']:
            clipped_output = f'{modis_nrt_params["folder_path"]}/merged_clipped.tif'
            pop_impacted = self.calculate_population_in_flood_area(clipped_output, modis_nrt_params['population_year'], modis_nrt_params['population_type'], modis_nrt_params['population_data_type'],
                                                                   modis_nrt_params['folder_path'])
            print(pop_impacted)

    def cleanup_files(self, tif_list: List[str], hdf_files_to_process: List[str], modis_nrt_params: Dict[str, Any]) -> None:
        if not modis_nrt_params['keep_individual_tiles']:
            for file in tif_list + hdf_files_to_process:
                try:
                    os.remove(file)
                except FileNotFoundError:
                    pass

    def merge_files(self, tif_list: List[str], folder: str) -> str:
        merged_output = os.path.join(folder, 'merged.tif')
        self.merge_tifs(tif_list, merged_output)
        return merged_output

    def create_sub_folder(self, modis_nrt_params: Dict[str, Any]) -> str:
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
        super().__init__(ee_manager)  # Initialize the base WorldPop class
        self.out = widgets.Output()  # For displaying logs, errors, etc.
        # Initialize widgets
        self.create_widgets_for_modis_nrt()

    def on_single_or_date_range_change_modis_nrt(self, change: Dict[str, Any]) -> Any:
        """
        Handles the change event when the option for single date or date range is changed.

        :param change: A dictionary containing information about the change event.
        :param glofas_option: The selected Glofas option.
        :return: None

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
            self.date_picker_modis_nrt = HBox([
                DatePicker(
                    description='Select Start Date:',
                    disabled=False,
                    value=min(self.modis_nrt_available_dates),  # Default value
                    min=min(self.modis_nrt_available_dates),  # Minimum value
                    max=max(self.modis_nrt_available_dates)  # Maximum value (assumes 31 days in max month)
                ),

                DatePicker(
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

    def get_modis_nrt_dates(self) -> List[datetime.date]:
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

    def create_widgets_for_modis_nrt(self) -> List[widgets.Widget]:
        """
        Create widgets specific to GloFas Data Type 2

        :param glofas_option: The selected GloFas option
        :return: A list of widgets specific to the selected GloFas option
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
                disabled=True,
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

            # Return a list of widgets
            return [self.modis_nrt_band_selection, self.single_or_date_range_modis_nrt, self.modis_nrt_date_vbox,
                    self.filechooser, self.population_source_grid, self.end_of_vbox_items]

    def process_modis_nrt_api(self, geometry: Any, distinct_values: Any, index: int, bbox) -> None:
        """
        :param geometry: The geometry of the area of interest.
        :param distinct_values: A boolean indicating whether distinct values should be used.
        :param index: The index for the MODIS NRT API.
        :return: None

        This method processes MODIS NRT API data for a given geometry, distinct values setting, and index. It first calculates the bounding box of the geometry using the provided distinct values
        *. It then gathers the required parameters for the MODIS NRT API. The parameters are printed to the console.

        If the 'create_sub_folder' parameter is True, a sub-folder is created with the current timestamp as the folder name. The 'folder_path' parameter is updated accordingly.

        Next, the method retrieves the MODIS tiles intersecting the bounding box. The tile numbers are printed to the console.

        The method then searches for matching files for each tile based on the provided year, day of year, and tile number. The URLs of the matching files are retrieved using requests and BeautifulSoup
        *.

        The method downloads the HDF files and saves them in the specified folder path. The paths to the downloaded HDF files are stored in the 'hdf_files_to_process' list.

        For each HDF file, the method opens it using GDAL and retrieves the subdatasets. It selects a subdataset and opens it. The subdataset is then converted to a GeoTIFF file. The paths to
        * the generated GeoTIFF files are stored in the 'tif_list' list.

        Upon completion of processing all HDF files, the method merges the generated GeoTIFF files into a single GeoTIFF file using GDAL.

        If the 'keep_individual_tiles' parameter is True, the individual tile files are kept. Otherwise, they are deleted.

        Finally, the method calls another method 'process_and_clip_raster' to process and clip the merged GeoTIFF file based on the provided geometry and MODIS NRT API parameters.
        """

        modis_nrt_params = self.gather_modis_nrt_parameters()

        print(modis_nrt_params)

        if modis_nrt_params['create_sub_folder']:
            folder = f"{modis_nrt_params['folder_path']}/{str(datetime.datetime.now()).replace('-', '').replace('_', '').replace(':', '').replace('.', '')}/"
            os.mkdir(folder)

            modis_nrt_params['folder_path'] = folder
        tiles = self.get_modis_tile(bbox)
        with self.out:
            self.out.clear_output()
            print(f'Processing tiles: {tiles}')
        matching_files = self.get_modis_nrt_file_list(tiles, modis_nrt_params)

        hdf_files_to_process = []
        tif_list = []
        start=1
        for url in matching_files:
            self.download_and_process_modis_nrt(url, modis_nrt_params['folder_path'], hdf_files_to_process, subdataset=self.modis_nrt_band_selection.value, tif_list=tif_list)
            start += 1

        merged_output = f'{folder}merged.tif'
        self.merge_tifs(tif_list, merged_output)
        for file in tif_list + hdf_files_to_process:
            if modis_nrt_params['keep_individual_tiles']:
                pass
            else:
                try:
                    os.remove(file)
                except FileNotFoundError:
                    pass
        process_and_clip_raster(merged_output, geometry, modis_nrt_params, ee_instance)

        clipped_output = f'{folder}merged_clipped.tif'
        if modis_nrt_params['calculate_population']:
            with self.out:
                self.out.clear_output()
                pop_impacted = self.calculate_population_in_flood_area(clipped_output, modis_nrt_params['year'])
                print(pop_impacted)


    def gather_modis_nrt_parameters(self) -> Dict[str, Any]:
        """
        Gathers the parameters for the MODIS NRT processing.

        :return: A dictionary containing the gathered parameters:
                 - 'date' or 'start_date' and 'end_date': The selected date(s) for processing.
                 - 'multi_date': True if date range selected, False otherwise.
                 - 'folder_path': The selected folder path where the output will be saved.
                 - 'create_sub_folder': True if output should be saved in a sub-folder, False otherwise.
                 - 'clip_to_geometry': True if the output should be clipped to a provided geometry, False otherwise.
                 - 'keep_individual_tiles': True if individual tiles should be saved, False otherwise.
                 - 'add_to_map': True if the processed image should be added to the map, False otherwise.
        """

        population_source = 'Google Earth Engine' if self.population_source.value == 'WorldPop' else 'GPWv4'
        if self.single_or_date_range_modis_nrt.value == 'Single Date':
            date = self.date_picker_modis_nrt.value
            return {
                'date': date,
                'multi_date': False,
                'folder_path': self.filechooser.selected,
                'create_sub_folder': self.create_sub_folder.value,
                'clip_to_geometry': self.clip_to_geometry.value,
                'keep_individual_tiles': self.keep_individual_tiles.value,
                'add_to_map': self.add_image_to_map.value,
                'calculate_population': self.calculate_population.value,
                'nrt_band': self.modis_nrt_band_selection.value,
                'population_year': self.population_source_year.value,
                'population_type': self.population_source_variable.value,
                'population_data_type': population_source
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
                'add_to_map': self.add_image_to_map.value,
                'calculate_population': self.calculate_population.value,
                'nrt_band': self.modis_nrt_band_selection.value,
                'population_year': self.population_source_year.value,
                'population_type': self.population_source_variable.value,
                'population_data_type': population_source
            }
        else:
            pass


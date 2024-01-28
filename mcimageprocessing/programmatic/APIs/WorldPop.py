import datetime
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List
from typing import Optional

import ee
import ipyfilechooser as fc
import ipywidgets as widgets
from geojson import Feature, FeatureCollection
from ipywidgets import Layout

from mcimageprocessing.programmatic.APIs.EarthEngine import EarthEngineManager
from mcimageprocessing.programmatic.shared_functions.utilities import mosaic_images


class WorldPop:
    """
    WorldPop class

    A class for processing WorldPop data using the WorldPop API or Google Earth Engine.

    Attributes:
    - worldpop_agesex_bands (list): List of age and sex bands for WorldPop data.
    - ee_auth_path (str): Path to the authentication file for Google Earth Engine.
    - ee_instance (EarthEngineManager): Instance of the EarthEngineManager class for managing interactions with Google Earth Engine.

    Methods:
    - __init__(): Initializes the class with default values.
    - process_residential_population(geometry, params): Process Residential Population data.
    - mosaic_images(file_names, output_filename): Mosaic images and save as a single file.
    - download_and_process_image(image, geometry, scale, params, band): Download and process the image.
    - process_age_and_sex_structures(geometry, params): Process Age and Sex Structures data.
    - get_image_dates(): Get the dates of the WorldPop population data.
    - validate_parameters(params): Validate the parameters.
    - process_worldpop_api(geometry, distinct_values, index, params=None): Method to process WorldPop API data for given parameters.
    """

    data_type_options = ['Residential Population', 'Age and Sex Structures']
    year_options = [str(x) for x in range(2000, 2021, 1)]
    source_options = ['WorldPop API', 'Google Earth Engine']

    def __init__(self, ee_manager: Optional[EarthEngineManager] = None):
        self.worldpop_agesex_bands = ['population', 'M_0', 'M_1', 'M_5', 'M_10', 'M_15', 'M_20', 'M_25', 'M_30', 'M_35',
                                      'M_40', 'M_45', 'M_50', 'M_55', 'M_60', 'M_65', 'M_70', 'M_75', 'M_80', 'F_0',
                                      'F_1', 'F_5', 'F_10', 'F_15', 'F_20', 'F_25', 'F_30', 'F_35', 'F_40',
                                      'F_45', 'F_50', 'F_55', 'F_60', 'F_65', 'F_70', 'F_75', 'F_80']

        self.ee_instance = ee_manager if ee_manager else EarthEngineManager()
        self.logger = logging.getLogger(__name__)

    def _validate_parameters(self, params: Dict[str, Any]) -> bool:
        required_keys = ['folder_output', 'api_source', 'year', 'datatype']
        for key in required_keys:
            if key not in params:
                self.logger.error(f"Missing required worldpop_param: {key}")
                return False
            if not params[key]:
                self.logger.error(f"worldpop_param {key} is empty or invalid.")
                return False
        return True

    def _create_sub_folder(self, base_folder: str) -> str:
        folder_name = os.path.join(base_folder, datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
        try:
            os.mkdir(folder_name)
            return folder_name
        except OSError as e:
            self.logger.error(f"Failed to create subfolder: {e}")
            return base_folder

    def process_residential_population(self, geometry: Any, params: Dict[str, Any]) -> Any:
        """
        Process residential population based on the given parameters.

        :param geometry: The geometry to apply the process on.
        :type geometry: Any
        :param params: The parameters needed for the WorldPop processing.
        :type params: Dict[str, Any]
        :return: The processed image if statistics_only is not True, otherwise the calculated statistics.
        :rtype: Any
        """

        if params['statistics_only']:
            all_stats = ee.Dictionary()

        band = 'population'
        image, geometry, scale = self.ee_instance.get_image(
            multi_date=True,
            start_date=f'{params["year"]}-01-01',
            end_date=f'{params["year"]}-12-31',
            image_collection='WorldPop/GP/100m/pop',
            band=band,
            geometry=geometry,
            aggregation_method='max')

        geojson = geometry.getInfo()
        multipolygon_feature = Feature(geometry=geojson)

        feature_collection = FeatureCollection([multipolygon_feature])

        if params['statistics_only']:
            # Assuming 'image', 'geometry', 'scale', and 'band' are defined and available in this scope
            sum_value = self.ee_instance.get_image_sum(image, geometry, scale, band)
            print(sum_value)  # Print the sum value
            all_stats = all_stats.set(band, sum_value)  # Store the sum value in the dictionary
            all_stats_info = all_stats.getInfo()  # This will fetch the results if 'all_stats' is an ee.Dictionary
            return all_stats_info

        self.download_and_process_image(image, geometry, scale, params, band)
        return image


    def download_and_process_image(self, image: ee.Image, geometry: Any, scale: Any, params: Dict[str, Any],
                                   band: str) -> None:
        """
        Downloads and processes an image.

        :param image: The Earth Engine image to download.
        :param geometry: The geometry to clip the image to.
        :param scale: The scale of the image to download.
        :param params: Additional parameters for WorldPop.
        :param band: The band of the image to download.
        :return: None
        """
        file_names, download_successful = self.ee_instance.download_and_split(image, geometry, scale,
                                                                  params=params,
                                                                  band=band)

        if not download_successful:
            output_filename = f"mosaic_{band}.tif"
            output_filename = f"{params['folder_output']}/{output_filename}"
            mosaic_images(file_names, output_filename)
        else:
            print(f"Downloaded {file_names[0]} successfully without needing to mosaic.")

    def process_age_and_sex_structures(self, geometry, params):
        all_stats = {}

        if params['statistics_only']:
            all_computed_stats = ee.Dictionary()

            for band in self.worldpop_agesex_bands:
                # Assuming self.get_image is a method that fetches the image. You might need to replace this with your actual method to get the image.
                image, geometry, scale = self.ee_instance.get_image(
                    multi_date=True,
                    start_date='2020-01-01',
                    end_date='2020-12-31',
                    image_collection='WorldPop/GP/100m/pop_age_sex_cons_unadj',
                    band=band,
                    geometry=geometry,
                    aggregation_method='max'
                )

                # Calculate statistics for the band and add it to the dictionary of all computed stats.
                stats = self.ee_instance.calculate_statistics(image, geometry, band)
                all_computed_stats = all_computed_stats.set(band, stats)

            # Now, fetch all results with a single .getInfo() call to reduce the number of requests to the server.
            all_stats_info = all_computed_stats.getInfo()

            # Process and rename the stats for each band.
            for band, stats_info in all_stats_info.items():
                stats_dict = {
                    'Mean': stats_info.get(band + '_mean'),
                    'Sum': stats_info.get(band + '_sum'),
                    'Max': stats_info.get(band + '_max'),
                    'Min': stats_info.get(band + '_min'),
                    'Standard Deviation': stats_info.get(band + '_stdDev'),
                    'Variance': stats_info.get(band + '_variance'),
                    'Median': stats_info.get(band + '_median')
                }
                all_stats[band] = stats_dict  # Add the structured stats to the all_stats dictionary.

            return all_stats
        else:
            for band in self.worldpop_agesex_bands:
                image, geometry, scale = self.ee_instance.get_image(
                    multi_date=True,
                    start_date='2020-01-01',
                    end_date='2020-12-31',
                    image_collection='WorldPop/GP/100m/pop_age_sex_cons_unadj',
                    band=band,
                    geometry=geometry,
                    aggregation_method='max'
                )
                self.download_and_process_image(image, geometry, scale, params, band)
                return None

    def get_image_dates(self) -> List[datetime.datetime]:
        """
        Returns the dates of the images in the given image collection.

        :return: A list of dates representing the dates of the images in the image collection.
        """
        # Get the image collection
        image_collection = self.ee_instance.get_image_collection_dates("WorldPop/POP")

        # Get the dates
        dates = self.ee_instance.get_image_dates(image_collection)

        return dates

    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """
        Validates the parameters for the params.

        :param params: A dictionary containing the worldpop parameters.
                                It should have the following keys:
                                - folder_output: The output folder path.
                                - api_source: The API source (either 'WorldPop' or 'Google Earth Engine').
                                - year: The year.
                                - datatype: The data type.

        :return: True if all parameters are valid, False otherwise.
        """
        if not params['folder_output']:
            print("Please select an output folder.")
            return False

        if not os.path.exists(params['folder_output']):
            print("The selected output folder does not exist.")
            return False

        if not params['api_source'] in ['WorldPop', 'Google Earth Engine']:
            print("Please select a valid API source.")
            return False

        if not params['year']:
            print("Please select a valid year.")
            return False

        if not params['datatype']:
            print("Please select a valid data type.")
            return False

        return True

    def process_api(self, geometry: Any, distinct_values: Any, index: Any, params: Dict[str, Any] = None, bbox=None) -> Any:
        print('Processing!')
        if not self._validate_parameters(params):
            return

        if params.get('create_sub_folder'):
            params['folder_output'] = self._create_sub_folder(params['folder_output'])

        geometry = self.ee_instance.ee_ensure_geometry(geometry)

        if 'datatype' in params:
            if params['datatype'] == 'Residential Population':
                image = self._process_datatype_residential_population(geometry, params)
                return image
            elif params['datatype'] == 'Age and Sex Structures':
                print(f'Processing {params["datatype"]}...')
                return self._process_datatype_age_and_sex_structures(geometry, params)
            else:
                self.logger.error('No valid data type provided.')
        else:
            self.logger.error("No valid params provided.")

    def _process_datatype_residential_population(self, geometry, params):
        image = self.process_residential_population(geometry, params)
        if params['statistics_only']:
            self._save_statistics(params['folder_output'], image)
        return image

    def _process_datatype_age_and_sex_structures(self, geometry, params):
        try:
            statistics = self.process_age_and_sex_structures(geometry, params)
            if params['statistics_only']:
                self._save_statistics(params['folder_output'], statistics)
            return statistics
        except Exception as e:
            print(e)

    def _save_statistics(self, folder_output: str, data: Any):
        try:
            with open(os.path.join(folder_output, 'statistics.json'), 'w') as f:
                f.write(str(data))
        except IOError as e:
            self.logger.error(f"Error saving statistics: {e}")


class WorldPopNotebookInterface(WorldPop):
    def __init__(self, ee_manager: Optional[EarthEngineManager] = None):
        super().__init__(ee_manager)  # Initialize the base WorldPop class
        self.out = widgets.Output()  # For displaying logs, errors, etc.
        # Initialize widgets
        self.create_widgets_for_worldpop()

    def create_widgets_for_worldpop(self) -> List[widgets.Widget]:
        self.worldpop_data_source = widgets.ToggleButtons(
            options=self.source_options,
            disabled=False,
            value=self.source_options[1],  # Default to 'Google Earth Engine'
            tooltips=['Obtain data directly from WorldPop API', 'Google Earth Engine'],
        )
        self.worldpop_data_type = widgets.Dropdown(
            options=self.data_type_options,
            value=self.data_type_options[0],  # Default to 'Residential Population'
            description='Data Type:',
            disabled=False,
            layout=Layout(width='auto')
        )
        self.worldpop_year = widgets.Dropdown(
            options=self.year_options,
            value=self.year_options[-1],  # Default to the last year
            description='Year:',
            disabled=False,
            layout=Layout(width='auto')
        )
        self.statistics_only_check = widgets.Checkbox(
            value=False,
            description='Image Statistics Only (dictionary)',
            disabled=False,
            indent=False
        )
        self.scale_input = widgets.Text(
            value='default',
            placeholder='Scale',
            description='Scale:',
            disabled=True,
            layout=Layout()
        )
        self.add_image_to_map = widgets.Checkbox(description='Add Image to Map')
        self.create_sub_folder = widgets.Checkbox(description='Create Sub-folder')
        self.filechooser = fc.FileChooser(os.getcwd(), show_only_dirs=True)
        self.gee_end_of_container_options = widgets.Accordion(
            [widgets.TwoByTwoLayout(
                top_left=self.statistics_only_check, top_right=self.add_image_to_map,
                bottom_right=self.create_sub_folder
            )])
        self.gee_end_of_container_options.set_title(0, 'Processing Options')
        self.widget_list = [
            self.worldpop_data_source,
            self.worldpop_data_type,
            self.worldpop_year,
            self.scale_input,
            self.filechooser,
            self.gee_end_of_container_options
        ]
        return self.widget_list

    def gather_parameters(self, **kwargs) -> Dict[str, Any]:
        # Ensure that you're accessing the correct attribute for the file chooser
        folder_output = self.filechooser.selected or self.filechooser.value
        print(folder_output)  # Debugging: Print the value to ensure it's correct

        # Return the parameters as a dictionary
        return {
            'api_source': self.worldpop_data_source.value,
            'year': self.worldpop_year.value,
            'datatype': self.worldpop_data_type.value,
            'statistics_only': self.statistics_only_check.value,
            'add_image_to_map': self.add_image_to_map.value,
            'create_sub_folder': self.create_sub_folder.value,
            'folder_output': folder_output,
            'band': 'population'
        }

    def process_api(self, geometry: Any, distinct_values: Any, index: int, params=None, bbox=None) -> None:
        try:
            image = super().process_api(geometry, distinct_values, index, params=self.gather_parameters())
            print('passed!')
            return image
        except Exception as e:
            print(e)
            return None


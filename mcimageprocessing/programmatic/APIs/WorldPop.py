import datetime
import logging
import os
from typing import Any, Dict, List
from typing import Optional

import ee
import json
import ipyfilechooser as fc
import ipywidgets as widgets
from geojson import Feature, FeatureCollection
from ipywidgets import Layout

from mcimageprocessing.programmatic.APIs.EarthEngine import EarthEngineManager
from mcimageprocessing.programmatic.shared_functions.utilities import mosaic_images


class WorldPop:
    """
    Class for processing WorldPop data.

    Args:
        ee_manager (Optional[EarthEngineManager]): An instance of EarthEngineManager (optional).

    Attributes:
        data_type_options (list[str]): List of valid data type options.
        year_options (list[str]): List of valid year options.

    """

    data_type_options = ['Residential Population', 'Age and Sex Structures']
    year_options = [str(x) for x in range(2000, 2021, 1)]

    def __init__(self, ee_manager: Optional[EarthEngineManager] = None):
        """
        Initialize the object.

        :param ee_manager: An instance of EarthEngineManager (optional).
        """
        self.worldpop_agesex_bands = ['population', 'M_0', 'M_1', 'M_5', 'M_10', 'M_15', 'M_20', 'M_25', 'M_30', 'M_35',
                                      'M_40', 'M_45', 'M_50', 'M_55', 'M_60', 'M_65', 'M_70', 'M_75', 'M_80', 'F_0',
                                      'F_1', 'F_5', 'F_10', 'F_15', 'F_20', 'F_25', 'F_30', 'F_35', 'F_40',
                                      'F_45', 'F_50', 'F_55', 'F_60', 'F_65', 'F_70', 'F_75', 'F_80']

        self.ee_instance = ee_manager if ee_manager else EarthEngineManager()
        self.logger = logging.getLogger(__name__)

    def _validate_parameters(self, params: Dict[str, Any]) -> bool:
        """
        Validate parameters for the given method.

        :param params: A dictionary of parameters.
        :return: True if all required keys are present and not empty, False otherwise.
        """
        required_keys = ['folder_output', 'year', 'datatype']
        for key in required_keys:
            if key not in params:
                self.logger.error(f"Missing required worldpop_param: {key}")
                return False
            if not params[key]:
                self.logger.error(f"worldpop_param {key} is empty or invalid.")
                return False
        return True

    def _create_sub_folder(self, base_folder: str) -> str:
        """
        :param base_folder: The base folder in which the subfolder will be created.
        :return: The path of the created subfolder.

        """
        folder_name = os.path.join(base_folder, f"WorldPop_processed_on_{str(datetime.datetime.now()).replace('-', '').replace('_', '').replace(':', '').replace('.', '')}")
        try:
            os.mkdir(folder_name)
            return folder_name
        except OSError as e:
            self.logger.error(f"Failed to create subfolder: {e}")
            return base_folder

    def process_residential_population(self, geometry: Any, params: Dict[str, Any]) -> Any:
        """
        :param geometry: The geometry representing the area of interest.
        :param params: A dictionary containing parameters for processing the residential population.
            - "statistics_only": A boolean indicating whether to only compute statistics or also download and process the image.
            - "year": A string representing the year to filter the image collection.
        :return: If "statistics_only" is True, returns a dictionary containing statistics of the residential population. Otherwise, returns the processed image.

        """

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

        try:
            if params['flood_pop_calc']:
                sum_value = self.ee_instance.get_image_sum(image, geometry, scale, band)
                all_stats = all_stats.set(band, sum_value)  # Store the sum value in the dictionary
                all_stats_info = all_stats.getInfo()  # This will fetch the results if 'all_stats' is an ee.Dictionary
                return all_stats_info
        except KeyError:
            pass

        if params['statistics_only']:
            # Assuming 'image', 'geometry', 'scale', and 'band' are defined and available in this scope
            sum_value = self.ee_instance.get_image_sum(image, geometry, scale, band)
            all_stats = all_stats.set(band, sum_value)  # Store the sum value in the dictionary
            all_stats_info = all_stats.getInfo()  # This will fetch the results if 'all_stats' is an ee.Dictionary
            return all_stats_info

        self.download_and_process_image(image, geometry, scale, params, band)
        return image


    def download_and_process_image(self, image: ee.Image, geometry: Any, scale: Any, params: Dict[str, Any],
                                   band: str) -> None:
        """
        Downloads and processes the given image.

        :param image: The Earth Engine image to be downloaded and processed.
        :param geometry: The geometry to filter the image by.
        :param scale: The scale of the image.
        :param params: Additional parameters for the download and processing.
        :param band: The specific band to be processed.

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
            pass

    def process_age_and_sex_structures(self, geometry, params):
        """
        Method to process age and sex structures for a given geometry.

        :param geometry: The geometry of interest.
        :param params: A dictionary of parameters.
            - 'statistics_only': If True, calculate statistics only. If False, download and process image.
        :return: A dictionary containing the processed age and sex statistics. If 'statistics_only' is True, the dictionary
                 will contain statistics for each band. If 'statistics_only' is False, the method returns None.
        """
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

                try:
                    if params['flood_pop_calc']:
                        sum_value = self.ee_instance.get_image_sum(image, geometry, scale, band)
                        all_stats[band] = round(sum_value)
                except KeyError:
                    pass


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
        :return: A list of datetime objects representing the dates of the images in the image collection.
        :rtype: List[datetime.datetime]
        """
        # Get the image collection
        image_collection = self.ee_instance.get_image_collection_dates("WorldPop/POP")

        # Get the dates
        dates = self.ee_instance.get_image_dates(image_collection)

        return dates

    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """
        Validate the parameters passed to the method.

        :param params: The parameters dictionary to validate.
        :type params: dict[str, any]
        :return: True if all the parameters are valid, False otherwise.
        :rtype: bool
        """
        if not params['folder_output']:
            print("Please select an output folder.")
            return False

        if not os.path.exists(params['folder_output']):
            print("The selected output folder does not exist.")
            return False

        if not params['api_source'] in ['WorldPop']:
            print("Please select a valid API source.")
            return False

        if not params['year']:
            print("Please select a valid year.")
            return False

        if not params['datatype']:
            print("Please select a valid data type.")
            return False

        return True

    def process_api(self, geometry: Any, distinct_values: Any, index: Any, params: Dict[str, Any] = None, bbox=None, pbar=None) -> Any:
        """
        Process API method.

        :param geometry: The geometry to process.
        :param distinct_values: The distinct values to process.
        :param index: The index to process.
        :param params: Additional parameters for processing (optional).
        :param bbox: The bounding box for processing (optional).
        :return: The processed result.

        """


        if not self._validate_parameters(params):
            return


        geometry = self.ee_instance.ee_ensure_geometry(geometry)

        if 'datatype' in params:
            if params['datatype'] == 'Residential Population':
                image = self._process_datatype_residential_population(geometry, params)
                return image, params['folder_output']
            elif params['datatype'] == 'Age and Sex Structures':
                return self._process_datatype_age_and_sex_structures(geometry, params), params['folder_output']
            else:
                self.logger.error('No valid data type provided.')
        else:
            self.logger.error("No valid params provided.")

    def _process_datatype_residential_population(self, geometry, params):
        """
        Process the datatype 'residential_population' for a given geometry and parameters.

        :param geometry: The geometry for which to process the residential population data.
        :param params: A dictionary of parameters for processing the data.
            - 'statistics_only' (bool): If True, only statistics will be calculated and saved.
            - 'folder_output' (str): The folder where the processed data will be saved.

        :return: The processed image of residential population.
        """
        image = self.process_residential_population(geometry, params)
        if params['statistics_only']:
            self._save_statistics(params['folder_output'], image)
        return image

    def _process_datatype_age_and_sex_structures(self, geometry, params):
        """
        Process datatype, age, and sex structures.

        :param geometry: The geometry to process.
        :param params: The parameters for processing.
        :return: The processed statistics.

        """
        try:
            statistics = self.process_age_and_sex_structures(geometry, params)
            if params['statistics_only']:
                self._save_statistics(params['folder_output'], statistics)
            return statistics
        except Exception as e:
            print(e)

    def _save_statistics(self, folder_output: str, data: Any):
        """
        Save statistics data to a JSON file.

        :param folder_output: The directory where the statistics file will be saved.
        :param data: The statistics data to be saved.
        :return: None
        :raises IOError: If there is an error while saving the statistics file.
        """
        try:
            with open(os.path.join(folder_output, 'statistics.json'), 'w') as f:
                f.write(str(data))
        except IOError as e:
            self.logger.error(f"Error saving statistics: {e}")


class WorldPopNotebookInterface(WorldPop):
    """
    WorldPopNotebookInterface
    ========================

    :class:`~WorldPopNotebookInterface` is a subclass of :class:`~WorldPop` class and provides an interface for interacting with the WorldPop API in a Jupyter Notebook environment.

    Attributes:
    -----------
    - ee_manager (:class:`~EarthEngineManager`, optional): An instance of the EarthEngineManager class. Defaults to None.

    Methods:
    --------
    __init__(ee_manager: Optional[:class:`~EarthEngineManager`] = None)
        Initializes the WorldPopNotebookInterface class.

    create_widgets_for_worldpop() -> List[:class:`~widgets.Widget`]
        Creates and returns a list of widgets for configuring the WorldPop parameters.

    gather_parameters(**kwargs) -> Dict[str, Any]
        Gathers user-selected parameters and returns them as a dictionary.

    process_api(geometry: Any, distinct_values: Any, index: int, params=None, bbox=None) -> None
        Processes the WorldPop API with the provided parameters.

    """
    def __init__(self, ee_manager: Optional[EarthEngineManager] = None):
        """
        Constructor for the class.

        :param ee_manager: An instance of the EarthEngineManager class.
                           If provided, it will be used for Earth Engine operations.
                           If not provided, Earth Engine functions will be unavailable.
        """
        super().__init__(ee_manager)  # Initialize the base WorldPop class
        self.out = widgets.Output()  # For displaying logs, errors, etc.
        # Initialize widgets
        self.create_widgets_for_worldpop()

    def create_widgets_for_worldpop(self) -> List[widgets.Widget]:
        """
        Create and initialize widgets for configuring WorldPop data parameters.

        :return: A list of widget objects.
        """
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
        self.add_image_to_map = widgets.Checkbox(description='Add Image to Map', value=True)
        self.create_sub_folder = widgets.Checkbox(description='Create Sub-folder', value=True)
        self.filechooser = fc.FileChooser(os.getcwd(), show_only_dirs=True)
        self.gee_end_of_container_options = widgets.Accordion(
            [widgets.TwoByTwoLayout(
                top_left=self.statistics_only_check, top_right=self.add_image_to_map,
                bottom_right=self.create_sub_folder
            )])
        self.gee_end_of_container_options.set_title(0, 'Processing Options')
        self.widget_list = [
            self.worldpop_data_type,
            self.worldpop_year,
            self.scale_input,
            self.filechooser,
            self.gee_end_of_container_options
        ]
        return self.widget_list

    def gather_parameters(self, **kwargs) -> Dict[str, Any]:
        """
        :param kwargs: Additional keyword arguments. No other parameters are required.

        :return: A dictionary containing the gathered parameters.

        """
        # Ensure that you're accessing the correct attribute for the file chooser
        folder_output = self.filechooser.selected or self.filechooser.value

        # Return the parameters as a dictionary
        return {
            'population_source': 'WorldPop',
            'year': self.worldpop_year.value,
            'datatype': self.worldpop_data_type.value,
            'statistics_only': self.statistics_only_check.value,
            'add_image_to_map': self.add_image_to_map.value,
            'create_sub_folder': self.create_sub_folder.value,
            'folder_output': folder_output,
            'band': 'population'
        }

    def process_api(self, geometry: Any, distinct_values: Any, index: int, params=None, bbox=None, pbar=None) -> None:
        """
        Process API.

        :param geometry: The geometry parameter.
        :param distinct_values: The distinct_values parameter.
        :param index: The index parameter.
        :param params: The params parameter.
        :param bbox: The bbox parameter.
        :return: None.
        """
        try:

            pbar.update(1)
            pbar.set_postfix_str(f"Processing {self.worldpop_data_type.value} for {self.worldpop_year.value}...")

            if params.get('create_sub_folder'):
                params['folder_output'] = self._create_sub_folder(params['folder_output'])

            params_file_path = os.path.join(params['folder_output'], 'parameters.json')

            with open(params_file_path, 'w') as f:
                json.dump(params, f)

            image, output_folder = super().process_api(geometry, distinct_values, index, params=params, pbar=pbar)
            # Serialize the geometry to GeoJSON
            if isinstance(geometry, ee.Geometry):
                geojson_geometry = geometry.getInfo()  # If geometry is an Earth Engine object
            elif isinstance(geometry, ee.Feature):
                geojson_geometry = geometry.getInfo()
            elif isinstance(geometry, ee.FeatureCollection):
                geojson_geometry = geometry.getInfo()
            else:
                geojson_geometry = geometry  # If geometry is already in GeoJSON format

            pbar.update(7)
            pbar.set_postfix_str(f"Saving geometry...")

            # Define the GeoJSON filename
            geojson_filename = os.path.join(params['folder_output'], 'geometry.geojson')

            # Write the GeoJSON to a file
            with open(geojson_filename, 'w') as f:
                f.write(json.dumps(geojson_geometry))

            pbar.update(2)
            pbar.set_postfix_str(f"Finished!")

            return image
        except Exception as e:
            print(e)
            return None


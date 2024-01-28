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


class GPWv4:
    """
    GPWv4

    A class for processing GPWv4 (Gridded Population of the World Version 4) data.

    Attributes:
        data_type_options (List[Dict[str, str]]): A list of dictionaries containing the available data types.
        year_options (List[str]): A list of string representations of available years.

    Methods:
        __init__(ee_manager: Optional[EarthEngineManager] = None) -> None:
            Initializes a GPWv4 instance.

        _validate_parameters(gpwv4_params: Dict[str, Any]) -> bool:
            Validates the parameters for GPWv4.

        _create_sub_folder(base_folder: str) -> str:
            Creates a subfolder within the given base folder.

        process_residential_population(geometry: Any, gpwv4_params: Dict[str, Any]) -> Any:
            Processes residential population based on the given parameters.

        download_and_process_image(image: ee.Image, geometry: Any, scale: Any, gpwv4_params: Dict[str, Any], band: str) -> None:
            Downloads and processes an image.

        validate_parameters(gpwv4_params: Dict[str, Any]) -> bool:
            Validates the parameters for GPWv4.

        process_gpwv4_api(geometry: Any, distinct_values: Any, index: Any, gpwv4_params: Dict[str, Any] = None) -> Any:
            Processes GPWv4 data based on the given parameters.

        _process_datatype_residential_population(geometry, gpwv4_params):
            Processes residential population for the given geometry and parameters.

        _process_datatype_age_and_sex_structures(geometry, gpwv4_params):
            Processes age and sex structures for the given geometry and parameters.

        _save_statistics(folder_output: str, data: Any):
            Saves the calculated statistics to a file.

    """

    data_type_options = [{"name": "Population Count", "layer": "CIESIN/GPWv411/GPW_Population_Count", 'band': 'population_count'},
                         {"name": "Population Density", "layer": "CIESIN/GPWv411/GPW_Population_Density", 'band': 'population_density'},
                         {"name": "UN-Adjusted Population Count", "layer": "CIESIN/GPWv411/GPW_UNWPP-Adjusted_Population_Count", 'band': 'unwpp-adjusted_population_count'}]
    year_options = [str(x) for x in range(2000, 2021, 5)]

    def __init__(self, ee_manager: Optional[EarthEngineManager] = None):

        self.ee_instance = ee_manager if ee_manager else EarthEngineManager()
        self.logger = logging.getLogger(__name__)

    def _validate_parameters(self, gpwv4_params: Dict[str, Any]) -> bool:
        required_keys = ['folder_output', 'year', 'datatype']
        for key in required_keys:
            if key not in gpwv4_params:
                self.logger.error(f"Missing required gpwv4_param: {key}")
                return False
            if not gpwv4_params[key]:
                self.logger.error(f"gpwv4_param {key} is empty or invalid.")
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

    def process_gpwv4_layer(self, geometry: Any, gpwv4_params: Dict[str, Any]) -> Any:
        """
        Process residential population based on the given parameters.

        :param geometry: The geometry to apply the process on.
        :type geometry: Any
        :param gpwv4_params: The parameters needed for the WorldPop processing.
        :type gpwv4_params: Dict[str, Any]
        :return: The processed image if statistics_only is not True, otherwise the calculated statistics.
        :rtype: Any
        """

        if gpwv4_params['statistics_only']:
            all_stats = ee.Dictionary()

        band = gpwv4_params['datatype']
        image, geometry, scale = self.ee_instance.get_image(
            multi_date=True,
            start_date=f'{gpwv4_params["year"]}-01-01',
            end_date=f'{gpwv4_params["year"]}-12-31',
            image_collection=gpwv4_params['datatype'],
            band=gpwv4_params['band'],
            geometry=geometry,
            aggregation_method='max')

        geojson = geometry.getInfo()
        multipolygon_feature = Feature(geometry=geojson)

        feature_collection = FeatureCollection([multipolygon_feature])



        if gpwv4_params['statistics_only']:
            stats = self.ee_instance.calculate_statistics(image, geometry, band)
            all_stats = all_stats.set(band, stats)
            all_stats_info = all_stats.getInfo()
            return all_stats_info

        self.download_and_process_image(image, geometry, scale, gpwv4_params, band)
        return image


    def download_and_process_image(self, image: ee.Image, geometry: Any, scale: Any, gpwv4_params: Dict[str, Any],
                                   band: str) -> None:
        """
        Downloads and processes an image.

        :param image: The Earth Engine image to download.
        :param geometry: The geometry to clip the image to.
        :param scale: The scale of the image to download.
        :param gpwv4_params: Additional parameters for WorldPop.
        :param band: The band of the image to download.
        :return: None
        """
        file_names, download_successful = self.ee_instance.download_and_split(image, geometry, scale,
                                                                  params=gpwv4_params,
                                                                  band=band)

        if not download_successful:
            output_filename = f"mosaic_{band}.tif"
            output_filename = f"{gpwv4_params['folder_output']}/{output_filename}"
            mosaic_images(file_names, output_filename)
        else:
            print(f"Downloaded {file_names[0]} successfully without needing to mosaic.")

    def validate_parameters(self, gpwv4_params: Dict[str, Any]) -> bool:
        """
        Validates the parameters for the GPWv4 processing.

        :param gpwv4_params: The dictionary containing the GPWv4 parameters.
        :type gpwv4_params: Dict[str, Any]
        :return: True if all parameters are valid, False otherwise.
        :rtype: bool
        """
        if not gpwv4_params['folder_output']:
            print("Please select an output folder.")
            return False

        if not os.path.exists(gpwv4_params['folder_output']):
            print("The selected output folder does not exist.")
            return False

        if not gpwv4_params['year']:
            print("Please select a valid year.")
            return False

        if not gpwv4_params['datatype']:
            print("Please select a valid data type.")
            return False

        return True

    def process_api(self, geometry: Any, distinct_values: Any, index: Any, params: Dict[str, Any] = None, bbox=None) -> Any:
        if not self._validate_parameters(params):
            return

        if params.get('create_sub_folder'):
            params['folder_output'] = self._create_sub_folder(params['folder_output'])


        geometry = self.ee_instance.ee_ensure_geometry(geometry)

        return self._process_datatype_residential_population(geometry, params)


    def _process_datatype_residential_population(self, geometry, gpwv4_params):
        image = self.process_gpwv4_layer(geometry, gpwv4_params)
        if gpwv4_params['statistics_only']:
            self._save_statistics(gpwv4_params['folder_output'], image)
        return image

    def _save_statistics(self, folder_output: str, data: Any):
        try:
            with open(os.path.join(folder_output, 'statistics.json'), 'w') as f:
                f.write(str(data))
        except IOError as e:
            self.logger.error(f"Error saving statistics: {e}")


class GPWv4NotebookInterface(GPWv4):
    """

    This class provides an interface to interact with the GPWv4 data in Earth Engine.

    Attributes:
        ee_manager (Optional[EarthEngineManager]): An optional EarthEngineManager object to handle authentication and
            Earth Engine tasks. Defaults to None.

    Methods:
        __init__(self, ee_manager: Optional[EarthEngineManager] = None)
            Initializes an instance of the GPWv4NotebookInterface class.

        create_widgets_for_gpwv4(self) -> List[widgets.Widget]
            Creates widgets for GPWv4 data selection and processing options.

        gather_gpwv4_parameters(self) -> Dict[str, Any]
            Gathers the selected parameters for GPWv4 data processing.

        process_gpwv4_data(self, geometry: Any, distinct_values: Any, index: int) -> None
            Processes GPWv4 data using the selected parameters.

    """
    def __init__(self, ee_manager: Optional[EarthEngineManager] = None):
        super().__init__(ee_manager)
        self.out = widgets.Output()
        # Initialize widgets
        self.create_widgets_for_gpwv4()

    def create_widgets_for_gpwv4(self) -> List[widgets.Widget]:
        with self.out:
            self.gpwv4_data_type = widgets.Dropdown(
                options={x['name']: x['layer'] for x in self.data_type_options},
                value=self.data_type_options[0]['layer'],
                description='Data Type:',
                disabled=False,
                layout=Layout(width='auto')
            )
            self.gpwv4_year = widgets.Dropdown(
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
                self.gpwv4_data_type,
                self.gpwv4_year,
                self.scale_input,
                self.filechooser,
                self.gee_end_of_container_options
            ]
            return self.widget_list

    def gather_parameters(self) -> Dict[str, Any]:
        # Ensure that you're accessing the correct attribute for the file chooser
        folder_output = self.filechooser.selected or self.filechooser.value

        # Return the parameters as a dictionary
        return {
            'year': self.gpwv4_year.value,
            'datatype': self.gpwv4_data_type.value,
            'band': self.data_type_options[self.gpwv4_data_type.index]['band'],
            'statistics_only': self.statistics_only_check.value,
            'add_image_to_map': self.add_image_to_map.value,
            'create_sub_folder': self.create_sub_folder.value,
            'folder_output': folder_output,
        }

    def process_api(self, geometry: Any, distinct_values: Any, index: int, params=None, bbox=None) -> None:
        with self.out:
            try:
                image = super().process_api(geometry, distinct_values, index, params=self.gather_parameters())
                return image
            except Exception as e:
                print(f"An error occurred: {e}")

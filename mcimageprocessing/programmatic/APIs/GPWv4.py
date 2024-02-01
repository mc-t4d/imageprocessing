import datetime
import json
import logging
import os
from typing import Any, Dict, List
from typing import Optional

import ee
import ipyfilechooser as fc
import ipywidgets as widgets
from ipywidgets import Layout

from mcimageprocessing.programmatic.APIs.EarthEngine import EarthEngineManager
from mcimageprocessing.programmatic.shared_functions.utilities import mosaic_images


class GPWv4:
    """
    Initialize the object.

    :param ee_manager: An instance of the EarthEngineManager class. If not provided, a new instance will be created.
    :type ee_manager: Optional[EarthEngineManager]
    """

    data_type_options = [{"name": "Population Count", "layer": "CIESIN/GPWv411/GPW_Population_Count", 'band': 'population_count'},
                         {"name": "Population Density", "layer": "CIESIN/GPWv411/GPW_Population_Density", 'band': 'population_density'},
                         {"name": "UN-Adjusted Population Count", "layer": "CIESIN/GPWv411/GPW_UNWPP-Adjusted_Population_Count", 'band': 'unwpp-adjusted_population_count'}]
    year_options = [str(x) for x in range(2000, 2021, 5)]

    def __init__(self, ee_manager: Optional[EarthEngineManager] = None):
        """
        Initialize the object.

        :param ee_manager: An instance of the EarthEngineManager class. If not provided, a new instance will be created.
        :type ee_manager: Optional[EarthEngineManager]
        """
        self.ee_instance = ee_manager if ee_manager else EarthEngineManager()
        self.logger = logging.getLogger(__name__)

    def _validate_parameters(self, gpwv4_params: Dict[str, Any]) -> bool:
        """
        Validates the given gpwv4_params dictionary.

        :param gpwv4_params: A dictionary containing the parameters for GPWv4.
                            Required keys: 'folder_output', 'year', 'datatype'.
        :type gpwv4_params: dict[str, any]
        :return: True if all required keys are present and not empty; False otherwise.
        :rtype: bool
        """
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
        """
        Create a new subfolder within the given base folder.

        :param base_folder: The path of the base folder where the subfolder will be created.
        :type base_folder: str
        :return: The path of the newly created subfolder.
        :rtype: str
        """
        folder_name = os.path.join(base_folder, f"GPWv4_processed_on_{str(datetime.datetime.now()).replace('-', '').replace('_', '').replace(':', '').replace('.', '')}")
        try:
            os.mkdir(folder_name)
            return folder_name
        except OSError as e:
            self.logger.error(f"Failed to create subfolder: {e}")
            return base_folder

    def process_gpwv4_layer(self, geometry: Any, gpwv4_params: Dict[str, Any]) -> Any:
        """
        :param geometry: The geometry object representing the area of interest for processing.
        :param gpwv4_params: The dictionary containing all the parameters for processing the GPWv4 layer.
        :return: The processed image or dictionary of statistics, depending on the value of the 'statistics_only' parameter.

        """

        try:

            if gpwv4_params['statistics_only']:
                all_stats = ee.Dictionary()

            if not gpwv4_params['band']:
                band = gpwv4_params['datatype']
            else:
                band = gpwv4_params['band']
            image, geometry, scale = self.ee_instance.get_image(
                multi_date=True,
                start_date=f'{gpwv4_params["year"]}-01-01',
                end_date=f'{gpwv4_params["year"]}-12-31',
                image_collection=gpwv4_params['datatype'],
                band=gpwv4_params['band'],
                geometry=geometry,
                aggregation_method='first')

            if gpwv4_params['statistics_only']:
                projection = image.select(0).projection()
                scale = projection.nominalScale()

                sum_value = self.ee_instance.get_image_sum(image, geometry, scale, band)

                all_stats = all_stats.set(band, sum_value)
                all_stats_info = all_stats.getInfo()
                return all_stats_info


            self.download_and_process_image(image, geometry, scale, gpwv4_params, band)
            return image

        except Exception as e:
            print(f"An error occurred: {e}")


    def download_and_process_image(self, image: ee.Image, geometry: Any, scale: Any, gpwv4_params: Dict[str, Any],
                                   band: str) -> None:
        """
        Downloads and processes an image by splitting it into tiles and optionally mosaicing them.

        :param image: The image to download and process.
        :param geometry: The geometry (region of interest) to download the image for.
        :param scale: The scale to use for downloading the image.
        :param gpwv4_params: Additional parameters for the download process.
        :param band: The band of the image to download and process.
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
            pass

    def validate_parameters(self, gpwv4_params: Dict[str, Any]) -> bool:
        """
        :param gpwv4_params: A dictionary containing the parameters for GPWv4 processing.
            - 'folder_output': The selected output folder.
            - 'year': The selected year.
            - 'datatype': The selected data type.

        :return: Returns True if all parameters are valid, False otherwise.
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

    def process_api(self, geometry: Any, distinct_values: Any, index: Any, params: Dict[str, Any] = None, bbox=None, pbar=None) -> Any:
        """
        Perform API processing.

        :param geometry: The geometry to process.
        :param distinct_values: The distinct values.
        :param index: The index.
        :param params: Additional parameters (optional).
        :param bbox: The bounding box (optional).
        :return: The processed result.
        """
        if not self._validate_parameters(params):
            return


        geometry = self.ee_instance.ee_ensure_geometry(geometry)

        return self._process_datatype_residential_population(geometry, params), params['folder_output']


    def _process_datatype_residential_population(self, geometry, gpwv4_params):
        """
        :param geometry: The geometry object containing the spatial area of interest.
        :param gpwv4_params: The parameters for processing the GPWv4 layer.
        :return: The processed image representing the residential population within the specified geometry.

        """
        image = self.process_gpwv4_layer(geometry, gpwv4_params)
        if gpwv4_params['statistics_only']:
            self._save_statistics(gpwv4_params['folder_output'], image)
        return image

    def _save_statistics(self, folder_output: str, data: Any):
        """
        Save statistics to a JSON file.

        :param folder_output: The path to the output folder where the JSON file will be saved.
        :param data: The data to be saved as JSON.
        :return: None

        Example usage:
            >>> _save_statistics('/path/to/output', {'stat1': 100, 'stat2': 200})
        """
        try:
            with open(os.path.join(folder_output, 'statistics.json'), 'w') as f:
                f.write(str(data))
        except IOError as e:
            self.logger.error(f"Error saving statistics: {e}")


class GPWv4NotebookInterface(GPWv4):
    """GPWv4NotebookInterface is a class that extends the base class GPWv4 and provides a user interface for interacting with the GPWv4 API in a Jupyter notebook.

    Usage:
    ------

    Instantiate an instance of GPWv4NotebookInterface by providing an optional instance of EarthEngineManager as the ee_manager parameter. If no ee_manager is provided, the default Earth
    *EngineManager will be used.

    Example:

        >>> interface = GPWv4NotebookInterface()

    Methods:
    --------

    __init__(ee_manager: Optional[EarthEngineManager] = None)
        Initializes a new instance of GPWv4NotebookInterface.

    Parameters:
        - ee_manager (Optional[EarthEngineManager]): An optional instance of EarthEngineManager to use.

    create_widgets_for_gpwv4() -> List[widgets.Widget]
        Creates the interactive widgets for the GPWv4 API.

    Returns:
        - List[widgets.Widget]: A list of Widget objects that represent the interactive widgets.

    gather_parameters() -> Dict[str, Any]
        Gathers the parameters from the interactive widgets.

    Returns:
        - Dict[str, Any]: A dictionary of parameter name-value pairs.

    process_api(geometry: Any, distinct_values: Any, index: int, params=None, bbox=None) -> None
        Processes the GPWv4 API using the provided parameters and displays the result.

    Parameters:
        - geometry (Any): The geometry to process.
        - distinct_values (Any): The distinct values to process.
        - index (int): The index of the item to process.
        - params (Optional[Dict[str, Any]]): An optional dictionary of parameter name-value pairs. If not provided, the parameters will be gathered from the interactive widgets.
        - bbox (Optional[Any]): An optional bounding box to use for filtering the data. If not provided, no filtering will be applied.

    Returns:
        - None
    """
    def __init__(self, ee_manager: Optional[EarthEngineManager] = None):
        """
        Initializes an instance of the class.

        :param ee_manager: An optional parameter of type EarthEngineManager. It represents the Earth Engine manager
                           used for interacting with the Earth Engine Python API.
        """
        super().__init__(ee_manager)
        self.out = widgets.Output()
        # Initialize widgets
        self.create_widgets_for_gpwv4()

    def create_widgets_for_gpwv4(self) -> List[widgets.Widget]:
        """
        Returns a list of widgets for the GPWv4 data processing tool.

        The `create_widgets_for_gpwv4` method creates several widgets that are used in the GPWv4 data processing tool. These widgets allow the user to select options such as data type, year
        *, scale, file directory, and processing options.

        The method initializes each widget with default values and settings. The `gpwv4_data_type` widget is a dropdown menu that displays available data types and their corresponding layers
        *. The `gpwv4_year` widget is also a dropdown menu that displays available years for the data.

        The `statistics_only_check` widget is a checkbox that allows the user to select whether only image statistics should be generated, represented as a dictionary. The `scale_input` widget
        * is a text box where the user can input the desired scale for the processing.

        The `add_image_to_map` and `create_sub_folder` widgets are checkboxes that give the user the option to add the processed image to the map and create a sub-folder, respectively. The `
        *filechooser` widget is a file chooser dialog that allows the user to select the directory for the processed files.

        The `gee_end_of_container_options` widget is an accordion container that holds the processing options checkboxes. It is configured with a two-by-two layout, with the `statistics_only
        *_check` widget in the top left corner, the `add_image_to_map` widget in the top right corner, and the `create_sub_folder` widget in the bottom right corner.

        The method creates a list named `widget_list` which contains all the widgets created. Finally, the method returns this list.

        :return: A list of widgets used in the GPWv4 data processing tool.
        """
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
                self.gpwv4_data_type,
                self.gpwv4_year,
                self.scale_input,
                self.filechooser,
                self.gee_end_of_container_options
            ]
            return self.widget_list

    def gather_parameters(self) -> Dict[str, Any]:
        """
        Gather the parameters for the method.

        :return: A dictionary containing the parameters.
        :rtype: Dict[str, Any]
        """
        # Ensure that you're accessing the correct attribute for the file chooser
        folder_output = self.filechooser.selected or self.filechooser.value

        # Return the parameters as a dictionary
        return {
            'population_source': 'GPWv4',
            'year': self.gpwv4_year.value,
            'datatype': self.gpwv4_data_type.value,
            'band': self.data_type_options[self.gpwv4_data_type.index]['band'],
            'statistics_only': self.statistics_only_check.value,
            'add_image_to_map': self.add_image_to_map.value,
            'create_sub_folder': self.create_sub_folder.value,
            'folder_output': folder_output,
        }

    def process_api(self, geometry: Any, distinct_values: Any, index: int, params=None, bbox=None, pbar=None) -> None:
        """
        Process the API for a given geometry.

        :param geometry: The geometry to process.
        :type geometry: Any

        :param distinct_values: The distinct values.
        :type distinct_values: Any

        :param index: The index.
        :type index: int

        :param params: The parameters.
        :type params: Any, optional

        :param bbox: The bounding box.
        :type bbox: Any, optional

        :return: None
        """

        try:

            pbar.update(1)
            pbar.set_postfix_str(f"Processing...")

            if params.get('create_sub_folder'):
                params['folder_output'] = self._create_sub_folder(params['folder_output'])

            params_file_path = os.path.join(params['folder_output'], 'parameters.json')

            with open(params_file_path, 'w') as f:
                json.dump(params, f)

            # Process the image
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
            print(f"An error occurred: {e}")

import ipywidgets as widgets
from ipywidgets import Layout
from typing import List, Dict, Any
import ee
from mcimageprocessing.programmatic.APIs.EarthEngine import EarthEngineManager
from mcimageprocessing.programmatic.APIs.WorldPop import WorldPop
from mcimageprocessing.programmatic.shared_functions.shared_utils import mosaic_images
import pkg_resources
import os
import rasterio
from rasterio.merge import merge

ee_auth_path = pkg_resources.resource_filename('mcimageprocessing', 'ee_auth_file.json')

ee_instance = EarthEngineManager(authentication_file=ee_auth_path)

def create_widgets_for_worldpop(self) -> List[widgets.Widget]:
    """
    :param self: the instance of the class calling this method
    :return: a list of widgets for creating WorldPop data visualizations

    This method creates and configures a series of widgets for selecting WorldPop data options and processing options.

    The following widgets are created:

    - `worldpop_data_source`: a `ToggleButtons` widget for selecting the data source, with options for 'WorldPop API' and 'Google Earth Engine'.

    - `worldpop_data_type`: a `Dropdown` widget for selecting the type of WorldPop data to visualize, with options for 'Residential Population' and 'Age and Sex Structures'.

    - `worldpop_year`: a `Dropdown` widget for selecting the year of the data to visualize, with options for the years from 2000 to 2020 in increments of 5.

    - `statistics_only_check`: a `Checkbox` widget for indicating whether only image statistics should be calculated, without generating a visualization.

    - `scale_input`: a `Text` widget for specifying the scale of the visualization.

    - `gee_end_of_container_options`: an `Accordion` widget containing three additional widgets, which are the `statistics_only_check`, `add_image_to_map`, and `create_sub_folder` widgets
    *. This accordion allows for collapsing and expanding the processing options.

    - `widget_list`: a list containing all the created widgets.

    Each created widget is then configured with appropriate values, descriptions, and layouts. Finally, the `widget_list` is returned.

    This method assumes that the class calling this method has attributes `out`, `add_image_to_map`, `create_sub_folder`, and `filechooser` already defined.
    """
    with self.out:

        self.worldpop_data_source = widgets.ToggleButtons(
            options=['WorldPop API', 'Google Earth Engine'],
            disabled=False,
            value='Google Earth Engine',
            tooltips=['Obtain data directly from WorldPop API (more dynamic and more options)', 'Google Earth Engine (less functionality and optiosn, but potentially faster'],
        )

        self.worldpop_data_type = widgets.Dropdown(
            options=[x for x in ['Residential Population', 'Age and Sex Structures', ]],
            value='Residential Population',
            description='Results:',
            disabled=False,
            layout=Layout()
        )

        self.worldpop_year = widgets.Dropdown(
            options=[str(x) for x in range(2000, 2021, 1)],
            value="2020",
            description='Year:',
            disabled=False,
            layout=Layout()
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

        self.gee_end_of_container_options = widgets.Accordion(
            [widgets.TwoByTwoLayout(
                top_left=self.statistics_only_check, top_right=self.add_image_to_map,
                bottom_right=self.create_sub_folder
            )])

        self.gee_end_of_container_options.set_title(0, 'Processing Options')

        widget_list = [
            self.worldpop_data_source,
            self.worldpop_data_type,
            self.worldpop_year,
            self.scale_input,
            self.filechooser,
            self.gee_end_of_container_options
        ]

        for widget in widget_list:
            widget.layout.width = '100%'

        return widget_list

def gather_worldpop_parameters(self) -> Dict[str, Any]:
    """
    :param self: The current object instance.
    :return: A dictionary containing the parameters for gathering world population data.

    The method gather_worldpop_parameters gathers the parameters required for gathering world population data. It returns a dictionary containing the following parameters:
    - api_source: The data source for the world population data.
    - year: The year for which the world population data is requested.
    - datatype: The data type for the world population data.
    - statistics_only: A flag indicating whether only statistics need to be calculated.
    - add_image_to_map: A flag indicating whether the image should be added to the map.
    - create_sub_folder: A flag indicating whether a sub-folder should be created for the output.
    - folder_output: The output folder path.

    Example usage:
    ```
    parameters = gather_worldpop_parameters(self)
    ```
    """

    return {
        'api_source': self.worldpop_data_source.value,
        'year': self.worldpop_year.value,
        'datatype': self.worldpop_data_type.value,
        'statistics_only': self.statistics_only_check.value,
        'add_image_to_map': self.add_image_to_map.value,
        'create_sub_folder': self.create_sub_folder.value,
        'folder_output': self.filechooser.value,
    }



def process_worldpop_data(self, geometry: Any, distinct_values: Any, index: int) -> None:
    """
    Method to process WorldPop API data for given parameters.

    :param self: The instance of the class.
    :param geometry: The geometry to process.
    :param distinct_values: The distinct values to filter.
    :param index: The index of the image.
    :return: None
    """
    with self.out:
        WorldPop.process_worldpop_api(self, geometry, distinct_values, index, worldpop_params=gather_worldpop_parameters(self))






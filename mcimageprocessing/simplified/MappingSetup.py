import os
import subprocess
import tempfile

import cdsapi
import ee
import geemap
import geopandas as gpd
import ipyfilechooser as fc
import ipywidgets as widgets
import localtileserver
import numpy as np
import pygrib
from ipywidgets import DatePicker
import datetime
import rasterio
from IPython.display import HTML
from ipywidgets import Output, Layout
import rioxarray
from shapely.geometry import shape
from osgeo import gdal, ogr
from shapely.geometry import Polygon, MultiPolygon
from ipywidgets import VBox
from osgeo import gdal
from rasterio.features import geometry_mask
from rasterio.mask import mask as riomask
from shapely.geometry import shape
from tqdm.notebook import tqdm
from ipywidgets import Text, FileUpload, VBox
from shapely.geometry import shape

from mcimageprocessing.simplified.GloFasAPI import CDSAPI
from mcimageprocessing.simplified.earthengine import EarthEngineManager

# Define custom CSS
custom_css = """
<style>
/* Target labels of ipywidgets */
.widget-label {
    width: auto !important;
}

"""

boundary_dropdown = {'Admin 0': 'admin_0', 'Admin 1': 'admin_1', 'Admin 2': 'admin_2',
                     'Watersheds Level 1': 'watersheds_1',
                     'Watersheds Level 2': 'watersheds_2', 'Watersheds Level 3': 'watersheds_3',
                     'Watersheds Level 4': 'watersheds_4', 'Watersheds Level 5': 'watersheds_5',
                     'Watersheds Level 6': 'watersheds_6', 'Watersheds Level 7': 'watersheds_7',
                     'Watersheds Level 8': 'watersheds_8', 'Watersheds Level 9': 'watersheds_9',
                     'Watersheds Level 10': 'watersheds_10', 'Watersheds Level 11': 'watersheds_11',
                     'Watersheds Level 12': 'watersheds_12'}

boundary_definition_type = {'User Definied': 'user_defined', 'Predefined Boundaries': 'predefined',
                            'User Uploaded Data': 'user_uploaded'}

# Render the CSS in the notebook
HTML(custom_css)

ee_instance = EarthEngineManager(authentication_file='../ee_auth_file.json')


def create_specific_widgets_for_glofas1(glofas_dict):
    """
    :param glofas_dict: A dictionary containing data specific to GloFas Data Type 1.
    :return: A list of widgets created for GloFas Data Type 1.

    This method creates widgets specific to GloFas Data Type 1. It takes a dictionary `glofas_dict` as a parameter and returns a list of widgets. The widgets created include a `system_version
    *` ToggleButtons widget, a `leadtime` IntSlider widget, a `year` Dropdown widget, a `month` Dropdown widget, and a `filechooser1` FileChooser widget. These widgets are customized based
    * on the data present in the `glofas_dict`.

    The `system_version` ToggleButtons widget allows the user to select the system version. The options for the ToggleButtons are obtained from the `glofas_dict['products']['cems-glofas
    *-seasonal']['system_version']` list.

    The `leadtime` IntSlider widget allows the user to select the lead time. The minimum and maximum values for the IntSlider are obtained from the `glofas_dict['products']['cems-glofas
    *-seasonal']['leadtime_hour']` list. The step is set to 24, and the default value is set to 24.

    The `year` Dropdown widget allows the user to select the year. The options for the Dropdown widget are obtained from the `glofas_dict['products']['cems-glofas-seasonal']['year']` list
    *. The default value is set to the minimum value in the list.

    The `month` Dropdown widget allows the user to select the month. The options for the Dropdown widget are obtained from the `glofas_dict['products']['cems-glofas-seasonal']['month']`
    * list. The default value is set to the maximum value in the list.

    The `system_version`, `year`, and `month` widgets have their layout width set to 'auto' for better display.

    The `filechooser1` FileChooser widget is created with the current working directory as the default directory, and only directories are shown.

    Finally, the method returns the list of all the created widgets.

    Example usage:

    glofas_dict = {
        'products': {
            'cems-glofas-seasonal': {
                'system_version': ['operational', 'experimental'],
                'leadtime_hour': [24, 48, 72],
                'year': [2020, 2021, 2022],
                'month': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
            }
        }
    }

    widgets_list = create_specific_widgets_for_glofas1(glofas_dict)
    """
    # Create widgets specific to GloFas Data Type 1
    # Example: A text input for a parameter and a dropdown to select an option

    system_version = widgets.ToggleButtons(
        options=[x.replace('_', '.').title() for x in
                 glofas_dict['products']['cems-glofas-seasonal']['system_version']],
        description='System Version:',
        disabled=False,
        value='Operational',
    )

    leadtime = widgets.IntSlider(
        value=24,
        min=min(glofas_dict['products']['cems-glofas-seasonal']['leadtime_hour']),
        max=max(glofas_dict['products']['cems-glofas-seasonal']['leadtime_hour']),
        step=24,
        description='Lead Time:',
        disabled=False,
        orientation='horizontal',
        readout=True,
        readout_format='d'
    )

    year = widgets.Dropdown(
        options=[x for x in glofas_dict['products']['cems-glofas-seasonal']['year']],
        value=min([x for x in glofas_dict['products']['cems-glofas-seasonal']['year']]),
        description='Year:',
        disabled=False,
    )

    month = widgets.Dropdown(
        options=[x for x in glofas_dict['products']['cems-glofas-seasonal']['month']],
        value=max([x for x in glofas_dict['products']['cems-glofas-seasonal']['month']]),
        description='Month:',
        disabled=False,
    )

    system_version.layout.width = 'auto'
    year.layout.width = 'auto'
    month.layout.width = 'auto'

    filechooser1 = fc.FileChooser(os.getcwd(), show_only_dirs=True)

    # Return a list of widgets
    return [system_version, leadtime, year, month, filechooser1]


def create_specific_widgets_for_glofas2(glofas_dict):
    """
    :param glofas_dict: A dictionary containing GloFas data
    :return: A list of specific widgets for GloFas Data Type 2

    This method creates specific widgets for GloFas Data Type 2. It takes in a dictionary `glofas_dict`, which should contain the necessary data for creating the widgets. The method creates
    * a ToggleButtons widget for selecting the system version, an IntSlider widget for selecting the lead time, and Dropdown widgets for selecting the year, month, and day. The method also
    * creates a FileChooser widget for selecting files. The created widgets are then added to a list and returned by the method.
    """
    # Create widgets specific to GloFas Data Type 2
    # Example: A slider for selecting a range and a button

    system_version = widgets.ToggleButtons(
        options=[x.replace('_', '.').title() for x in
                 glofas_dict['products']['cems-glofas-forecast']['system_version']],
        description='System Version:',
        disabled=False,
        value='Operational',
    )

    leadtime = widgets.IntSlider(
        value=24,
        min=min(glofas_dict['products']['cems-glofas-forecast']['leadtime_hour']),
        max=max(glofas_dict['products']['cems-glofas-forecast']['leadtime_hour']),
        step=24,
        description='Lead Time:',
        disabled=False,
        orientation='horizontal',
        readout=True,
        readout_format='d'
    )

    # Define the minimum and maximum dates based on the year and month data
    min_year = min(glofas_dict['products']['cems-glofas-forecast']['year'])
    max_year = max(glofas_dict['products']['cems-glofas-forecast']['year'])
    min_month = 1  # Assuming January is always included
    max_month = 12  # Assuming December is always included

    # Create the DatePicker widget with constraints
    date_picker = DatePicker(
        description='Select Date:',
        disabled=False,
        value=datetime.date(min_year, min_month, 1),  # Default value
        min=datetime.date(min_year, min_month, 1),   # Minimum value
        max=datetime.date(max_year, max_month, 31)   # Maximum value (assumes 31 days in max month)
    )

    # Adjusting the layout
    date_picker.layout.width = 'auto'

    system_version.layout.width = 'auto'

    filechooser2 = fc.FileChooser(os.getcwd(), show_only_dirs=True)

    # Return a list of widgets
    return [system_version, leadtime, date_picker, filechooser2]


def create_specific_widgets_for_glofas3(glofas_dict):
    """
    :param glofas_dict: A dictionary containing the data needed to create the specific widgets for GloFas Data Type 2.
    :return: A list of widgets that are specific to GloFas Data Type 2.

    This method takes in a dictionary and uses the data within the dictionary to create specific widgets for GloFas Data Type 2. The widgets created are a ToggleButtons widget for selecting
    * the system version, an IntSlider widget for selecting the lead time, and Dropdown widgets for selecting the year, month, and day. Additionally, a FileChooser widget is created for
    * choosing a file. These widgets are then returned as a list.
    """
    # Create widgets specific to GloFas Data Type 2
    # Example: A slider for selecting a range and a button

    system_version = widgets.ToggleButtons(
        options=[x.replace('_', '.').title() for x in
                 glofas_dict['products']['cems-glofas-reforecast']['system_version']],
        description='System Version:',
        disabled=False,
        value='Version.4.0',
    )

    leadtime = widgets.IntSlider(
        value=24,
        min=min(glofas_dict['products']['cems-glofas-reforecast']['leadtime_hour']),
        max=max(glofas_dict['products']['cems-glofas-reforecast']['leadtime_hour']),
        step=24,
        description='Lead Time:',
        disabled=False,
        orientation='horizontal',
        readout=True,
        readout_format='d'
    )

    # Define the minimum and maximum dates based on the year and month data
    min_year = min(glofas_dict['products']['cems-glofas-forecast']['year'])
    max_year = max(glofas_dict['products']['cems-glofas-forecast']['year'])
    min_month = 1  # Assuming January is always included
    max_month = 12  # Assuming December is always included

    # Create the DatePicker widget with constraints
    date_picker = DatePicker(
        description='Select Date:',
        disabled=False,
        value=datetime.date(min_year, min_month, 1),  # Default value
        min=datetime.date(min_year, min_month, 1),  # Minimum value
        max=datetime.date(max_year, max_month, 31)  # Maximum value (assumes 31 days in max month)
    )

    system_version.layout.width = 'auto'
    date_picker.layout.width = 'auto'

    filechooser3 = fc.FileChooser(os.getcwd(), show_only_dirs=True)

    # Return a list of widgets
    return [system_version, leadtime, date_picker, filechooser3]


NODATA_VALUE = -9999


class JupyterAPI(geemap.Map):
    """
    JupyterAPI Class
    ================

    This is a class that extends the geemap.Map class and provides additional functionality for interacting with the JupyterAPI.

    Constructor
    -----------

    ```
    def __init__(self):
        super().__init__()
    ```

    The constructor initializes the JupyterAPI object by calling the constructor of the superclass, geemap.Map.

    Attributes
    ----------

    - `states`: A variable representing the states.
    - `hydrosheds`: A variable representing the hydrosheds.
    - `added_layers`: A dictionary that stores the added layers.

    Methods
    -------

    No additional methods are defined in this class.

    """

    def __init__(self):
        super().__init__()

        # Create state and global variables
        self.added_layers = {}

        self.glofas_dict = {
            "products": {
                'cems-glofas-seasonal': {
                    "system_version": ['operational', 'version_3_1', 'version_2_2'],
                    'hydrological_model': ['lisflood'],
                    "variable": "river_discharge_in_the_last_24_hours",
                    "leadtime_hour": [
                        24, 48, 72, 96, 120, 144, 168, 192, 216, 240, 264, 288, 312, 336, 360, 384, 408,
                        432, 456, 480, 504, 528, 552, 576, 600, 624, 648, 672, 696, 720, 744, 768, 792,
                        816, 840, 864, 888, 912, 936, 960, 984, 1008, 1032, 1056, 1080, 1104, 1128, 1152,
                        1176, 1200, 1224, 1248, 1272, 1296, 1320, 1344, 1368, 1392, 1416, 1440, 1464, 1488,
                        1512, 1536, 1560, 1584, 1608, 1632, 1656, 1680, 1704, 1728, 1752, 1776, 1800, 1824,
                        1848, 1872, 1896, 1920, 1944, 1968, 1992, 2016, 2040, 2064, 2088, 2112, 2136, 2160,
                        2184, 2208, 2232, 2256, 2280, 2304, 2328, 2352, 2376, 2400, 2424, 2448, 2472, 2496,
                        2520, 2544, 2568, 2592, 2616, 2640, 2664, 2688, 2712, 2736, 2760, 2784, 2808, 2832,
                        2856, 2880, 2904, 2928, 2952, 2976, 3000, 3024, 3048, 3072, 3096, 3120, 3144, 3168,
                        3192, 3216, 3240, 3264, 3288, 3312, 3336, 3360, 3384, 3408, 3432, 3456, 3480, 3504,
                        3528, 3552, 3576, 3600, 3624, 3648, 3672, 3696, 3720, 3744, 3768, 3792, 3816, 3840,
                        3864, 3888, 3912, 3936, 3960, 3984, 4008, 4032, 4056, 4080, 4104, 4128, 4152, 4176,
                        4200, 4224, 4248, 4272, 4296, 4320, 4344, 4368, 4392, 4416, 4440, 4464, 4488, 4512,
                        4536, 4560, 4584, 4608, 4632, 4656, 4680, 4704, 4728, 4752, 4776, 4800, 4824, 4848,
                        4872, 4896, 4920, 4944, 4968, 4992, 5016, 5040, 5064, 5088, 5112, 5136, 5160],
                    "year": [2019, 2020, 2021, 2022, 2023],
                    "month": ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
                              "11", "12"],
                    # "day": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                    # "area": [10.95, -90.95, -30.95, -29.95],
                    "format": "grib"
                },
                'cems-glofas-forecast': {
                    "system_version": ['operational', 'version_3_1', 'version_2_1'],
                    'hydrological_model': ['lisflood', 'htessel_lisflood'],
                    'product_type': [
                        'control_forecast', 'ensemble_perturbed_forecasts',
                    ],
                    "variable": "river_discharge_in_the_last_24_hours",
                    "leadtime_hour": [
                        24, 48, 72, 96, 120, 144, 168, 192, 216, 240, 264, 288, 312, 336, 360, 384, 408,
                        432, 456, 480, 504, 528, 552, 576, 600, 624, 648, 672, 696, 720],
                    "year": [2020, 2021, 2022, 2023],
                    "month": ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
                              "11", "12"],
                    "day": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
                            13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
                            23, 24, 25, 26, 27, 28, 29, 30, 31],
                    # "area": [10.95, -90.95, -30.95, -29.95],
                    "format": "grib"
                },
                'cems-glofas-reforecast': {
                    "system_version": ['version_4_0', 'version_3_1', 'version_2_2'],
                    'hydrological_model': ['lisflood', 'htessel_lisflood'],
                    'product_type': [
                        'control_forecast', 'ensemble_perturbed_forecasts',
                    ],
                    "leadtime_hour": [
                        24, 48, 72, 96, 120, 144, 168, 192, 216, 240, 264, 288, 312, 336, 360, 384, 408,
                        432, 456, 480, 504, 528, 552, 576, 600, 624, 648, 672, 696, 720, 744, 768, 792,
                        816, 840, 864, 888, 912, 936, 960, 984, 1008, 1032, 1056, 1080, 1104],
                    "year": [1999, 2000, 20001, 2002, 2003, 2004, 2005, 2006, 2007,
                             2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015,
                             2016, 2017, 2018, 2019, 2020, 2021, 2022],
                    "month": ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
                              "11", "12"],
                    "day": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
                            13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
                            23, 24, 25, 26, 27, 28, 29, 30, 31],
                    # "area": [10.95, -90.95, -30.95, -29.95],
                    "format": "grib"
                }
            }
        }

        self.boundary_type = widgets.ToggleButtons(
            options=['Predefined Boundaries', 'User Defined', 'User Uploaded Data'],
            disabled=False,
            value='Predefined Boundaries',
            tooltips=['Predefined Boundaries (such as watersheds or administrative boundaries)', 'User Defined (draw a polygon on the map)', 'User Uploaded Data (upload a shapefile, kml, or kmz)'],
        )

        self.dropdown = self.create_dropdown(boundary_dropdown, 'Select Boundary:',
                                             'watersheds_4')
        self.dropdown.layout.width = 'auto'  # Adjust the width of the entire dropdown
        self.dropdown_api = self.create_dropdown({'GloFas': 'glofas'}, 'Select API:', 'glofas')
        self.dropdown_api.layout.width = 'auto'
        self.glofas_options = self.create_glofas_dropdown([x for x in self.glofas_dict['products'].keys()],
                                                          description='Select GloFas Product:',
                                                          default_value='cems-glofas-seasonal')
        self.add_to_map_check = widgets.Checkbox(value=True, description='Add Downloaded Image to Map')
        self.glofas_options.layout.width = 'auto'
        self.btn = widgets.Button(description='Process Drawn Features')
        self.btn.layout.width = '100%'
        # self.layer = self.states if self.dropdown.value == 'admin_0' else self.hydrosheds
        # self.column = 'ADM0_NAME' if self.dropdown.value == 'admin_0' else 'HYBAS_ID'
        self.btn.on_click(self.on_button_click)

        # self.add_widget(self.btn)
        self.widget_container = VBox(layout=Layout(resize='both', overflow='auto'))
        self.add_widget(self.widget_container)

        self.out = Output()
        # self.add_widget(self.out)

        # Define the instruction text and file upload widgets first
        self.instruction_text = widgets.Text(value='Draw one or more polygons on the map', disabled=True)
        self.upload_widget = widgets.FileUpload(accept='.shp,.geojson,.kml', multiple=False)

        # Set their display to 'none' initially
        self.instruction_text.layout.display = 'none'
        self.upload_widget.layout.display = 'none'

        # Create and initialize the specific widgets
        self.glofas1_widgets = create_specific_widgets_for_glofas1(self.glofas_dict) or []
        self.glofas2_widgets = create_specific_widgets_for_glofas2(self.glofas_dict) or []
        self.glofas3_widgets = create_specific_widgets_for_glofas3(self.glofas_dict) or []

        # Initially hide all specific widgets
        for widget in self.glofas1_widgets + self.glofas2_widgets + self.glofas3_widgets:
            widget.layout.visibility = 'hidden'

        # Initialize map with default dropdown value
        self.on_dropdown_change({'new': self.dropdown.value})

        self.on_glofas_option_change({'new': self.glofas_options.value})

        # Initially set up widgets based on the default boundary type
        self.on_boundary_type_change({'new': self.boundary_type.value})

        # Set up listeners for boundary type changes
        self.boundary_type.observe(self.on_boundary_type_change, names='value')

        self.boundary_type.observe(self.on_any_change, names='value')
        self.dropdown.observe(self.on_any_change, names='value')
        self.glofas_options.observe(self.on_any_change, names='value')


        self.update_final_output()

    def create_dropdown(self, dropdown_options, description, default_value):
        """
        Create a dropdown widget with specified options, description, and default value.

        :param dropdown_options: A list of options for the dropdown.
        :param description: A string specifying the description of the dropdown.
        :param default_value: The default value selected in the dropdown.
        :return: The created dropdown widget.
        """
        dropdown = widgets.Dropdown(
            options=dropdown_options,
            value=default_value,  # the default value
            description=description,
            disabled=False,
        )

        dropdown.observe(self.on_dropdown_change, names='value')
        return dropdown

    def toggle_minimize(self, b):
        # This function is called when the minimize button is clicked.
        if self.main_content.layout.display == 'none':
            # If the content is hidden, show it and change button text to 'Minimize'
            self.main_content.layout.display = 'block'
            self.minimize_button.description = 'Minimize'
        else:
            # If the content is shown, hide it and change button text to 'Maximize'
            self.main_content.layout.display = 'none'
            self.minimize_button.description = 'Maximize'

    def geometry_to_geodataframe(self):
        # Convert the geometry dictionary to a shape
        geometry_shape = shape(self.geometry)

        # Create a GeoDataFrame from the shape
        return gpd.GeoDataFrame([{'geometry': geometry_shape}], crs='EPSG:4326')

    def inspect_grib_file(self, file_path):
        try:
            # Open the GRIB file
            grib_file = pygrib.open(file_path)

            # Count the number of messages
            num_messages = grib_file.messages

            for i in range(1, num_messages + 1):
                # Read each message
                message = grib_file.message(i)


                try:
                    # Attempt to read the data array
                    data = message.values
                except Exception as e:
                    # Handle cases where data can't be read
                    print(f"  - An error occurred when reading data: {e}")

                print("")

        except Exception as e:
            print(f"An overall error occurred: {e}")

    # Replace 'your_grib_file.grib' with the path to your actual GRIB file

    def gather_current_selections(self):
        """
        Gather current selections from all relevant widgets.
        :return: dict of current selections
        """
        selections = {
            'boundary_type': self.boundary_type.value,
            'selected_boundary': self.dropdown.value,
            'glofas_product': self.glofas_options.value,
            'uploaded_file': self.upload_widget.value,  # This will include the uploaded file data
            # ... include other relevant widget values ...
        }
        return selections

    def update_final_output(self):
        """
        Update the final output container based on current selections.
        """
        selections = self.gather_current_selections()

        # Handle special cases or default behavior
        if 'special_case' in selections['boundary_type']:
            # Do something specific for this special case
            pass

        # Dynamically update the final container based on the selections
        # This might include showing/hiding widgets, displaying messages, etc.
        # ...

    def on_any_change(self, change):
        """
        Generic change handler to update the final output whenever any widget changes.
        """
        self.update_final_output()

    def convert_to_cog(self, input_path, output_path):
        # Convert a GeoTIFF to a COG using gdal_translate
        cmd = [
            'gdal_translate',
            '-of', 'COG',
            '-co', 'COMPRESS=DEFLATE',
            '-ot', 'Float64',  # Adjust the compression as needed
            input_path,
            output_path
        ]
        subprocess.run(cmd, check=True)

    def convert_grib_to_geotiff(self, grib_path, geotiff_path):
        # Convert a GRIB file to a standard GeoTIFF using gdal_translate
        cmd = [
            'gdal_translate',
            '-of', 'GTiff',
            '-ot', 'Float64',
            grib_path,
            geotiff_path
        ]
        subprocess.run(cmd, check=True)

    def get_edge_values(self, raster_array, transform, shape, geometry):
        """
        Get the most common value at the edge of the raster, outside the geometry.
        """
        # Create a mask for the geometry
        mask = geometry_mask([geometry], transform=transform, invert=True, out_shape=shape)

        # Find the edge values of the raster
        edge_values = np.unique(raster_array[mask])
        return edge_values

    def get_nodata_value(self, src):
        # Try to get no-data value from source metadata
        if src.nodata is not None:
            return src.nodata

        # If no-data value isn't set, infer it from data statistics or common conventions
        data_sample = src.read(1, masked=True)  # Read first band as a sample
        common_nodata_values = [-9999, -999, 0]  # Add common no-data values for your data

        for nodata_candidate in common_nodata_values:
            if np.isclose(data_sample, nodata_candidate).mean() > 0.5:  # More than 50% matches
                return nodata_candidate

        return -9999  # or 0, or whatever makes sense for your data

    def create_mask(self, out_image, nodata_value):
        if nodata_value is None:
            # If no no-data value is known, you might need a custom strategy
            # Perhaps infer the no-data value based on data distribution
            nodata_value = self.get_nodata_value(out_image)  # This would be a custom function you'd need to implement

        if isinstance(nodata_value, float):
            # Use a tolerance for floating-point comparisons
            tolerance = 1e-6  # Adjust based on your data's precision
            return np.isclose(out_image, nodata_value, atol=tolerance)
        else:
            # Direct comparison for integer types
            return out_image == nodata_value

    def clip_raster(self, grib_path, geometry, temp_dir=None):
        # First, inspect the GRIB file to understand its contents
        self.inspect_grib_file(grib_path)

        with rioxarray.open_rasterio(
            grib_path,
            masked=True) as xds:

            raster = xds.isel(band=0)

            try:
                polygon = shape(geometry['geometries'][1])
            except KeyError:
                polygon = shape(geometry)

            gdf = gpd.GeoDataFrame([1], geometry=[polygon], crs="EPSG:4326")
            gdf = gdf.to_crs(raster.rio.crs)  # Reproject the geometry to match the raster's CRS

            clipped_raster = raster.rio.clip(gdf.geometry, drop=True, invert=False)

            try:
                clipped_raster.rio.write_nodata(-9999, inplace=True)
            except ValueError:
                pass

            grib_path = grib_path.replace('.grib', '.tif')

            try:
                clipped_raster.rio.to_raster(grib_path, nodata=-9999)
            except ValueError as e:
                if "overwriting existing key _FillValue" in str(e):
                    if '_FillValue' in clipped_raster.encoding:
                        del clipped_raster.encoding['_FillValue']
                    clipped_raster.rio.to_raster(grib_path, nodata=-9999)
                else:
                    raise  # re-raise the exception if it's not the one we're expecting

            return grib_path


    def create_glofas_dropdown(self, dropdown_options, description, default_value):
        """
        Create a dropdown widget for GLOFAS.

        :param dropdown_options: a list of options for the dropdown
        :type dropdown_options: list
        :param description: a description for the dropdown
        :type description: str
        :param default_value: the default value for the dropdown
        :type default_value: any
        :return: a Dropdown widget
        :rtype: ipywidgets.Dropdown
        """
        dropdown = widgets.Dropdown(
            options=dropdown_options,
            value=default_value,  # the default value
            description=description,
            disabled=False,
        )

        dropdown.observe(self.on_glofas_option_change, names='value')
        return dropdown

    def on_dropdown_change(self, change):
        """
        Handle the change event of a dropdown menu.

        :param change: A dictionary containing the change event information.
        :return: None
        """
        new_value = change['new']

        # Remove any existing layers
        for name, layer in self.added_layers.items():
            if layer in self.layers:
                self.remove_layer(layer)
        self.added_layers = {}

        new_value = new_value.split('_')

        # Add the appropriate layer based on the selection
        if new_value[0] == 'admin':
            # Add the states layer for 'admin_0'.
            states = ee.FeatureCollection(f"FAO/GAUL_SIMPLIFIED_500m/2015/level{new_value[1]}")
            states_layer = geemap.ee_tile_layer(states, {}, 'US States')
            self.layer = states
            self.column = f'ADM{new_value[1]}_NAME'
            self.add_layer(states_layer)
            self.added_layers[f'admin_{1}'] = states_layer
        elif new_value[0] == 'watersheds':
            hydrosheds = ee.FeatureCollection(f"WWF/HydroSHEDS/v1/Basins/hybas_{new_value[1]}")
            # Add the HydroSHEDS layer for 'watersheds_4'.
            hydrosheds_layer = geemap.ee_tile_layer(hydrosheds, {}, 'HydroSHEDS Basins')
            self.layer = hydrosheds
            self.column = 'HYBAS_ID'
            self.add_layer(hydrosheds_layer)
            self.added_layers[f'watersheds_{new_value[1]}'] = hydrosheds_layer

    def on_boundary_type_change(self, change):
        """
        Handle changes to the boundary type selection.

        :param change: A dictionary representing the change in value of the boundary_type widget.
        """
        boundary_value = change['new']
        self.update_boundary_options(boundary_value)

        # Reset the widget container to include only the widgets relevant to the selected boundary type
        self.widget_container.children = [self.boundary_type, self.dropdown, self.dropdown_api, self.glofas_options]

        # Update the visibility and options of other widgets based on the selected boundary type
        # ... (add any additional logic specific to your application)

    def update_boundary_options(self, boundary_value):
        # Define how the boundary type affects the boundary dropdown options
        if boundary_value == 'Predefined Boundaries':
            # Predefined boundaries selected
            self.dropdown.layout.display = 'block'  # Show the dropdown
            self.instruction_text.layout.display = 'none'  # Hide the instruction text
            self.upload_widget.layout.display = 'none'  # Hide the upload widget
        elif boundary_value == 'User Defined':
            # User defined selected
            self.dropdown.layout.display = 'none'  # Hide the dropdown
            self.instruction_text.layout.display = 'block'  # Show the instruction text
            self.upload_widget.layout.display = 'none'  # Hide the upload widget
            print("User Defined selected - text should be visible now.")
        elif boundary_value == 'User Uploaded Data':
            # User uploaded data selected
            self.dropdown.layout.display = 'none'  # Hide the dropdown
            self.instruction_text.layout.display = 'none'  # Hide the instruction text
            self.upload_widget.layout.display = 'block'  # Show the upload widget
        else:
            # Default case, hide everything
            self.dropdown.layout.display = 'none'
            self.instruction_text.layout.display = 'none'
            self.upload_widget.layout.display = 'none'

        # Update the widget container to include the custom widgets along with the defaults
        self.widget_container.children = [self.boundary_type, self.dropdown, self.dropdown_api, self.glofas_options,
                                          self.instruction_text, self.upload_widget]

    def on_glofas_option_change(self, change):
        """
        Handle the change event of the "glofas_option" dropdown widget.
        """
        new_value = change['new']
        self.update_glofas_container(new_value)

    def update_glofas_container(self, glofas_value):
        """
        Update the visibility and children of the GloFAS widget container based on the selected GloFAS product.

        :param glofas_value: The selected value of the GloFAS product dropdown.
        """
        # Reset children and visibility for all widgets
        self.widget_container.children = [self.boundary_type, self.dropdown, self.dropdown_api, self.glofas_options]
        for widget in self.glofas1_widgets + self.glofas2_widgets + self.glofas3_widgets:
            widget.layout.visibility = 'hidden'

        # Update widget container and visibility based on the GloFAS product selection
        glofas_widgets_mapping = {
            'cems-glofas-seasonal': self.glofas1_widgets,
            'cems-glofas-forecast': self.glofas2_widgets,
            'cems-glofas-reforecast': self.glofas3_widgets,
        }

        if glofas_value in glofas_widgets_mapping:
            specific_widgets = glofas_widgets_mapping[glofas_value]
            self.widget_container.children += tuple(specific_widgets)
            for widget in specific_widgets:
                widget.layout.visibility = 'visible'

        # Always add the 'add_to_map_check' and 'btn' widgets
        self.widget_container.children += (self.add_to_map_check, self.btn,)


    def add_clipped_raster_to_map(self, raster_path, vis_params=None):
        if vis_params is None:
            vis_params = {}
        try:
            client = localtileserver.TileClient(raster_path)
            tile_layer = localtileserver.get_leaflet_tile_layer(client, **vis_params)
            self.add_layer(tile_layer)
            self.fit_bounds(client.bounds)
        except ValueError as e:
            print(f"ValueError: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

    def process_drawn_features(self, drawn_features):
        """
        Process the drawn features to get distinct values of a column.

        :param drawn_features: List of drawn features.
        :type drawn_features: list of ee.Feature or ee.Geometry
        :return: List of distinct values of the column.
        :rtype: list
        """
        all_distinct_values = []
        for feature in drawn_features:

            if isinstance(feature, ee.Feature) or isinstance(feature, ee.Geometry):
                drawn_geom = feature.geometry()
                bounding = drawn_geom.bounds()
                filtered_layer = self.layer.filterBounds(bounding)
                distinct_values = filtered_layer.aggregate_array(self.column).distinct().getInfo()
                all_distinct_values.extend(distinct_values)
        return list(set(all_distinct_values))

    def ensure_multipolygon(self, geometry):
        """Ensure the geometry is a MultiPolygon."""
        if geometry.type().getInfo() == 'Polygon':
            return ee.Geometry.MultiPolygon([geometry.coordinates()])
        else:
            return geometry

    def download_feature_geometry(self, distinct_values):
        if not distinct_values:
            print("No distinct values provided.")
            return

        feature_type_prefix = self.dropdown.value.split('_')[0]

        if feature_type_prefix not in ['watersheds', 'admin']:
            print("Invalid feature type.")
            return

        all_geometries = []

        for value in distinct_values:
            feature = self.layer.filter(ee.Filter.eq(self.column, value)).first()
            if not feature:
                print("No feature found for value:", value)
                continue

            geometry = feature.geometry()
            if not geometry:
                print("No geometry for value:", value)
                continue

            geometry_type = geometry.type().getInfo()

            if geometry_type == 'Polygon':
                all_geometries.append(geometry.coordinates().getInfo())
            elif geometry_type == 'MultiPolygon':
                for poly in geometry.coordinates().getInfo():
                    all_geometries.append(poly)
            elif geometry_type == 'GeometryCollection':
                self.process_geometry_collection(geometry, all_geometries)

        if all_geometries:
            try:
                dissolved_geometry = ee.Geometry.MultiPolygon(all_geometries).dissolve()
                feature = ee.Feature(dissolved_geometry)
            except ee.EEException as e:
                print("Error creating dissolved geometry:", e)
        else:
            print("No valid geometries to dissolve.")

        if feature:
            self.geometry = feature.geometry().getInfo()

    def process_geometry_collection(self, geometry_collection, all_geometries):
        geometries = geometry_collection.geometries().getInfo()
        for geom in geometries:
            geom_type = geom['type']
            if geom_type == 'Polygon':
                all_geometries.append(geom['coordinates'])
            elif geom_type == 'MultiPolygon':
                for poly in geom['coordinates']:
                    all_geometries.append(poly)

    def get_raster_min_max(self, raster_path):
        dataset = gdal.Open(raster_path)
        band = dataset.GetRasterBand(1)  # Assumes the raster has only one band
        min_val = band.GetMinimum()
        max_val = band.GetMaximum()

        band_data = band.ReadAsArray()

        # Check if 9999 is in the data
        if 9999 in band_data:
            # Mask the data to ignore values of 9999 or higher
            masked_data = np.ma.masked_where(band_data >= 9999, band_data)

            # Find the maximum value in the masked data
            next_highest_val = masked_data.max()

            # Set max_val to the next highest value
            max_val = next_highest_val

        # If the minimum and maximum values are not natively provided by the raster band
        if min_val is None or max_val is None:
            min_val, max_val = band.ComputeRasterMinMax(True)

        dataset = None  # Close the dataset
        return min_val, max_val

    def draw_and_process(self):
        """
        This method `draw_and_process` is responsible for drawing features on the map and processing them based on certain conditions.

        :return: None
        """
        with self.out:
            if self.draw_features:
                for feature in self.draw_features:
                    distinct_values = self.process_drawn_features([feature])
                    self.download_feature_geometry(distinct_values)
                    bbox = self.get_bounding_box(distinct_values)

                    if self.glofas_options.value == 'cems-glofas-seasonal':
                        # Retrieve values from widgets
                        system_version = self.glofas1_widgets[0].value.replace('.',
                                                                               '_').lower()  # Assuming this is the system_version widget
                        leadtime_hour = str(self.glofas1_widgets[1].value)  # Assuming this is the leadtime widget
                        year = str(self.glofas1_widgets[2].value)  # Assuming this is the year widget
                        month = self.glofas1_widgets[3].value  # Assuming this is the month widget
                        day = "01"
                        folder_location = self.glofas1_widgets[4].selected  # Assuming this is the file chooser widget
                    elif self.glofas_options.value == 'cems-glofas-forecast':
                        system_version = self.glofas2_widgets[0].value.replace('.',
                                                                               '_').lower()
                        leadtime_hour = str(self.glofas2_widgets[1].value)
                        date = self.glofas2_widgets[2].value
                        year = str(date.year)
                        month = int(date.month)
                        day = str(date.day)
                        folder_location = self.glofas2_widgets[3].selected
                    elif self.glofas_options.value == 'cems-glofas-reforecast':
                        system_version = self.glofas3_widgets[0].value.replace('.',
                                                                               '_').lower()
                        leadtime_hour = str(self.glofas3_widgets[1].value)
                        date = self.glofas2_widgets[2].value
                        year = str(date.year)
                        month = int(date.month)
                        day = str(date.day)
                        folder_location = self.glofas3_widgets[3].selected

                    print(f"add_to_map value is {self.add_to_map_check.value}")
                    # Create an instance of the CDSAPI class
                    cds_api = CDSAPI()

                    # Prepare the request parameters
                    request_parameters = {
                        'variable': 'river_discharge_in_the_last_24_hours',
                        'format': 'grib',
                        'system_version': system_version,
                        'hydrological_model': 'lisflood',
                        'product_type': 'ensemble_perturbed_forecasts',
                        'year': year,
                        'month': month,
                        # Omit 'day' to use the default value or provide a specific day
                        'day': day,
                        'leadtime_hour': leadtime_hour,
                        'area': [bbox['maxy'][0], bbox['minx'][0], bbox['miny'][0], bbox['maxx'][0]],
                        'folder_location': folder_location,
                    }

                    # Call the download_data method
                    file_name = f"{self.dropdown.value}_{'_'.join(str(value) for value in distinct_values)}_{year}_{month}_{request_parameters.get('day', '01')}.grib"
                    file_path = cds_api.download_data(self.glofas_options.value, request_parameters, file_name)

                    print(f"Downloaded {year} file to {file_path}")

                    min_val, max_val = self.get_raster_min_max(file_path)

                    if min_val == -9999:
                        min_val = 0


                    vis_params = {
                        'min': min_val,
                        'max': max_val,
                        'palette': 'viridis',  # or any other valid colormap name
                        'nodata': -9999  # Replace with your actual nodata value
                    }

                    clipped_raster_path = self.clip_raster(file_path, self.geometry)
                    if self.add_to_map_check.value:
                        self.add_clipped_raster_to_map(clipped_raster_path, vis_params=vis_params)
                    print("Distinct values from all drawn features:", distinct_values)
            else:
                print("No features have been drawn on the map.")

    def on_button_click(self, b):
        """
        :param b: The button object that triggered the event
        :return: None
        """
        with self.out:
            self.out.clear_output()  # Clear the previous output
            self.draw_and_process()

            # Assuming `distinct_values` is available after drawing and processing

    def get_bounding_box(self, distinct_values):
        """
        :param distinct_values: a list of distinct values used to filter the data
        :return: a GeoDataFrame representing the bounding box of the filtered data

        This method takes a list of distinct values and generates a bounding box for the filtered data based on the selected dropdown value. If the dropdown value is 'admin_0', it filters
        * the data using the distinct values and returns the bounding box as a GeoDataFrame. If the dropdown value is 'watersheds_4', it filters the data using the distinct values and returns
        * the bounding box as a GeoDataFrame.
        """
        if self.dropdown.value.split('_')[0] == 'admin':
            bounds = self.layer.filter(ee.Filter.inList(self.column, distinct_values)).geometry().bounds().getInfo()
            gdf = gpd.GeoDataFrame([{'geometry': shape(bounds)}], crs='EPSG:4326')
            return gdf.geometry.bounds
        elif self.dropdown.value.split('_')[0] == 'watersheds':
            bounds = self.layer.filter(
                ee.Filter.inList(self.column, distinct_values)).geometry().bounds().getInfo()
            gdf = gpd.GeoDataFrame([{'geometry': shape(bounds)}], crs='EPSG:4326')
            return gdf.geometry.bounds

    def get_map_and_output(self):
        """
        Returns the map object and the output value.

        :return: A tuple containing the map object and the output value.
        """
        return self, self.out

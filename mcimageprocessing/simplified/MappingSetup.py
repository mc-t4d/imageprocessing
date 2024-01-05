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
import json
import datetime
import rasterio
from IPython.display import HTML
from ipywidgets import Output, Layout
from ipyleaflet import GeoJSON
import rioxarray
from shapely.geometry import shape
from osgeo import gdal, ogr
from shapely.geometry import Polygon, MultiPolygon
from ipywidgets import VBox
from osgeo import gdal
import geojson
from rasterio.features import geometry_mask
from rasterio.mask import mask as riomask
from shapely.geometry import shape
from tqdm.notebook import tqdm as notebook_tqdm
from ipywidgets import Text, FileUpload, VBox, jslink, Stack, HBox
from shapely.geometry import shape
import warnings
from IPython.display import display

from mcimageprocessing.simplified.GloFasAPI import GlofasAPI
from mcimageprocessing.simplified.earthengine import EarthEngineManager

# Define custom CSS
custom_css = """
<style>
/* Target labels of ipywidgets */
.widget-label {
    width: auto !important;
}
</style>

"""

boundary_dropdown = {'Admin 0': 'admin_0', 'Admin 1': 'admin_1', 'Admin 2': 'admin_2',
                     'Watersheds Level 1': 'watersheds_1',
                     'Watersheds Level 2': 'watersheds_2', 'Watersheds Level 3': 'watersheds_3',
                     'Watersheds Level 4': 'watersheds_4', 'Watersheds Level 5': 'watersheds_5',
                     'Watersheds Level 6': 'watersheds_6', 'Watersheds Level 7': 'watersheds_7',
                     'Watersheds Level 8': 'watersheds_8', 'Watersheds Level 9': 'watersheds_9',
                     'Watersheds Level 10': 'watersheds_10', 'Watersheds Level 11': 'watersheds_11',
                     'Watersheds Level 12': 'watersheds_12'}

boundary_definition_type = {'User Defined': 'user_defined', 'Predefined Boundaries': 'predefined',
                            'User Uploaded Data': 'user_uploaded'}

# Render the CSS in the notebook
HTML(custom_css)

ee_instance = EarthEngineManager(authentication_file='../ee_auth_file.json')

warnings.filterwarnings('ignore', category=UserWarning, message="This was only*")

NODATA_VALUE = -9999

class OutputWidgetTqdm(notebook_tqdm):
    """
    OutputWidgetTqdm class

    This class is a subclass of the notebook_tqdm class. It provides a custom implementation for displaying progress using the tqdm library in Jupyter Notebook.

    Attributes:
    - output_widget: An output widget used to display the progress bar.

    Methods:
    - __init__(*args, **kwargs): Initializes the OutputWidgetTqdm instance. Accepts custom arguments and also the output_widget argument to extract the output widget.
    - display(*args, **kwargs): Overrides the display method of the superclass. Redirects the display to the output widget specified in the constructor.

    Note: This class requires the tqdm and ipywidgets libraries to be installed.

    Example usage:

    output_widget = OutputWidget()  # Instantiate the custom output widget
    widget_tqdm = OutputWidgetTqdm(output_widget=output_widget)  # Create an instance of OutputWidgetTqdm
    widget_tqdm.display()  # Display the progress bar in the output widget

    """
    def __init__(self, *args, **kwargs):
        # You can add custom arguments here if needed, or pass through to superclass
        self.output_widget = kwargs.pop('output_widget', None)  # Extract the output widget
        super().__init__(*args, **kwargs)

    def display(self, *args, **kwargs):
        # Override the display method to redirect to the output widget
        if self.output_widget:
            self.output_widget.clear_output(wait=True)
            with self.output_widget:
                display(self.container)

class JupyterAPI(geemap.Map):
    """

    """

    def __init__(self):
        super().__init__()

        self.setup_global_variables()

        self.create_widgets()

        self.setup_event_listeners()

        self.initialize_ui_state()

        # self.update_final_output()

    def setup_global_variables(self):
        self.added_layers = {}
        self.glofas_dict = {
            "products": {
                'cems-glofas-seasonal': {
                    "system_version": ['operational', 'version_3_1', 'version_2_2'],
                    'hydrological_model': ['lisflood'],
                    "variable": "river_discharge_in_the_last_24_hours",
                    "leadtime_hour": list(range(24, 5161, 24)),
                    "year": list(range(2019, datetime.date.today().year + 1)),
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
                    "leadtime_hour": list(range(24, 721, 24)),
                    "year": list(range(2020, datetime.date.today().year + 1)),
                    "month": ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
                              "11", "12"],
                    "day": list(range(24, 32)),
                    # "area": [10.95, -90.95, -30.95, -29.95],
                    "format": "grib"
                },
                'cems-glofas-reforecast': {
                    "system_version": ['version_4_0', 'version_3_1', 'version_2_2'],
                    'hydrological_model': ['lisflood', 'htessel_lisflood'],
                    'product_type': [
                        'control_forecast', 'ensemble_perturbed_forecasts',
                    ],
                    "leadtime_hour": list(range(24, 1105, 24)),
                    "year": list(range(1999, datetime.date.today().year + 1)),
                    "month": ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
                              "11", "12"],
                    "day": list(range(24, 32)),
                    # "area": [10.95, -90.95, -30.95, -29.95],
                    "format": "grib"
                }
            }
        }

    def create_widgets(self):
        self.boundary_type = widgets.ToggleButtons(
            options=['Predefined Boundaries', 'User Defined', 'User Uploaded Data', 'Parameter File'],
            disabled=False,
            value='Predefined Boundaries',
            tooltips=['Predefined Boundaries (such as watersheds or administrative boundaries)',
                      'User Defined (draw a polygon on the map)',
                      'User Uploaded Data (upload a shapefile, kml, or kmz)',
                      'Parameter file generated during a past run or setup.'],
        )

        self.dropdown = self.create_dropdown(boundary_dropdown, 'Select Boundary:', 'watersheds_4')
        self.dropdown.layout.width = 'auto'

        self.dropdown_api = self.create_dropdown({'GloFas': 'glofas', 'Google Earth Engine': 'gee'}, 'Select API:',
                                                 'glofas')
        self.dropdown_api.layout.width = 'auto'

        self.add_to_map_check = widgets.Checkbox(value=True, description='Add Downloaded Image to Map')
        self.btn = widgets.Button(description='Process')
        self.btn.layout.width = '100%'

        self.instruction_text = widgets.Text(value='Draw one or more polygons on the map', disabled=True)
        self.instruction_text.style.text_color = '#c8102e'
        self.upload_widget = widgets.FileUpload(accept='.geojson', multiple=False)
        self.upload_widget.layout.width= '100%'
        self.upload_widget.style.button_color = '#c8102e'
        self.upload_widget.style.text_color = 'white'

        self.no_data_helper_checklist = widgets.Checkbox(value=True, description='No-Data Helper Function',
                                                         tooltip="Due to GloFas API framework, some versions and/or "
                                                                 "models aren't available for certain dates. If enabled,"
                                                                 "This will allow the program to automatically alter the version date and "
                                                                 "hydrological model to find a matching dataset.")

        self.boundary_stack = VBox([self.dropdown, self.instruction_text, self.upload_widget])

        self.api_choice_stack = VBox([])

        self.end_of_vbox_items = VBox([self.add_to_map_check, self.no_data_helper_checklist])

        self.predefined_upload_widget = widgets.FileUpload(
            accept='.json',
            multiple=False  # True to accept multiple files upload else False
        )

        self.predefined_upload_widget.layout.display='none'
        self.predefined_upload_widget.layout.width = '100%'
        self.predefined_upload_widget.style.button_color = '#c8102e'
        self.predefined_upload_widget.style.text_color = 'white'

        self.glofas_stack = VBox([])

        self.widget_container = VBox(
            [self.boundary_type, self.boundary_stack, self.dropdown_api, self.api_choice_stack, self.end_of_vbox_items, self.predefined_upload_widget, self.btn],
            layout=Layout(resize='both', overflow='auto'))

        self.userlayers = {}

        self.out = Output()

    def setup_event_listeners(self):
        """
        Set up event listeners for the given parameters.

        :return: None
        """
        self.boundary_type.observe(self.on_boundary_type_change, names='value')
        self.dropdown.observe(self.on_dropdown_change, names='value')
        self.dropdown_api.observe(self.on_api_change, names='value')
        self.btn.on_click(self.on_button_click)
        self.upload_widget.observe(self.on_file_upload, names='value')

    def initialize_ui_state(self):
        """
        Initializes the UI state by setting initial values and visibility for various elements.

        :return: None
        """
        self.on_dropdown_change({'new': self.dropdown.value})
        self.on_api_change({'new': self.dropdown_api.value})
        self.on_boundary_type_change({'new': self.boundary_type.value})
        self.on_file_upload({'new': self.upload_widget.value})

        # Set initial visibility for instruction text and upload widget
        self.instruction_text.layout.display = 'none'

        self.upload_widget.layout.display = 'none'

        self.on_api_change({'new': self.dropdown_api.value})

        # Add the main widget container to the display
        self.add_widget(self.widget_container)

    def create_dropdown(self, dropdown_options, description, default_value):
        """
        Create a dropdown widget with the given options, description, and default value.

        :param dropdown_options: a list of options for the dropdown
        :type dropdown_options: list
        :param description: the description text for the dropdown
        :type description: str
        :param default_value: the default value for the dropdown
        :type default_value: any
        :return: the created dropdown widget
        :rtype: widgets.Dropdown
        """
        dropdown = widgets.Dropdown(
            options=dropdown_options,
            value=default_value,  # the default value
            description=description,
            disabled=False,
        )

        dropdown.observe(self.on_dropdown_change, names='value')
        return dropdown

    def on_gee_search_button_clicked(self, b):
        """
        Perform a search for Earth Engine data when the search button is clicked.

        :param b: The button widget.
        :type b: Button
        :return: None
        :rtype: None
        """
        # Here you define what happens when the button is clicked.
        # For now, it's just a print statement.
        assets = geemap.search_ee_data(self.gee_layer_search_widget.value)
        with self.out:
            print([x['id'] for x in assets])
            print([x['title'] for x in assets])
            print("Button clicked: Searching for", self.gee_layer_search_widget.value)
        self.gee_layer_search_results_dropdown.options = {x['title']: x['id'] for x in assets}

    def on_gee_layer_selected(self, b):
        """
        Event handler for when a Google Earth Engine layer is selected.

        :param b: The input value triggered by the event.
        :type b: Any
        :return: None
        """
        selected_layer = self.gee_layer_search_results_dropdown.value
        self.ee_dates_min_max = ee_instance.get_image_collection_dates(selected_layer, min_max_only=True)
        print(datetime.datetime.strptime(self.ee_dates_min_max[0], '%Y-%m-%d'))

    def on_single_or_range_dates_change(self, change):
        """
        :param change: The change event object
        :return: None
        """
        if self.single_or_range_dates.value == 'Single Date':
            self.gee_single_date_selector = widgets.Dropdown(
                options=[],
                value=None,
                description='Results:',
                disabled=False,
                layout=Layout(width='auto')
            )

            self.gee_single_date_selector.options = ee_instance.get_image_collection_dates(
                self.gee_layer_search_results_dropdown.value, min_max_only=False)
            self.gee_date_selection.children = [self.gee_single_date_selector]
        elif self.single_or_range_dates.value == 'Date Range':
            start_date = datetime.datetime.strptime(self.ee_dates_min_max[0], '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(self.ee_dates_min_max[1], '%Y-%m-%d').date()

            self.gee_date_picker_start = DatePicker(
                description='Select Start Date:',
                disabled=False,
                min=start_date,
                max=end_date,
                value=start_date
            )
            self.gee_date_picker_end = DatePicker(
                description='Select End Date:',
                disabled=False,
                min=start_date,
                max=end_date,
                value=end_date
            )

            self.gee_multi_date_aggregation_periods = widgets.ToggleButtons(
                options=['Monthly', 'Yearly'],
                disabled=False,
                value='Monthly',
                tooltips=['Monthly', 'Yearly'],
            )

            aggregation_values = {
                'mode': lambda ic: ic.mode(),
                'median': lambda ic: ic.median(),
                'mean': lambda ic: ic.mean(),
                'max': lambda ic: ic.max(),
                'min': lambda ic: ic.min(),
                'sum': lambda ic: ic.reduce(ee.Reducer.sum()),
                'first': lambda ic: ic.sort('system:time_start', False).first(),
                'last': lambda ic: ic.sort('system:time_start', False).last()
            }

            self.gee_multi_date_aggregation_method = widgets.Dropdown(
                options={x.title(): x for x in aggregation_values.keys()},
                value='mean',
                description='Aggregation Method:',
                disabled=False,
            )
            self.gee_date_selection.children = [HBox([self.gee_date_picker_start, self.gee_date_picker_end]),
                                                self.gee_multi_date_aggregation_periods,
                                                self.gee_multi_date_aggregation_method]

    def create_widgets_gee(self):
        """
        Create and return a list of widgets for the Google Earth Engine layer search functionality.

        :return: A list of widgets for the Google Earth Engine layer search functionality.
        """
        self.gee_layer_search_widget = widgets.Text(
            value='',
            placeholder='Search for a layer',
            description='Search:',
            disabled=False,
            layout=Layout(width='auto')
        )

        self.gee_layer_search_widget.layout.width = 'auto'

        self.search_button = widgets.Button(
            description='Search',
            disabled=False,
            button_style='',  # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Click to search',
            icon='search'  # Icons names are available at https://fontawesome.com/icons
        )

        self.search_button.on_click(self.on_gee_search_button_clicked)

        self.search_box = HBox([self.gee_layer_search_widget, self.search_button])

        self.gee_layer_search_results_dropdown = widgets.Dropdown(
            options=[],
            value=None,
            description='Results:',
            disabled=False,
            layout=Layout(width='auto')
        )

        self.select_layer_gee = widgets.Button(
            description='Select',
            disabled=False,
            button_style='',  # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Select Layer',
            icon='crosshairs'  # Icons names are available at https://fontawesome.com/icons
        )

        self.select_layer_gee.on_click(self.on_gee_layer_selected)

        self.layer_select_box = HBox([self.gee_layer_search_results_dropdown, self.select_layer_gee])

        self.single_or_range_dates = widgets.ToggleButtons(
            options=['Single Date', 'Date Range'],
            disabled=False,
            value='Date Range',
            tooltips=['Single Date', 'Date Range'],
        )

        self.single_or_range_dates.observe(self.on_single_or_range_dates_change, names='value')
        self.select_layer_gee.on_click(self.on_single_or_range_dates_change)

        self.gee_date_selection = widgets.VBox([])

        return [self.search_box, self.layer_select_box, self.single_or_range_dates, self.gee_date_selection]

    # def update_gee_date_selection_box(self, change):

    def toggle_minimize(self, b):
        """
        Toggles the visibility of the main content and changes the button text between 'Minimize' and 'Maximize'.

        :param b: A boolean value indicating whether to minimize or maximize the content.
        :type b: bool
        :return: None
        """
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
        """
        Converts the geometry dictionary to a GeoDataFrame.

        :return: A GeoDataFrame containing the converted geometry.
        """
        # Convert the geometry dictionary to a shape
        geometry_shape = shape(self.geometry)

        # Create a GeoDataFrame from the shape
        return gpd.GeoDataFrame([{'geometry': geometry_shape}], crs='EPSG:4326')

    def inspect_grib_file(self, file_path):
        """
        Inspects a GRIB file at the given file path and prints information about each message in the file.

        :param file_path: The path to the GRIB file.
        :return: None
        """
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

    def calculate_bounds(self, geojson_content):
        """
        Calculate the bounds of a given GeoJSON content.

        :param geojson_content: The GeoJSON content to calculate the bounds from.
        :return: A list of two lists representing the minimum and maximum latitude and longitude coordinates respectively.
        """
        # Initialize min and max coordinates
        min_lat, min_lon, max_lat, max_lon = 90, 180, -90, -180

        # Function to update the bounds based on a coordinate pair
        def update_bounds(lat, lon):
            nonlocal min_lat, min_lon, max_lat, max_lon
            if lat < min_lat: min_lat = lat
            if lon < min_lon: min_lon = lon
            if lat > max_lat: max_lat = lat
            if lon > max_lon: max_lon = lon

        # Iterate through the coordinates and update the bounds
        for feature in geojson_content['features']:
            coords = feature['geometry']['coordinates']
            geom_type = feature['geometry']['type']

            # Update bounds based on the geometry type
            if geom_type == 'Point':
                update_bounds(*coords)
            elif geom_type in ['LineString', 'MultiPoint']:
                for coord in coords:
                    update_bounds(*coord)
            elif geom_type in ['Polygon', 'MultiLineString']:
                for part in coords:
                    for coord in part:
                        update_bounds(*coord)
            elif geom_type == 'MultiPolygon':
                for polygon in coords:
                    for part in polygon:
                        for coord in part:
                            update_bounds(*coord)

        return [[min_lat, min_lon], [max_lat, max_lon]]

    def on_file_upload(self, change):
        """
        Method to process uploaded files and create a GeoJSON layer.

        :param change: A dictionary containing the uploaded file info.
        :return: None
        """
        uploaded_files = change['new']  # Get the list of uploaded file info

        try:
            # Process each uploaded file
            for file_info in uploaded_files:
                filename = file_info['name']

                # This is the file content as a memoryview object
                content = file_info['content']

                # Convert the memoryview object to bytes then decode to string
                content_str = bytes(content).decode("utf-8")

                # Load the string as GeoJSON
                geojson_content = geojson.loads(content_str)

                # Create a GeoJSON layer

                style = {
                    "color": "black",  # Line color
                    "fillColor": "black",  # Fill color
                    "weight": 1,  # Border width
                    "fillOpacity": 0.5  # Fill opacity
                }

                geojson_layer = GeoJSON(data=geojson_content, style=style)

                # Add the GeoJSON to the map
                try:
                    self.add_layer(geojson_layer,
                                   name='User Uploaded Data',
                                   vis_params={'color': 'black'})
                    # bounds = self.calculate_bounds(geojson_content)
                    # self.fit_bounds(bounds)
                    self.userlayers['User Uploaded Data'] = geojson_layer
                except Exception as e:
                    with self.out:
                        print(f"Error adding layer: {e}")

        except Exception as e:
            with self.out:
                print(f"Error processing files: {e}")

    def convert_to_cog(self, input_path, output_path):
        """
        Convert a GeoTIFF to a COG (Cloud-Optimized GeoTIFF) using gdal_translate.

        :param input_path: Full path to the input GeoTIFF file.
        :type input_path: str
        :param output_path: Full path to the output COG file.
        :type output_path: str
        :return: None
        """
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
        """
        Converts a GRIB file to a standard GeoTIFF using gdal_translate.

        :param grib_path: The path to the input GRIB file.
        :param geotiff_path: The path to save the output GeoTIFF file.
        :return: None

        This method uses the `gdal_translate` command to convert the input GRIB file to a GeoTIFF file. The output GeoTIFF file will be saved at the specified `geotiff_path` location.

        **Note:** The `gdal_translate` command is executed using the `subprocess.run()` method with the `check=True` parameter to ensure the conversion process completes without any errors.

        Example usage:

        ```python
        # Instantiate the object
        converter = Converter()

        # Convert a GRIB file to GeoTIFF
        converter.convert_grib_to_geotiff('/path/to/input.grib', '/path/to/output.tif')
        ```
        """
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
        Get the edge values of a raster within a specified geometry.

        :param raster_array: The array representing the raster.
        :param transform: The affine transformation matrix to transform coordinates from pixel space to world space.
        :param shape: The shape of the output raster array.
        :param geometry: The geometry within which to find the edge values.
        :return: An array containing the unique edge values found within the specified geometry.

        """
        # Create a mask for the geometry
        mask = geometry_mask([geometry], transform=transform, invert=True, out_shape=shape)

        # Find the edge values of the raster
        edge_values = np.unique(raster_array[mask])
        return edge_values

    def get_nodata_value(self, src):
        """
        Method: get_nodata_value

        This method is used to retrieve the no-data value from a given data source.

        :param src: The data source from which to retrieve the no-data value.
        :return: The no-data value of the source, if available. Otherwise, it infers the no-data value from data statistics or common conventions.

        """
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
        """
        Method to create a mask based on a given output image and no-data value.

        :param out_image: The output image to create the mask from.
        :param nodata_value: The no-data value used to determine the mask.
        :return: The mask created based on the output image and no-data value.

        """
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

    def clip_raster(self, grib_path, geometry):
        """
        :param grib_path: The file path of the GRIB file to be clipped.
        :return: The file path of the clipped TIFF file.

        The `clip_raster` method takes in a GRIB file and clips it based on a provided geometry. It returns the file path of the resulting clipped TIFF file.

        The method begins by inspecting the GRIB file to understand its contents. It then converts the provided geometry into a Shapely geometry object.

        Using the `open_rasterio` function from the `rioxarray` library, the GRIB file is opened as a raster dataset with masking enabled. The first band of the raster is selected.

        The method then tries to extract a polygon geometry from the provided geometry. If the polygon is not found, the method falls back to using the original geometry.

        A GeoDataFrame is created with the polygon geometry, assigning it the CRS (Coordinate Reference System) EPSG:4326. The geometry is then reprojected to match the CRS of the raster dataset
        *.

        The raster dataset is clipped using the clipped geometry. The `drop` parameter is set to True to remove any portions of the raster that fall outside the geometry. The `invert` parameter
        * is set to False to keep the portions of the raster that intersect with the geometry.

        The clipped raster is then checked for a potential _FillValue issue, where overwriting may cause errors. If such an issue is caught, the _FillValue encoding is deleted to resolve the
        * issue. The clipped raster is then written to the provided output file path, replacing the .grib extension with .tif. The nodata value is set to -9999.

        If the clipping and writing process encounters any other ValueError, it is re-raised as an exception. Otherwise, the file path of the resulting clipped TIFF file is returned.
        """
        with self.out:
            # First, inspect the GRIB file to understand its contents
            self.inspect_grib_file(grib_path)

            geometry = self.ee_geometry_to_shapely(geometry)

            with rioxarray.open_rasterio(
                grib_path,
                masked=True) as xds:

                raster = xds.isel(band=0)

                try:
                    polygon = shape(geometry['geometries'][1])
                except KeyError:
                    polygon = shape(geometry)

                except TypeError:
                    polygon = geometry

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
        Creates a dropdown widget for the GLOFAS application.

        :param dropdown_options: A list of options for the dropdown.
        :param description: The description label for the dropdown.
        :param default_value: The default value for the dropdown.
        :return: A Dropdown widget for the GLOFAS application.
        """
        dropdown = widgets.Dropdown(
            options=dropdown_options,
            value=default_value,  # the default value
            description=description,
            disabled=False,
        )

        # dropdown.observe(self.on_glofas_option_change, names='value')
        return dropdown

    def on_dropdown_change(self, change):
        """
        :param change: A dictionary containing information about the dropdown change event.
        :return: None

        This method is called when the value of a dropdown menu is changed. It takes in the `change` parameter, which is a dictionary that contains information about the change event.

        The method first extracts the new value from the `change` dictionary.

        It then proceeds to remove any existing layers by iterating over the `added_layers` dictionary and removing each layer from the `layers` list. It also resets the `added_layers` dictionary
        *.

        Next, it splits the new value into two parts using the underscore (_) as the delimiter.

        If the first part of the new value is 'admin', it adds the states layer based on the second part of the new value. It creates a feature collection based on the specified GAUL dataset
        * and level, and then creates an EE tile layer using the feature collection. The layer variable is updated with the new feature collection, and the column variable is set to the corresponding
        * administrative name column. The new layer is added to the map using the `add_layer` method, and the layer is also stored in the `added_layers` dictionary.

        If the first part of the new value is 'watersheds', it adds the HydroSHEDS layer based on the second part of the new value. It creates a feature collection based on the specified Hydro
        *SHEDS dataset, and then creates an EE tile layer using the feature collection. The layer variable is updated with the new feature collection, and the column variable is set to the Hydro
        *SHEDS ID column. The new layer is added to the map using the `add_layer` method, and the layer is also stored in the `added_layers` dictionary.
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

    def on_api_change(self, change):
        """
        :param change: dictionary containing the change information
            - 'new': the new value of the change
        :return: None

        This method is called when there is a change in the API selection. The `change` parameter is a dictionary that contains information about the change. The 'new' key in the dictionary
        * represents the new value of the change.

        Depending on the new value of the change, this method performs different actions. If the new value is 'glofas', it creates a dropdown menu for GloFas products and sets up the necessary
        * event listener. It then updates the API choice stack to display the GloFas options.

        If the new value is 'gee', it creates widgets for Google Earth Engine (GEE) options. It then updates the API choice stack to display the GEE options.

        If the new value is neither 'glofas' nor 'gee', no action is taken.

        Note that the commented code in the method is not executed.

        Examples:
            # Example usage
            change = {'new': 'glofas'}
            on_api_change(self, change)
        """
        new_value = change['new']

        # Remove any existing layers
        # for name, layer in self.added_layers.items():
        #     if layer in self.layers:
        #         self.remove_layer(layer)
        # self.added_layers = {}

        # Add the appropriate layer based on the selection
        if new_value == 'glofas':
            self.glofas_options = self.create_glofas_dropdown([x for x in self.glofas_dict['products'].keys()],
                                                              description='Select GloFas Product:',
                                                              default_value='cems-glofas-seasonal')
            self.glofas_options.layout.width = 'auto'
            self.glofas_options.observe(self.on_glofas_option_change, names='value')
            self.on_glofas_option_change({'new': self.glofas_options.value})
            self.api_choice_stack.children = [self.glofas_options, self.glofas_stack]

        elif new_value == 'gee':
            self.gee_options = self.create_widgets_gee()
            # self.gee_options.layout.width = 'auto'
            self.api_choice_stack.children = tuple(self.gee_options)
        else:
            pass

    def on_boundary_type_change(self, change):
        """
        :param change: A dictionary representing the change that occurred in the boundary type. The dictionary should have a key 'new' which points to the new boundary value.
        :return: None

        This method updates the boundary options based on the new boundary value provided in the change dictionary. The updated options are passed to the method 'update_boundary_options'.
        """
        boundary_value = change['new']
        self.update_boundary_options(boundary_value)

    def update_boundary_options(self, boundary_value):
        """
        Method Name: update_boundary_options

        Description: This method updates the boundary options based on the selected boundary value.

        Parameters:
        - boundary_value (str): The selected boundary value.

        Returns:
        None

        """
        # Define how the boundary type affects the boundary dropdown options
        if boundary_value == 'Predefined Boundaries':
            self.on_dropdown_change({'new': self.dropdown.value})
            # Predefined boundaries selected
            self.dropdown.layout.display = 'block'  # Show the dropdown
            self.instruction_text.layout.display = 'none'  # Hide the instruction text
            self.upload_widget.layout.display = 'none'  # Hide the upload widget
            self.predefined_upload_widget.layout.display = 'none'
            self.end_of_vbox_items.layout.display = 'block'
            self.boundary_stack.layout.display = 'block'
            self.dropdown_api.layout.display = 'block'
            self.api_choice_stack.layout.display = 'block'

        elif boundary_value in ['User Defined', 'User Uploaded Data']:
            # Either User defined or User uploaded data selected

            # Remove EE Leaflet Tile Layers with Google Earth Engine attribution
            for layer in self.layers:
                if hasattr(layer, 'attribution') and 'Google Earth Engine' in layer.attribution:
                    self.remove_layer(layer)

            if boundary_value == 'User Defined':
                # User defined selected
                self.dropdown.layout.display = 'none'  # Hide the dropdown
                self.instruction_text.layout.display = 'block'  # Show the instruction text
                self.upload_widget.layout.display = 'none'  # Hide the upload widget
                self.predefined_upload_widget.layout.display = 'none'
                self.end_of_vbox_items.layout.display = 'block'
                self.boundary_stack.layout.display = 'block'
                self.dropdown_api.layout.display = 'block'
                self.api_choice_stack.layout.display = 'block'

            elif boundary_value == 'User Uploaded Data':
                # User uploaded data selected
                self.dropdown.layout.display = 'none'  # Hide the dropdown
                self.instruction_text.layout.display = 'none'  # Hide the instruction text
                self.upload_widget.layout.display = 'block'  # Show the upload widget
                self.predefined_upload_widget.layout.display = 'none'
                self.end_of_vbox_items.layout.display = 'block'
                self.boundary_stack.layout.display = 'block'
                self.dropdown_api.layout.display = 'block'
                self.api_choice_stack.layout.display = 'block'

        elif boundary_value == 'Parameter File':
            self.predefined_upload_widget.layout.display='block'
            self.end_of_vbox_items.layout.display='none'
            self.boundary_stack.layout.display='none'
            self.dropdown_api.layout.display='none'
            self.api_choice_stack.layout.display='none'

        else:
            # Default case, hide everything
            self.dropdown.layout.display = 'none'
            self.instruction_text.layout.display = 'none'
            self.upload_widget.layout.display = 'none'

    def on_single_or_date_range_change(self, change, glofas_option: str):
        """
        Handles the change event when the option for single date or date range is changed.

        :param change: A dictionary containing information about the change event.
        :param glofas_option: The selected Glofas option.
        :return: None

        """

        single_or_date_range_value = change['new']

        # Define the minimum and maximum dates based on the year and month data
        min_year = min(self.glofas_dict['products'][glofas_option]['year'])
        max_year = max(self.glofas_dict['products'][glofas_option]['year'])
        min_month = 1  # Assuming January is always included
        max_month = 12  # Assuming December is always included

        print(min_year, max_year)

        if single_or_date_range_value == 'Single Date':
            # Create the DatePicker widget with constraints
            self.date_picker = DatePicker(
                description='Select Date:',
                disabled=False,
                value=datetime.date(min_year, min_month, 1),  # Default value
                min=datetime.date(min_year, min_month, 1),  # Minimum value
                max=datetime.date(max_year, max_month, 31)  # Maximum value (assumes 31 days in max month)
            )
            self.glofas_date_vbox.children = [self.date_picker]

        else:
            # Create the DatePicker widgets with constraints
            self.date_picker = HBox([
                DatePicker(
                description='Select Start Date:',
                disabled=False,
                value=datetime.date(min_year, min_month, 1),  # Default value
                min=datetime.date(min_year, min_month, 1),  # Minimum value
                max=datetime.date(max_year, max_month, 31)  # Maximum value (assumes 31 days in max month)
            ),

            DatePicker(
                description='Select End Date:',
                disabled=False,
                value=datetime.date(max_year, max_month, 31),  # Default value
                min=datetime.date(min_year, min_month, 1),  # Minimum value
                max=datetime.date(max_year, max_month, 31)  # Maximum value (assumes 31 days in max month)
            )])

            self.glofas_date_vbox.children = [self.date_picker]

    def create_widgets_for_glofas(self, glofas_option: str):
        """
        Create widgets specific to GloFas Data Type 2

        :param glofas_option: The selected GloFas option
        :return: A list of widgets specific to the selected GloFas option
        """
        # Create widgets specific to GloFas Data Type 2
        # Example: A slider for selecting a range and a button

        with self.out:
            self.system_version = widgets.ToggleButtons(
                options=[x.replace('_', '.').title() for x in
                         self.glofas_dict['products'][glofas_option]['system_version']],
                description='System Version:',
                disabled=False,
                value=self.glofas_dict['products'][glofas_option]['system_version'][0].replace('_', '.').title(),
            )

            self.hydrological_model = widgets.ToggleButtons(
                options=[x for x in
                         self.glofas_dict['products'][glofas_option]['hydrological_model']],
                description='Hydrological Model:',
                disabled=False,
                value=self.glofas_dict['products'][glofas_option]['hydrological_model'][0],
            )

            try:
                self.product_type = widgets.ToggleButtons(
                    options=[x.replace('_', '.').title() for x in
                             self.glofas_dict['products'][glofas_option]['product_type']],
                    description='Product Type:',
                    disabled=False,
                    value=self.glofas_dict['products'][glofas_option]['product_type'][0].replace('_', '.').title(),
                )
            except KeyError:
                pass

            self.leadtime = widgets.IntSlider(
                value=24,
                min=min(self.glofas_dict['products'][glofas_option]['leadtime_hour']),
                max=max(self.glofas_dict['products'][glofas_option]['leadtime_hour']),
                step=24,
                description='Lead Time:',
                disabled=False,
                orientation='horizontal',
                readout=True,
                readout_format='d'
            )

            self.leadtime.layout.width = 'auto'

            self.single_or_date_range = widgets.ToggleButtons(
                options=['Single Date', 'Date Range'],
                disabled=False,
                value='Single Date',
                tooltips=['Single Date', 'Date Range'],
            )


            self.glofas_date_vbox = VBox([])
            self.on_single_or_date_range_change({'new': self.single_or_date_range.value}, glofas_option=glofas_option)

            # Define the minimum and maximum dates based on the year and month data
            # min_year = min(self.glofas_dict['products'][glofas_option]['year'])
            # max_year = max(self.glofas_dict['products'][glofas_option]['year'])
            # min_month = 1  # Assuming January is always included
            # max_month = 12  # Assuming December is always included
            #
            # # Create the DatePicker widget with constraints
            # self.date_picker = DatePicker(
            #     description='Select Date:',
            #     disabled=False,
            #     value=datetime.date(min_year, min_month, 1),  # Default value
            #     min=datetime.date(min_year, min_month, 1),  # Minimum value
            #     max=datetime.date(max_year, max_month, 31)  # Maximum value (assumes 31 days in max month)
            # )

            self.single_or_date_range.observe(
                lambda change: self.on_single_or_date_range_change(change, glofas_option=glofas_option),
                names='value'
            )

            self.system_version.layout.width = 'auto'
            # self.date_picker.layout.width = 'auto'

            self.filechooser_glofas = fc.FileChooser(os.getcwd(), show_only_dirs=True)

            # Return a list of widgets
            if glofas_option == 'cems-glofas-seasonal':
                return [self.system_version, self.hydrological_model, self.leadtime, self.single_or_date_range,
                        self.glofas_date_vbox, self.filechooser_glofas]
            else:
                return [self.system_version, self.hydrological_model, self.product_type, self.leadtime,
                        self.single_or_date_range,
                        self.glofas_date_vbox, self.filechooser_glofas]

    def on_glofas_option_change(self, change):
        """
        Updates the glofas_stack based on the new value received in the change parameter.

        :param change:  A dictionary containing the new value of the glofas option.
        :return: None
        """
        new_value = change['new']
        self.glofas_stack.children = ()  # Clear the glofas_stack
        self.update_glofas_container(new_value)

    def update_glofas_container(self, glofas_value):
        """
        Update the GloFAS container based on the selected GloFAS product.

        :param glofas_value: The selected GloFAS product.
        :return: None
        """

        # Mapping of GloFAS product names to their respective widget lists
        # glofas_widgets_mapping = {
        #     'cems-glofas-seasonal': self.glofas1_widgets,
        #     'cems-glofas-forecast': self.glofas2_widgets,
        #     'cems-glofas-reforecast': self.glofas3_widgets,
        # }
        #
        # # Hide all widgets from previous selection
        # for widget_list in glofas_widgets_mapping.values():
        #     for widget in widget_list:
        #         # widget.layout.display = 'none'
        #         widget.layout.visibility = 'hidden'
        #
        # if glofas_value in glofas_widgets_mapping:
        #     # Get the specific widgets for the selected GloFAS product
        #     specific_widgets = glofas_widgets_mapping[glofas_value]
        #
        #     # Set the visibility of the specific widgets
        #     for widget in specific_widgets:
        #         # widget.layout.display = 'block'
        #         widget.layout.visibility = 'visible'

        specific_widgets = self.create_widgets_for_glofas(glofas_value)

        # Replace the children of the glofas_stack with the specific widgets
        self.glofas_stack.children = tuple(specific_widgets)

        # else:
        #     # If the selected GloFAS product is not recognized, clear the glofas_stack
        #     self.glofas_stack.children = ()

    def add_clipped_raster_to_map(self, raster_path, vis_params=None):
        """
        Adds a clipped raster to the map.

        :param raster_path: A string specifying the path to the raster file.
        :param vis_params: Optional dictionary specifying the visualization parameters for the raster. Default is an empty dictionary.
        :return: None

        Example usage:

            add_clipped_raster_to_map('/path/to/raster.tif', vis_params={'min': 0, 'max': 255})

        This method creates a `localtileserver.TileClient` object using the given raster path. It then uses the `localtileserver.get_leaflet_tile_layer` method to obtain the Leaflet tile layer
        * for the raster, applying the visualization parameters if provided. The resulting tile layer is added to the map using the `add_layer` method. Finally, the map adjusts its bounds to
        * fit the bounds of the raster using the `fit_bounds` method.

        If a ValueError occurs during the process, it will be caught and printed as an error message. Any other exceptions will also be caught and printed.

        Note: This method assumes that the necessary dependencies (`localtileserver`) are installed and importable.
        """
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
        Process the drawn features.

        :param drawn_features: A list of drawn features.
        :type drawn_features: list[ee.Feature or ee.Geometry]
        :return: A list of distinct values from the filtered layer.
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
        """
            Ensures that the given geometry is a MultiPolygon. If the geometry is a Polygon, it converts it into a MultiPolygon.

            :param geometry: The geometry object to ensure as a MultiPolygon.
            :return: The input geometry as a MultiPolygon or the original geometry if it is already a MultiPolygon.

            **Example Usage**

            .. code-block:: python

                geometry = ee.Geometry.Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
                ensure_multipolygon(geometry)

            **Example Output**

            .. code-block:: python

                <ee.Geometry.MultiPolygon object at 0x7f672fc35160>
        """
        if geometry.type().getInfo() == 'Polygon':
            return ee.Geometry.MultiPolygon([geometry.coordinates()])
        else:
            return geometry

    def download_feature_geometry(self, distinct_values):
        """
        Downloads the geometry for each distinct value from the specified feature layer and stores it in self.geometry.

        :param distinct_values: A list of distinct values for filtering the feature layer.
        :return: None
        """
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
            return self.geometry

    def process_geometry_collection(self, geometry_collection, all_geometries):
        """
        Processes a geometry collection and appends the coordinates of polygons and multipolygons to a list.

        :param geometry_collection: A geometry collection object.
        :param all_geometries: A list to store the coordinates of polygons and multipolygons.
        :return: None
        """
        geometries = geometry_collection.geometries().getInfo()
        for geom in geometries:
            geom_type = geom['type']
            if geom_type == 'Polygon':
                all_geometries.append(geom['coordinates'])
            elif geom_type == 'MultiPolygon':
                for poly in geom['coordinates']:
                    all_geometries.append(poly)

    def get_raster_min_max(self, raster_path):
        """
        :param raster_path: The file path to the raster file.
        :return: A tuple containing the minimum and maximum values of the raster.
        """
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

    def ee_geometry_to_shapely(self, geometry):
        """
        Convert an Earth Engine Geometry, Feature, or GeoJSON to a Shapely Geometry object.

        :param geometry: An Earth Engine Geometry, Feature, or GeoJSON dictionary.
        :return: A Shapely Geometry object.

        """
        # Check if the geometry is an Earth Engine Geometry or Feature
        if isinstance(geometry, ee.Geometry) or isinstance(geometry, ee.Feature):
            # Convert Earth Engine object to GeoJSON
            geo_json = geometry.getInfo()
            if 'geometry' in geo_json:  # If it's a Feature, extract the geometry part
                geo_json = geo_json['geometry']
            # Convert GeoJSON to a Shapely Geometry
            return shape(geo_json)
        elif isinstance(geometry, dict):  # Directly convert from GeoJSON if it's a dictionary
            return shape(geometry)
        else:
            # If it's neither, assume it's already a Shapely Geometry or compatible
            return geometry

    def determine_geometries_to_process(self):
        """
        Determine the geometries to process based on the boundary type and user inputs.

        :return: A list of tuples representing the geometries to process. Each tuple contains a feature and distinct values.
        """
        geometries = []
        if self.boundary_type.value in ['Predefined Boundaries', 'User Defined']:
            for feature in self.draw_features:
                if self.boundary_type.value == 'Predefined Boundaries':
                    distinct_values = self.process_drawn_features([feature])
                    feature = self.download_feature_geometry(distinct_values)
                else:  # User Defined
                    distinct_values = None
                    # Assuming feature is the geometry itself in this case
                geometries.append((feature, distinct_values))
        elif self.boundary_type.value == 'User Uploaded Data' and 'User Uploaded Data' in self.userlayers:
            feature = self.userlayers['User Uploaded Data'].data
            geometries.append((feature, None))
        return geometries

    def process_and_clip_raster(self, file_path, geometry):
        """
        Process and clip a raster file.

        :param file_path: The file path of the raster file to be processed and clipped.
        :return: None
        """
        with self.out:
            min_val, max_val = self.get_raster_min_max(file_path)
            if min_val == -9999:
                min_val = 0

            vis_params = {
                'min': min_val,
                'max': max_val,
                'palette': 'viridis',
                'nodata': -9999
            }

            clipped_raster_path = self.clip_raster(file_path, geometry)
            if self.add_to_map_check.value:
                self.add_clipped_raster_to_map(clipped_raster_path, vis_params=vis_params)

    def download_glofas_data(self, bbox, glofas_params, index, distinct_values=None):
        """
        :param bbox: The bounding box of the area to download Glofas data for.
        :param glofas_params: The parameters for downloading Glofas data.
        :param index: The index of the Glofas data.
        :param distinct_values: The distinct values for the Glofas data (optional).
        :return: The file path of the downloaded Glofas data.

        """
        glofas_api = GlofasAPI()
        request_parameters = {
            'variable': 'river_discharge_in_the_last_24_hours',
            'format': 'grib',
            'system_version': glofas_params.get('system_version'),
            'hydrological_model': glofas_params.get('hydrological_model'),
            'product_type': glofas_params.get('product_type', 'ensemble_perturbed_forecasts'),
            'year': glofas_params.get('year'),
            'month': glofas_params.get('month'),
            # Omit 'day' to use the default value or provide a specific day
            'day': glofas_params.get('day', '01'),
            'leadtime_hour': glofas_params.get('leadtime_hour'),
            'area': [bbox['maxy'][0], bbox['minx'][0], bbox['miny'][0], bbox['maxx'][0]],
            'folder_location': glofas_params.get('folder_location'),
        }

        # Construct file name based on the parameters
        file_name = f"{self.dropdown.value}_{'userdefined' if distinct_values is None else '_'.join(str(value) for value in distinct_values)}_{index}_{glofas_params.get('year')}_{glofas_params.get('month')}_{request_parameters.get('day', '01')}.grib"

        # Download data and return the file path
        return glofas_api.download_data(self.glofas_options.value, request_parameters, file_name)

    def get_glofas_parameters(self, glofas_product):
        """
        :param glofas_product: The type of GloFAS product.
        :return: A dictionary containing the parameters required for the given GloFAS product.

        The `get_glofas_parameters` method takes in the `glofas_product` parameter to determine the type of GloFAS product. It then collects the necessary parameters based on the type of product
        * and returns them in a dictionary.

        Note: The returned dictionary may vary depending on the value of `glofas_product`.

        Example usages:
        ```
        parameters = get_glofas_parameters('cems-glofas-seasonal')
        # Returns:
        # {
        #     'system_version': system_version,
        #     'hydrological_model': hydrological_model,
        #     'leadtime_hour': leadtime_hour,
        #     'year': year,
        #     'month': month,
        #     'day': day,
        #    """
        date_type = self.single_or_date_range.value
        system_version = self.system_version.value.replace('.', '_').lower()
        hydrological_model = self.hydrological_model.value
        try:
            product_type = self.product_type.value.replace('.', '_').lower()
        except AttributeError:
            product_type = None
        leadtime_hour = self.leadtime.value
        if date_type == 'Single Date':
            date = self.date_picker.value
            year = str(date.year)
            month = int(date.month)
            day = str(date.day)
        elif date_type == 'Date Range':
            start_date = self.date_picker.children[0].value
            end_date = self.date_picker.children[1].value
        folder_location = self.filechooser_glofas.selected

        if glofas_product == 'cems-glofas-seasonal':

            return {
                'system_version': system_version,
                'hydrological_model': hydrological_model,
                'leadtime_hour': leadtime_hour,
                'year': year,
                'month': month,
                'day': day,
                'folder_location': folder_location,
            }
        elif glofas_product == 'cems-glofas-forecast':

            return {
                'system_version': system_version,
                'hydrological_model': hydrological_model,
                'product_type': product_type,
                'leadtime_hour': leadtime_hour,
                'year': year,
                'month': month,
                'day': day,
                'folder_location': folder_location,
            }
        elif glofas_product == 'cems-glofas-reforecast':
            return {
                'system_version': system_version,
                'hydrological_model': hydrological_model,
                'product_type': product_type,
                'leadtime_hour': leadtime_hour,
                'year': year,
                'month': month,
                'day': day,
                'folder_location': folder_location,
            }
        else:
            print("Invalid GloFAS product.")
            return None

    def draw_and_process(self):
        """
        Perform the draw and process operation.

        :return: None
        """
        with self.out:
            if self.boundary_type.value == 'Parameter File':
                # Handle parameter file case
                pass

            else:
                # Determine geometries to process based on boundary type
                geometries = self.determine_geometries_to_process()

                # with OutputWidgetTqdm(total=len(geometries), output_widget=self.out) as pbar:
                for index, (geometry, distinct_values) in enumerate(geometries):
                    bbox = self.get_bounding_box(distinct_values=distinct_values, feature=geometry)
                    glofas_params = self.get_glofas_parameters(self.glofas_options.value)

                    file_path = self.download_glofas_data(bbox, glofas_params, index, distinct_values)
                    self.process_and_clip_raster(file_path, geometry)

                        # pbar.update(1)

    def on_button_click(self, b):
        """
            Handle button click event.

            :param b: The button object that was clicked.
            :type b: Button
            :return: None
        """
        with self.out:
            self.out.clear_output()  # Clear the previous output
        self.draw_and_process()

        # Assuming `distinct_values` is available after drawing and processing

    def get_bounding_box(self, distinct_values=None, feature=None):
        """
        :param distinct_values: A list of distinct values used for filtering the layer data
        :param feature: An optional feature object used for defining a custom geometry
        :return: The bounding box of the selected data

        This method calculates the bounding box of the selected data based on the provided parameters. If distinct_values is specified, it filters the layer data based on the values in distinct
        *_values and returns the bounding box of the filtered data. If feature is specified, it converts the feature to a GeoDataFrame and returns the bounding box of the geometry. If neither
        * distinct_values nor feature is provided, it returns the bounding box of the dissolved geometry of the User Uploaded Data.

        Example usage:
        ----------------
        distinct_values = ['value1', 'value2']
        feature = ee.Feature()

        bounding_box = get_bounding_box(distinct_values, feature)
        print(bounding_box)
        """

        if distinct_values:
            if self.dropdown.value.split('_')[0] == 'admin':
                bounds = self.layer.filter(ee.Filter.inList(self.column, distinct_values)).geometry().bounds().getInfo()
                gdf = gpd.GeoDataFrame([{'geometry': shape(bounds)}], crs='EPSG:4326')
                return gdf.geometry.bounds
            elif self.dropdown.value.split('_')[0] == 'watersheds':
                bounds = self.layer.filter(
                    ee.Filter.inList(self.column, distinct_values)).geometry().bounds().getInfo()
                gdf = gpd.GeoDataFrame([{'geometry': shape(bounds)}], crs='EPSG:4326')
                return gdf.geometry.bounds
        if 'User Uploaded Data' in self.userlayers and self.boundary_type.value == 'User Uploaded Data':
            gdf = gpd.GeoDataFrame.from_features(self.userlayers['User Uploaded Data'].data)
            dissolved_gdf = gdf.dissolve()
            self.geometry = dissolved_gdf.geometry.iloc[0]
            return dissolved_gdf.geometry.bounds

        elif self.draw_layer and self.boundary_type.value == 'User Defined':
            if feature:
                if isinstance(feature, ee.Feature):
                    feature_info = feature.getInfo()  # This converts the GEE Feature to a Python dictionary
                    geometry = feature_info['geometry']
                gdf = gpd.GeoDataFrame([{'geometry': shape(geometry)}], crs='EPSG:4326')
                self.geometry = gdf.geometry.iloc[0]
                return gdf.geometry.bounds

    def get_map_and_output(self):
        """

        :return: A tuple containing the map object `self` and the output attribute `self.out`.

        """
        return self, self.out

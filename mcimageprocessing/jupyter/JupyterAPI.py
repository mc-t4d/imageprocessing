import subprocess

import ee
import geopandas as gpd
import ipyfilechooser as fc
import ipywidgets as widgets
import localtileserver
import pandas as pd
import numpy as np
import pygrib
import json
from shapely.geometry import Point
import geemap
from pyproj import Proj, transform
from IPython.display import HTML
import datetime
from ipywidgets import Output
from ipyleaflet import GeoJSON
import ipyleaflet
from mcimageprocessing.programmatic.APIs.WorldPop import WorldPopNotebookInterface
from mcimageprocessing.programmatic.APIs.ModisNRT import ModisNRTNotebookInterface
from mcimageprocessing.programmatic.APIs.GloFasAPI import GloFasAPINotebookInterface
from mcimageprocessing.programmatic.APIs.EarthEngine import EarthEngineNotebookInterface
from mcimageprocessing.programmatic.APIs.GPWv4 import GPWv4NotebookInterface
from shapely.geometry import shape
from shapely.geometry import MultiPolygon
from osgeo import gdal
import geojson
import rasterio
from rasterio.features import geometry_mask
from tqdm.notebook import tqdm as notebook_tqdm
from mcimageprocessing.programmatic.APIs.EarthEngine import EarthEngineManager
from ipywidgets import VBox, Layout
from shapely.geometry import shape
import warnings
from IPython.display import display

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

    added_layers = {}

    def __init__(self):
        super().__init__()
        self.worldpop_class = WorldPopNotebookInterface()
        self.modis_nrt_class = ModisNRTNotebookInterface()
        self.ee_instance = EarthEngineManager()
        self.glofas_class = GloFasAPINotebookInterface()
        self.gee_class = EarthEngineNotebookInterface()
        self.gpwv4_class = GPWv4NotebookInterface()

        self.create_widgets()

        self.setup_event_listeners()

        self.initialize_ui_state()

        for control in list(self.controls):
            if isinstance(control, ipyleaflet.WidgetControl):
                # Check for a specific property of the widget
                # For example, if the widget has a unique title, icon, or label
                if 'Search location/data' in str(control.widget) or 'wrench' in str(control):
                    self.remove_control(control)
                    continue

                    # self.update_final_output()

    def get_map_and_output(self):
        """

        :return: A tuple containing the map object `self` and the output attribute `self.out`.

        """
        return self, self.out

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
        # self.dropdown.layout.width = 'auto'

        self.dropdown_api = self.create_dropdown({
            'GloFas': 'glofas',
            'Google Earth Engine': 'gee',
            'MODIS NRT Flood Data': 'modis_nrt',
            'WorldPop': 'worldpop',
            # 'Global Flood Database': 'global_flood_database',
            'GPWv4': 'gpwv4'
        },
            'Select API:',
            'worldpop')
        # self.dropdown_api.layout.width = 'auto'

        self.btn = widgets.Button(description='Process')
        self.btn.layout.width = '100%'
        self.btn.style.button_color = '#c8102e'
        self.btn.style.text_color = 'white'

        self.instruction_text = widgets.Text(value='Draw one or more polygons on the map', disabled=True)
        self.instruction_text.style.text_color = '#c8102e'
        self.upload_widget = widgets.FileUpload(accept='.geojson', multiple=False)
        self.upload_widget.layout.width = '100%'
        self.upload_widget.style.button_color = '#c8102e'
        self.upload_widget.style.text_color = 'white'

        self.boundary_stack = VBox([self.dropdown, self.instruction_text, self.upload_widget])

        self.api_choice_stack = VBox([])

        self.predefined_upload_widget = widgets.FileUpload(
            accept='.json',
            multiple=False  # True to accept multiple files upload else False
        )

        self.predefined_upload_widget.layout.display = 'none'
        self.predefined_upload_widget.layout.width = '100%'
        self.predefined_upload_widget.style.button_color = '#c8102e'
        self.predefined_upload_widget.style.text_color = 'white'

        max_width_value = '600px'

        self.out = Output(layout=Layout(max_height='1vh', overflow_y='scroll'))

        self.inner_widget_container = VBox(
            [self.boundary_type, self.boundary_stack, self.dropdown_api, self.api_choice_stack,
             self.predefined_upload_widget, self.btn, self.out],
            layout=Layout(width='100%', max_width=max_width_value)  # Set the width to '100%' and max_width to '50%'
        )

        # self.widget_container = VBox(
        #     [self.inner_widget_container],
        #     layout=Layout(justify_content='center', width='100%', max_height='40vh', overflow_y='scroll')  # Set the width of the outer container to '100%'
        # )

        for widget in [self.dropdown, self.dropdown_api, self.btn, self.out]:
            widget.layout.width = '100%'

        self.userlayers = {}

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
        self.add_widget(self.inner_widget_container,
                        layout=Layout(justify_content='center', max_height='30vh', overflow='auto'))

    def create_dropdown(self, dropdown_options: list, description: str, default_value):
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
                    bounds = self.calculate_bounds(geojson_content)
                    self.fit_bounds(bounds)
                    self.userlayers['User Uploaded Data'] = geojson_layer
                except Exception as e:
                    with self.out:
                        self.out.clear_output()
                        print(f"Error adding layer: {e}")

        except Exception as e:
            with self.out:
                self.out.clear_output()
                print(f"Error processing files: {e}")

    def convert_to_cog(self, input_path: str, output_path: str):
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

    def convert_grib_to_geotiff(self, grib_path: str, geotiff_path: str):
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

    def clip_raster(self, file_path, geometry):
        """
        :param file_path: The file path of the raster file (GRIB or TIFF) to be clipped.
        :param geometry: The geometry to clip the raster file.
        :return: The file path of the clipped TIFF file.
        """

        # Check file format and inspect if it's a GRIB file

        if file_path.endswith('.grib'):
            self.inspect_grib_file(file_path)

        # Convert Earth Engine geometry to shapely geometry
        geometry = self.ee_instance.ee_geometry_to_shapely(geometry)

        # Convert to MultiPolygon if needed
        if isinstance(geometry, dict):
            try:
                geometry = shape(geometry['geometries'][1])
            except KeyError:
                geometry = shape(geometry)
        if not isinstance(geometry, MultiPolygon):
            geometry = MultiPolygon([geometry])

        # Create a GeoDataFrame
        gdf = gpd.GeoDataFrame([{'geometry': geometry}], crs="EPSG:4326")

        # Open the raster file with rasterio
        with rasterio.open(file_path) as src:

            # Reproject the geometry to match the raster's CRS
            gdf = gdf.to_crs(src.crs)

            # Read the raster data
            raster_data = src.read(1)

            # Determine the nodata value based on the data type
            if raster_data.dtype == 'uint8':
                nodata_value = 255
            else:
                nodata_value = -9999

            # Create the mask
            mask = geometry_mask(gdf.geometry, transform=src.transform, invert=True,
                                 out_shape=(src.height, src.width))

            # Apply the mask - set nodata values
            raster_data[~mask] = nodata_value

            # Define output path
            output_path = file_path.rsplit('.', 1)[0] + '_clipped.tif'

            # Write the masked data to a new raster file
            with rasterio.open(
                output_path,
                'w',
                driver='GTiff',
                height=src.height,
                width=src.width,
                count=1,
                dtype=raster_data.dtype,
                crs=src.crs,
                transform=src.transform,
                nodata=nodata_value
            ) as dst:
                dst.write(raster_data, 1)

        return output_path

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
        with self.out:
            print(f"API Change detected. New value: {change['new']}")
            new_value = change['new']

            # Add the appropriate layer based on the selection
            if new_value == 'glofas':
                try:

                    self.glofas_options = self.glofas_class.create_glofas_dropdown(
                        [x for x in self.glofas_class.glofas_dict['products'].keys()],
                        description='Select GloFas Product:',
                        default_value='cems-glofas-forecast'
                    )
                    self.glofas_options.layout.width = 'auto'
                    self.glofas_options.observe(self.glofas_class.on_glofas_option_change, names='value')
                    self.glofas_class.on_glofas_option_change({'new': self.glofas_options.value})
                    self.api_choice_stack.children = [self.glofas_options, self.glofas_class.glofas_stack]
                    # self.api_choice_stack.layout.display = 'none'  # Hide and then show to force a refresh
                    # self.api_choice_stack.layout.display = 'block'

                    if self.boundary_type.value == 'Predefined Boundaries':
                        self.update_boundary_options('Predefined Boundaries')
                except Exception as e:
                    print(f"Error setting up GloFas options: {e}")

            elif new_value == 'gee':
                self.gee_options = self.gee_class.create_widgets_gee()
                # self.gee_options.layout.width = 'auto'
                self.api_choice_stack.children = tuple(self.gee_options)
                if self.boundary_type.value == 'Predefined Boundaries':
                    self.update_boundary_options('Predefined Boundaries')
            elif new_value == 'modis_nrt':
                self.modis_nrt_options = self.modis_nrt_class.create_widgets_for_modis_nrt()
                self.api_choice_stack.children = tuple(self.modis_nrt_options)
                if self.boundary_type.value == 'Predefined Boundaries':
                    self.update_boundary_options('Predefined Boundaries')

            elif new_value == 'worldpop':
                self.worldpop_options = self.worldpop_class.create_widgets_for_worldpop()
                self.api_choice_stack.children = tuple(self.worldpop_options)
                if self.boundary_type.value == 'Predefined Boundaries':
                    self.update_boundary_options('Predefined Boundaries')
            elif new_value == 'gpwv4':
                self.gp4w_options = self.gpwv4_class.create_widgets_for_gpwv4()
                self.api_choice_stack.children = tuple(self.gp4w_options)
                if self.boundary_type.value == 'Predefined Boundaries':
                    self.update_boundary_options('Predefined Boundaries')
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
            # self.end_of_vbox_items.layout.display = 'block'
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
                # self.end_of_vbox_items.layout.display = 'block'
                self.boundary_stack.layout.display = 'block'
                self.dropdown_api.layout.display = 'block'
                self.api_choice_stack.layout.display = 'block'

            elif boundary_value == 'User Uploaded Data':
                # User uploaded data selected
                self.dropdown.layout.display = 'none'  # Hide the dropdown
                self.instruction_text.layout.display = 'none'  # Hide the instruction text
                self.upload_widget.layout.display = 'block'  # Show the upload widget
                self.predefined_upload_widget.layout.display = 'none'
                # self.end_of_vbox_items.layout.display = 'block'
                self.boundary_stack.layout.display = 'block'
                self.dropdown_api.layout.display = 'block'
                self.api_choice_stack.layout.display = 'block'

        elif boundary_value == 'Parameter File':
            self.predefined_upload_widget.layout.display = 'block'
            # self.end_of_vbox_items.layout.display = 'none'
            self.boundary_stack.layout.display = 'none'
            self.dropdown_api.layout.display = 'none'
            self.api_choice_stack.layout.display = 'none'

        else:
            # Default case, hide everything
            self.dropdown.layout.display = 'none'
            self.instruction_text.layout.display = 'none'
            self.upload_widget.layout.display = 'none'

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

    def on_button_click(self, b):
        """
        Function to handle button click event.

        :param b: Button object representing the clicked button.
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

    def draw_and_process(self):
        """
        Draw and process data based on the boundary type.

        :return: None
        """
        if self.boundary_type.value == 'Parameter File':
            self.handle_parameter_file()
        else:
            self.process_based_on_api_selection()

    def handle_parameter_file(self):
        """
        Handle parameter file logic.

        :return: None
        """
        # Handle parameter file logic here
        pass

    def add_image_to_map(self, image_or_stats, params, geometry):
        with self.out:
            if params['add_image_to_map'] and isinstance(image_or_stats, ee.Image):
                # Get the projection of the first band
                projection = image_or_stats.select(0).projection()
                # Get the scale (in meters) of the projection
                scale = projection.nominalScale()

                # Calculate the min and max values of the image using dynamically obtained scale
                stats = image_or_stats.reduceRegion(
                    reducer=ee.Reducer.minMax(),
                    geometry=geometry,
                    scale=scale.getInfo(),  # Use the dynamically obtained scale
                    maxPixels=1e9
                )


                # Get the computed min and max values
                min_val = stats.getInfo()[f"{params['band']}_min"]
                max_val = stats.getInfo()[f"{params['band']}_max"]

                # Define visualization parameters using dynamic min and max
                visParams = {
                    'min': min_val,
                    'max': max_val,
                    'palette': ['440154', '21908C', 'FDE725']  # Viridis color palette
                }

                # Add EE layer with the specified visualization parameters
                self.add_ee_layer(image_or_stats, visParams)
            elif params['add_image_to_map'] and isinstance(image_or_stats, str):
                vis_params = {}
                client = localtileserver.TileClient(image_or_stats)
                tile_layer = localtileserver.get_leaflet_tile_layer(client, **vis_params)
                self.add_layer(tile_layer)
                self.fit_bounds(client.bounds)


    def process_api(self, api_class, api_name, geometry, distinct_values, index, bbox=None, additional_params=None):
        with self.out:
            try:
                # additional_params is a dictionary containing any additional parameters required by gather_parameters
                additional_params = additional_params or {}  # default to empty dict if None
                params = api_class.gather_parameters(**additional_params)  # Unpack additional parameters
                image_or_stats = api_class.process_api(geometry=geometry, distinct_values=distinct_values, index=index,
                                                       params=params, bbox=bbox)

                try:
                    self.add_image_to_map(image_or_stats, params, geometry)
                except Exception as e:
                    print(f"Error adding image to map: {e}")

                print('Added to map!')
            except Exception as e:
                print(f"Error processing {api_name}: {e}")

    def handle_glofas(self, geometry, distinct_values, index):
        additional_params = {
            'glofas_product': self.glofas_options.value}  # Include any specific parameters required by the GloFAS API
        bbox = self.get_bounding_box(distinct_values, geometry)
        self.process_api(self.glofas_class, 'glofas', geometry, distinct_values, index, bbox=bbox, additional_params=additional_params)

    def handle_gee(self, geometry, distinct_values, index):
        self.process_api(geometry, distinct_values, index)

    def handle_modis_nrt(self, geometry, distinct_values, index):
        bbox = self.get_bounding_box(distinct_values, geometry)
        self.process_api(self.modis_nrt_class, 'modis_nrt', geometry=geometry, distinct_values=distinct_values, index=index, bbox=bbox)

    def handle_worldpop(self, geometry, distinct_values, index):
        # No additional params required for WorldPop in this example
        self.process_api(self.worldpop_class, 'worldpop', geometry, distinct_values, index)

    def handle_gpwv4(self, geometry, distinct_values, index):
        self.process_api(self.gpwv4_class, 'gpwv4', geometry, distinct_values, index)

    def process_based_on_api_selection(self):
        """
        Process based on the selected API.

        :return: None
        """
        api_handlers = {
            'glofas': self.handle_glofas,
            'gee': self.handle_gee,
            'modis_nrt': self.handle_modis_nrt,
            'worldpop': self.handle_worldpop,
            'gpwv4': self.handle_gpwv4,
        }

        with self.out:
            geometries = self.ee_instance.determine_geometries_to_process(layer=self.layer, column=self.column,
                                                                          dropdown_api=self.dropdown_api.value,
                                                                          boundary_type=self.boundary_type.value,
                                                                          draw_features=self.draw_features,
                                                                          userlayers=self.userlayers,
                                                                          boundary_layer=self.dropdown.value)
            for index, (geometry, distinct_values) in enumerate(geometries):
                api_handler = api_handlers.get(self.dropdown_api.value)
                if api_handler:
                    api_handler(geometry, distinct_values, index)
                else:
                    print('No valid API selected!')


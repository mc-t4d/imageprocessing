import subprocess
import warnings

import branca.colormap as cm
import ee
import geemap
import geojson
import geopandas as gpd
import ipyleaflet
import os
import ipywidgets as widgets
import localtileserver
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from IPython.display import HTML
from IPython.display import display
from ipyleaflet import GeoJSON
from ipywidgets import Output
from ipywidgets import VBox, Layout
from pyproj import transform
from rasterio.features import geometry_mask
from shapely.geometry import MultiPolygon
from shapely.geometry import shape
from shapely.geometry import shape
from tqdm.notebook import tqdm as notebook_tqdm
from mcimageprocessing import config_manager
from mcimageprocessing.programmatic.shared_functions.utilities import calculate_bounds

from mcimageprocessing.programmatic.APIs.EarthEngine import EarthEngineManager
from mcimageprocessing.programmatic.APIs.EarthEngine import EarthEngineNotebookInterface
from mcimageprocessing.programmatic.APIs.GPWv4 import GPWv4NotebookInterface
from mcimageprocessing.programmatic.APIs.GloFasAPI import GloFasAPINotebookInterface
from mcimageprocessing.programmatic.APIs.ModisNRT import ModisNRTNotebookInterface
from mcimageprocessing.programmatic.APIs.WorldPop import WorldPopNotebookInterface

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

    :class: OutputWidgetTqdm

    OutputWidgetTqdm is a class that extends the `notebook_tqdm` class to redirect the progress bar display to a specified output widget.

    Methods:

    - __init__(*args, **kwargs): Initializes the OutputWidgetTqdm object. You can pass additional arguments here if needed, or pass them through to the superclass. The 'output_widget' keyword
    * argument allows you to specify the output widget to redirect the progress bar display.

    - display(*args, **kwargs): Overrides the display method to redirect the progress bar display to the specified output widget. If no 'output_widget' is specified, the progress bar will
    * be displayed in the default output area.

    Example usage:

    ```
    output_widget = OutputWidget()

    # Create an instance of OutputWidgetTqdm and pass the output_widget
    pbar = OutputWidgetTqdm(total=10, output_widget=output_widget)

    # Display the progress bar in the output_widget
    pbar.display()

    # Update the progress
    pbar.update(1)

    # Clear the output_widget
    output_widget.clear_output()
    ```
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
        """Initialize the NotebookInterface class.

        This method initializes the NotebookInterface class by calling the __init__ method of its parent class and setting up various class variables.

        Parameters:
            None

        Returns:
            None
        """
        super().__init__(ee_initialize=False)
        credentials = ee.ServiceAccountCredentials(
            email=config_manager.config['KEYS']['GEE']['client_email'],
            key_data=config_manager.config['KEYS']['GEE']['private_key']
        )

        ee.Initialize(credentials)
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

        self.progress = None

    def get_map_and_output(self):
        """
        Returns the map and output of the method.

        :return: A tuple containing the map and output.
        :rtype: tuple
        """
        return self, self.out

    def create_dropdown(self, dropdown_options, description, default_value):
        """
        Create a dropdown widget with specified options, description, and default value.

        :param dropdown_options: list of options for the dropdown widget
        :param description: description of the dropdown widget
        :param default_value: default value for the dropdown widget
        :return: dropdown widget
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
        """
        Function to create and initialize widgets for the user interface.

        :return: None
        """
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
            # 'Google Earth Engine': 'gee',
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
        Sets up event listeners for various UI components.

        :return: None
        """
        self.boundary_type.observe(self.on_boundary_type_change, names='value')
        self.dropdown.observe(self.on_dropdown_change, names='value')
        self.dropdown_api.observe(self.on_api_change, names='value')
        self.btn.on_click(self.on_button_click)
        self.upload_widget.observe(self.on_file_upload, names='value')

    def initialize_ui_state(self):
        """
        Initializes the UI state by performing the following tasks:
        - Calls the `on_dropdown_change` method with `{'new': self.dropdown.value}` as the argument
        - Calls the `on_api_change` method with `{'new': self.dropdown_api.value}` as the argument
        - Calls the `on_boundary_type_change` method with `{'new': self.boundary_type.value}` as the argument
        - Calls the `on_file_upload` method with `{'new': self.upload_widget.value}` as the argument
        - Sets the `display` property of the `instruction_text` layout to `'none'`
        - Sets the `display` property of the `upload_widget` layout to `'none'`
        - Calls the `on_api_change` method with `{'new': self.dropdown_api.value}` as the argument
        - Adds the `inner_widget_container` to the display with the specified layout properties

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
        Create a dropdown widget with the provided options, description, and default value.

        :param dropdown_options: A list of options for the dropdown widget.
        :param description: The description of the dropdown widget.
        :param default_value: The default value for the dropdown widget.
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

    # def update_gee_date_selection_box(self, change):

    def toggle_minimize(self, b):
        """
        Toggle the visibility of the main content and update the button text.

        :param b: The boolean value indicating whether to minimize or maximize the content.
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

    def on_file_upload(self, change):
        """
        :param change: A dictionary containing the information of the uploaded files.
        :return: None

        The 'on_file_upload' method is responsible for processing uploaded files and adding them as a GeoJSON layer to the map. It takes in a 'change' parameter, which is a dictionary that contains
        * the information of the uploaded files.

        The method starts by retrieving the list of uploaded file info from the 'change' dictionary. Then, it iterates over each file and extracts the filename and content. The content is initially
        * in the form of a memoryview object, which is converted to bytes and decoded to a string using 'utf-8' encoding.

        Next, the string content is loaded as GeoJSON using the 'geojson.loads' function. A style dictionary is created to define the appearance of the GeoJSON layer, including the line color
        *, fill color, border width, and fill opacity.

        A GeoJSON layer is created using the 'GeoJSON' class, with the loaded geojson_content and style as parameters. This layer is then added to the map using the 'add_layer' method, with
        * additional parameters like name and visualization parameters.

        If the layer is successfully added, the 'calculate_bounds' method is used to calculate the bounding box of the GeoJSON layer. This bounding box is then used to fit the map view using
        * the 'fit_bounds' method. Finally, the GeoJSON layer is stored in the 'userlayers' dictionary with the name 'User Uploaded Data'.

        If there are any errors during the processing or adding of the files, an exception is raised and caught. The error message is then printed to the output widget.

        Note: The method is part of a class and assumes the presence of certain properties and methods like 'self.add_layer', 'calculate_bounds', 'self.fit_bounds', 'self.userlayers', and
        * 'self.out'.
        """
        uploaded_files = change['new']  # Get the list of uploaded file info
        with self.out:
            try:
                # Process each uploaded file
                for file_info in uploaded_files:
                    filename = file_info['name']
                    content = file_info['content']  # file content as a memoryview object
                    content_str = bytes(content).decode("utf-8")  # convert to string

                    # Load the string as GeoJSON
                    geojson_content = geojson.loads(content_str)

                    # Ensure the loaded GeoJSON content is in FeatureCollection format
                    if isinstance(geojson_content, geojson.FeatureCollection):
                        data_to_add = geojson_content
                    elif isinstance(geojson_content, (geojson.Feature, geojson.geometry.Geometry)):
                        # Wrap the single feature or geometry into a FeatureCollection
                        data_to_add = geojson.FeatureCollection([geojson_content])
                    else:
                        raise ValueError("Unsupported GeoJSON type")

                    # Define the style for the layer
                    style = {"color": "black", "fillColor": "black", "weight": 1, "fillOpacity": 0.5}

                    # Create and add the GeoJSON layer to the map
                    geojson_layer = GeoJSON(data=data_to_add, style=style)
                    self.add_layer(geojson_layer, name='User Uploaded Data', vis_params={'color': 'black'})
                    bounds = calculate_bounds(data_to_add)
                    self.fit_bounds(bounds)
                    self.userlayers['User Uploaded Data'] = geojson_layer

            except Exception as e:
                self.out.clear_output()
                print(f"Error processing files: {e}")

    def convert_to_cog(self, input_path: str, output_path: str):
        """
        Convert a GeoTIFF to a COG using gdal_translate

        :param input_path: The path to the input GeoTIFF file
        :param output_path: The path where the COG will be saved
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

        :param grib_path: The path to the GRIB file.
        :param geotiff_path: The path to save the converted GeoTIFF file.
        :return: None
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

        :param raster_array: The raster array.
        :type raster_array: ndarray

        :param transform: The affine transformation matrix of the raster array.
        :type transform: affine.Affine

        :param shape: The shape of the output raster array.
        :type shape: tuple

        :param geometry: The geometry within which to find the edge values.
        :type geometry: shapely.geometry.*

        :return: An array containing the unique edge values of the raster.
        :rtype: ndarray
        """
        # Create a mask for the geometry
        mask = geometry_mask([geometry], transform=transform, invert=True, out_shape=shape)

        # Find the edge values of the raster
        edge_values = np.unique(raster_array[mask])
        return edge_values

    def get_nodata_value(self, src):
        """
            Tries to retrieve the no-data value from the source metadata. If it is not set, it infers it from data statistics or common conventions.

            :param src: The source object containing the data.
            :return: The no-data value.

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
        :param out_image: the output image or array
        :param nodata_value: the known no-data value
        :return: a mask array indicating the presence of no-data values

        This method creates a mask array based on the provided no-data value.
        If no no-data value is specified, a custom strategy can be used to infer it.
        For floating-point comparisons, a tolerance is used. For integer types, a direct comparison is performed.
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

    def clip_raster(self, file_path: str, geometry, output_file_name: str = None):
        """
        Clip a raster file based on a given geometry and return the path to the clipped file.

        :param file_path: The path to the raster file to be clipped.
        :type file_path: str
        :param geometry: The geometry to use for clipping the raster.
        :type geometry: Union[shapely.geometry.Polygon, shapely.geometry.MultiPolygon, dict]
        :return: The path to the clipped raster file.
        :rtype: str
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
            file_dir, file_name = os.path.split(file_path)
            file_base, file_ext = os.path.splitext(file_name)
            output_filename = f"{file_base}_clipped.tif" if output_file_name is None else output_file_name
            output_path = os.path.join(file_dir, output_filename)

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
        :param change: dictionary containing the new value of the dropdown
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

    def on_api_change(self, change):
        """
        :param change: the change event triggered by the API selection
        :return: None

        This method is called when there is a change in the API selection. It takes the 'change' parameter which contains information about the new value selected for the API.

        Based on the new value, different actions are performed:
        - If the new value is 'glofas', create the GloFas dropdown menu and update the API choices stack with the GloFas options.
        - If the new value is 'gee', create the Google Earth Engine options and update the API choices stack.
        - If the new value is 'modis_nrt', create the MODIS NRT options and update the API choices stack.
        - If the new value is 'worldpop', create the WorldPop options and update the API choices stack.
        - If the new value is 'gpwv4', create the GPWv4 options and update the API choices stack.
        - If the new value is any other value, do nothing.

        If the boundary type selected is 'Predefined Boundaries', the boundary options are updated accordingly.

        Note: The code snippets that are commented out with '# self.api_choice_stack.layout.display = 'none'' and '# self.api_choice_stack.layout.display = 'block'' seem to be hiding and then
        * showing the API choices stack, but are currently not active.
        """
        with self.out:
            new_value = change['new']

            # Add the appropriate layer based on the selection
            if new_value == 'glofas':

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
        Function to handle a change in the boundary type.

        :param change: A dictionary containing the changes made to the boundary type.
        :return: None
        """
        boundary_value = change['new']
        self.update_boundary_options(boundary_value)

    def update_boundary_options(self, boundary_value):
        """
        :param boundary_value: the value indicating the type of boundary selected
        :return: None

        This method updates the options for the boundary dropdown based on the value of "boundary_value". The dropdown options are modified according to the selected boundary type.

        If "boundary_value" is equal to 'Predefined Boundaries':
        - Calls the method "on_dropdown_change" passing {'new': self.dropdown.value} as argument
        - sets self.dropdown.layout.display to 'block'
        - sets self.instruction_text.layout.display to 'none'
        - sets self.upload_widget.layout.display to 'none'
        - sets self.predefined_upload_widget.layout.display to 'none'
        - sets self.boundary_stack.layout.display to 'block'
        - sets self.dropdown_api.layout.display to 'block'
        - sets self.api_choice_stack.layout.display to 'block'

        If "boundary_value" is either 'User Defined' or 'User Uploaded Data':
        - Removes EE Leaflet Tile Layers with Google Earth Engine attribution
        - If "boundary_value" is 'User Defined':
          - sets self.dropdown.layout.display to 'none'
          - sets self.instruction_text.layout.display to 'block'
          - sets self.upload_widget.layout.display to 'none'
          - sets self.predefined_upload_widget.layout.display to 'none'
          - sets self.boundary_stack.layout.display to 'block'
          - sets self.dropdown_api.layout.display to 'block'
          - sets self.api_choice_stack.layout.display to 'block'
        - If "boundary_value" is 'User Uploaded Data':
          - sets self.dropdown.layout.display to 'none'
          - sets self.instruction_text.layout.display to 'none'
          - sets self.upload_widget.layout.display to 'block'
          - sets self.predefined_upload_widget.layout.display to 'none'
          - sets self.boundary_stack.layout.display to 'block'
          - sets self.dropdown_api.layout.display to 'block'
          - sets self.api_choice_stack.layout.display to 'block'

        If "boundary_value" is 'Parameter File':
        - sets self.predefined_upload_widget.layout.display to 'block'
        - sets self.boundary_stack.layout.display to 'none'
        - sets self.dropdown_api.layout.display to 'none'
        - sets self.api_choice_stack.layout.display to 'none'

        In any other case:
        - sets self.dropdown.layout.display to 'none'
        - sets self.instruction_text.layout.display to 'none'
        - sets self.upload_widget.layout.display to 'none'
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
        :param geometry: A geometry object representing a polygon or multipolygon.
        :return: A multipolygon geometry object containing the input geometry.
        """
        if geometry.type().getInfo() == 'Polygon':
            return ee.Geometry.MultiPolygon([geometry.coordinates()])
        else:
            return geometry

    def on_button_click(self, b):
        """
        :param b: A parameter representing the button that was clicked
        :return: None

        This method is called when a button is clicked. It first clears the output area, and then calls the `draw_and_process` method to draw and process some data. After the drawing and processing
        * is done, the method assumes that the variable `distinct_values` is available for further use.
        """
        with self.out:
            self.out.clear_output()  # Clear the previous output
        self.draw_and_process()

        # Assuming `distinct_values` is available after drawing and processing


    def get_bounding_box(self, distinct_values=None, feature=None):
        """
        :param distinct_values: A list of distinct values to filter the layer by.
        :param feature: An optional feature object to use for calculating the bounding box.
        :return: The bounding box of the layer's filtered geometry.

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
        Draw and process the input based on the boundary type.

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
        with self.out:
            print(self.predefined_upload_widget.value)

    def add_image_to_map(self, image_or_stats, params, geometry):
        """
        Add an image or statistics to the map.

        :param image_or_stats: The image or statistics to be added to the map.
        :param params: Parameters for visualization.
        :param geometry: The geometry to restrict the image statistics.
        :return: None
        """
        with self.out:
            if params['add_image_to_map'] and isinstance(image_or_stats, ee.Image):
                self.remove_colorbar()
                self.remove_legend()

                if params['population_source'] == 'GPWv4':

                    scale = 927.67
                elif params['population_source'] == 'WorldPop':
                    scale = 100

                # Enhanced geometry handling
                if isinstance(geometry, ee.Geometry):
                    # If it's already an Earth Engine Geometry, use it directly
                    geometry = geometry
                elif isinstance(geometry, ee.Feature):
                    # Convert an Earth Engine Feature to an Earth Engine Geometry
                    geometry = geometry.geometry()
                elif isinstance(geometry, ee.FeatureCollection):
                    # If it's a FeatureCollection, reduce it to a single geometry
                    geometry = geometry.geometry()
                elif isinstance(geometry, dict):
                    # If it's a dictionary, it could be a GeoJSON object
                    if 'features' in geometry:
                        # It's a GeoJSON FeatureCollection, so convert it to an Earth Engine Geometry
                        # Check each feature's geometry type and convert accordingly
                        ee_geometries = []
                        for feat in geometry['features']:
                            geom_type = feat['geometry']['type']
                            if geom_type in ['Polygon', 'MultiPolygon']:
                                # Convert the GeoJSON geometry to an Earth Engine Geometry
                                ee_geom = ee.Geometry(feat['geometry'])
                                ee_geometries.append(ee_geom)
                            else:
                                # If the geometry is not a Polygon or MultiPolygon, print its type
                                print(f"Unsupported geometry type in GeoJSON feature: {geom_type}")

                        # Combine all the Earth Engine geometries into a MultiPolygon
                        if ee_geometries:
                            geometry = ee.Geometry.MultiPolygon(ee_geometries)
                        else:
                            raise ValueError("No valid Polygons or MultiPolygons found in GeoJSON features")
                    else:
                        # It's a single GeoJSON Feature, so convert it to an Earth Engine Geometry
                        geometry = ee.Geometry(shape(geometry['geometry']))
                elif isinstance(geometry, geojson.base.GeoJSON):
                    # If it's a GeoJSON object from the geojson library
                    geometry = ee.Geometry(shape(geometry))
                else:
                    raise ValueError("Unsupported geometry type")

                # Calculate the min and max values of the image using dynamically obtained scale
                stats = image_or_stats.reduceRegion(
                    reducer=ee.Reducer.minMax(),
                    geometry=geometry,
                    scale=scale,  # Use the dynamically obtained scale
                    maxPixels=1e9
                )

                # Get the computed min and max values
                min_val = stats.getInfo()[f"{params['band']}_min"]
                max_val = stats.getInfo()[f"{params['band']}_max"]


                viridis = plt.get_cmap('viridis')
                number_of_colors = 10  # You can change this to get more or fewer colors

                viridis_palette = [matplotlib.colors.rgb2hex(viridis(i / float(number_of_colors))) for i in
                                   range(number_of_colors)]

                # Define visualization parameters using dynamic min and max
                visParams = {
                    'min': min_val,
                    'max': max_val,
                    'palette': viridis_palette
                }

                # Add EE layer with the specified visualization parameters
                self.add_ee_layer(image_or_stats, visParams)
                color_bar = cm.LinearColormap(
                    visParams['palette'],
                    vmin=visParams['min'],
                    vmax=visParams['max']
                ).to_step(n=10)  # You can adjust the number of steps
                caption = 'Population Count per Pixel'
                self.add_colorbar(vis_params=visParams, label=caption, position='bottomleft')
            elif params['add_image_to_map'] and isinstance(image_or_stats, str):
                self.remove_colorbar()
                self.remove_legend()

                # Process the image using localtileserver
                client = localtileserver.TileClient(image_or_stats)

                # Use rasterio to read the image data and determine visualization parameters
                with rasterio.open(image_or_stats) as src:
                    # Read the first band
                    array = src.read(1)
                    nodata_value = src.nodatavals[0]  # Get nodata value from the file

                    # Mask the nodata values
                    masked_array = np.ma.masked_where(array == nodata_value, array)

                    # Calculate min and max from the masked array
                    min_val = masked_array.min()
                    max_val = masked_array.max()

                    unique_values = np.unique(
                        masked_array.compressed())  # Use compressed to get only the non-masked values
                    if len(unique_values) <= 10:  # Discrete data
                        # Define colors and color bar for discrete data
                        legend_keys = ['No Water', 'Surface Water', 'Recurring Flood', 'Flood']
                        discrete_colors = ['#000000', '#00FF00',  '#FFF000', '#FF0000']
                        vis_params = {'palette': discrete_colors, 'vmin': min_val, 'vmax': max_val, 'n_colors': 4, 'scheme':'discrete'}
                        caption = 'Modis NRT'
                        # Create tile layer with visualization parameters
                        tile_layer = localtileserver.get_leaflet_tile_layer(client, **vis_params)
                        self.add_layer(tile_layer)
                        self.fit_bounds(client.bounds)

                        self.add_legend(keys=legend_keys, colors=discrete_colors, title=caption, position='bottomleft')
                    else:
                        # Define colors and color bar for continuous data
                        viridis = plt.get_cmap('viridis')
                        continuous_palette = [matplotlib.colors.rgb2hex(viridis(i / 10)) for i in range(10)]
                        vis_params = {'palette': continuous_palette, 'min': min_val, 'max': max_val}
                        caption = 'GloFas Data'
                        # Create tile layer with visualization parameters
                        tile_layer = localtileserver.get_leaflet_tile_layer(client, **vis_params)
                        self.add_layer(tile_layer)
                        self.fit_bounds(client.bounds)

                        # Create and add color bar
                        color_bar = cm.LinearColormap(vis_params['palette'], vmin=vis_params['min'],
                                                      vmax=vis_params['max']).to_step(n=10)
                        color_bar.caption = caption
                        self.add_colorbar(vis_params=vis_params, label=color_bar.caption, position='bottomleft')


    def process_api(self, api_class, api_name, geometry, distinct_values, index, bbox=None, additional_params=None):
        """
        Process the API request.

        :param api_class: The API class to use for processing the request.
        :param api_name: The name of the API.
        :param geometry: The geometry to use for the request.
        :param distinct_values: A flag indicating whether to retrieve distinct values.
        :param index: The index to use for the request.
        :param bbox: The bounding box to use for the request. (Optional)
        :param additional_params: Additional parameters to pass to the API. (Optional)
        :return: None
        """
        with self.out:

            try:
                # additional_params is a dictionary containing any additional parameters required by gather_parameters
                additional_params = additional_params or {}  # default to empty dict if None
                params = api_class.gather_parameters(**additional_params)  # Unpack additional parameters
                with self.out:
                    pbar = notebook_tqdm(total=10, desc='Processing', leave=False)

                    image_or_stats = api_class.process_api(geometry=geometry, distinct_values=distinct_values, index=index,
                                                           params=params, bbox=bbox, pbar=pbar)

                try:
                    self.add_image_to_map(image_or_stats, params, geometry)
                except Exception as e:
                    print(f"Error adding image to map: {e}")

            except Exception as e:
                print(f"Error processing {api_name}: {e}")

    def handle_glofas(self, geometry, distinct_values, index):
        """
        Handles GloFAS API request for a given geometry and distinct values.

        :param geometry: The geometry to be used for the API request.
        :param distinct_values: The distinct values to be used for the API request.
        :param index: The index to be used for the API request.
        :return: None
        """
        additional_params = {
            'glofas_product': self.glofas_options.value}  # Include any specific parameters required by the GloFAS API
        bbox = self.get_bounding_box(distinct_values, geometry)
        self.process_api(self.glofas_class, 'glofas', geometry, distinct_values, index, bbox=bbox, additional_params=additional_params)

    def handle_gee(self, geometry, distinct_values, index):
        """
        Handle Gee Method

        :param geometry: The geometry to be processed.
        :param distinct_values: The distinct values to be used.
        :param index: The index to be used.
        :return: None

        """
        self.process_api(geometry, distinct_values, index)

    def handle_modis_nrt(self, geometry, distinct_values, index):
        """
        Handles the Modis NRT data by calling the appropriate API.

        :param geometry: The geometry of the area of interest.
        :type geometry: <geometry data type>

        :param distinct_values: The distinct values associated with the data.
        :type distinct_values: <distinct_values data type>

        :param index: The index of the data.
        :type index: <index data type>

        :return: None
        :rtype: None
        """
        bbox = self.get_bounding_box(distinct_values, geometry)
        if self.boundary_type.value == 'User Uploaded Data':
            geometry = self.geometry
        self.process_api(self.modis_nrt_class, 'modis_nrt', geometry=geometry, distinct_values=distinct_values, index=index, bbox=bbox)

    def handle_worldpop(self, geometry, distinct_values, index):
        """
        Process the WorldPop data.

        :param geometry: The geometry to use for filtering.
        :type geometry: str

        :param distinct_values: The distinct attribute values to filter by.
        :type distinct_values: list

        :param index: The index of the attribute to filter on.
        :type index: int

        :return: None
        """
        # No additional params required for WorldPop in this example
        self.process_api(self.worldpop_class, 'worldpop', geometry, distinct_values, index)

    def handle_gpwv4(self, geometry, distinct_values, index):
        """
        :param geometry: The geometry for which the processing needs to be done.
        :type geometry: <data type of geometry>
        :param distinct_values: The distinct values required for processing.
        :type distinct_values: <data type of distinct_values>
        :param index: The index of the geometry.
        :type index: <data type of index>
        :return: None
        """
        self.process_api(self.gpwv4_class, 'gpwv4', geometry, distinct_values, index)

    def process_based_on_api_selection(self):
        """
        Process data based on the selected API.

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
            try:
                selected_path = self.modis_nrt_class.filechooser.selected
            except Exception as e:
                pass
            geometries = self.ee_instance.determine_geometries_to_process(layer=self.layer, column=self.column,
                                                                          dropdown_api=self.dropdown_api.value,
                                                                          boundary_type=self.boundary_type.value,
                                                                          draw_features=self.draw_features,
                                                                          userlayers=self.userlayers,
                                                                          boundary_layer=self.dropdown.value,
                                                                          output_folder_location=selected_path)
            for index, (geometry, distinct_values) in enumerate(geometries):
                api_handler = api_handlers.get(self.dropdown_api.value)
                if api_handler:
                    api_handler(geometry, distinct_values, index)
                else:
                    print('No valid API selected!')


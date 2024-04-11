import datetime
import itertools
import os
from typing import Optional
import ee
import json
from contextlib import redirect_stdout
import io
import logging
import warnings

import cdsapi
import ipyfilechooser as fc
import ipywidgets as widgets
from ipywidgets import DatePicker
from ipywidgets import VBox, HBox

from mcimageprocessing import config_manager
from mcimageprocessing.programmatic.APIs.EarthEngine import EarthEngineManager
from mcimageprocessing.programmatic.shared_functions.utilities import process_and_clip_raster


class GloFasAPI:
    def __init__(self, ee_manager: Optional[EarthEngineManager] = None):
        self.ee_instance = ee_manager if ee_manager else EarthEngineManager()
        url = config_manager.config['KEYS']['GloFas']['url']
        key = config_manager.config['KEYS']['GloFas']['key']
        self.client = cdsapi.Client(url=url, key=key)

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

        logging.getLogger('cdsapi').setLevel(logging.CRITICAL)
        warnings.filterwarnings('ignore', message='.*Template .*')
    def download_data(self, product_name, request_parameters, file_name):
        # Construct the file path
        day = request_parameters.get('day', '01')
        file_path = os.path.join(request_parameters['folder_location'], file_name)

        f = io.StringIO()
        # Call the CDS API
        with redirect_stdout(f):
            self.client.retrieve(
                product_name,
                {
                    'variable': request_parameters['variable'],
                    'format': request_parameters['format'],
                    'system_version': request_parameters['system_version'],
                    'hydrological_model': request_parameters['hydrological_model'],
                    'product_type': request_parameters['product_type'],
                    'year': request_parameters['year'],
                    'day': day,
                    'month': request_parameters['month'],
                    'leadtime_hour': request_parameters['leadtime_hour'],
                    'area': request_parameters['area'],
                },
                file_path
            )

            return file_path

    def no_data_helper_function(self, bbox, glofas_params, geometry, index, distinct_values):
        """
        Helper function to handle 'no data available' scenario by trying different combinations.
        """
        system_version_list = self.glofas_dict['products'][glofas_params['glofas_product']]['system_version']
        hydrological_model_list = self.glofas_dict['products'][glofas_params['glofas_product']]['hydrological_model']
        product_type_list = self.glofas_dict['products'][glofas_params['glofas_product']].get('product_type', [None])

        all_combinations = list(itertools.product(system_version_list, hydrological_model_list, product_type_list))

        last_attempted_combination = (glofas_params['system_version'], glofas_params['hydrological_model'],
                                      glofas_params['product_type'] if glofas_params.get('product_type') else None)

        all_combinations.remove(last_attempted_combination)

        for comb in all_combinations:
            try:
                glofas_params['system_version'], glofas_params['hydrological_model'], glofas_params[
                    'product_type'] = comb
                file_path = self.download_glofas_data(bbox, glofas_params, index, distinct_values)
                processed_raster = process_and_clip_raster(file_path, geometry, glofas_params, self.ee_instance)
                if processed_raster:  # Check if processing was successful
                    return processed_raster
            except Exception as e:
                print(e)
                if "no data is available within your requested subset" not in str(e):
                    break  # Exit the loop if a different error occurs
        print("No suitable data could be found for any combination.")
        return None

    def download_glofas_data(self, geometry, distinct_values, index):
        pass

    def _create_sub_folder(self, base_folder: str) -> str:
        """
        Create a new subfolder within the given base folder.

        :param base_folder: The path of the base folder where the subfolder will be created.
        :type base_folder: str
        :return: The path of the newly created subfolder.
        :rtype: str
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # More readable timestamp
        folder_name = os.path.join(base_folder, f"glofas_processed_on_{timestamp}")
        try:
            os.mkdir(folder_name)
            return folder_name
        except OSError as e:
            self.logger.error(f"Failed to create subfolder: {e}")
            return base_folder

class GloFasAPINotebookInterface(GloFasAPI):

    def __init__(self, ee_manager: Optional[EarthEngineManager] = None):
        super().__init__(ee_manager)
        self.out = widgets.Output()  # For displaying logs, errors, etc.
        # Initialize widgets


        self.glofas_stack = VBox([])

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

        return dropdown

    def create_widgets_for_glofas(self, glofas_option: str):
        """
        Create widgets specific to GloFas Data Type 2

        :param glofas_option: The selected GloFas option
        :return: A list of widgets specific to the selected GloFas option
        """
        # Create widgets specific to GloFas Data Type 2
        # Example: A slider for selecting a range and a button


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
            options=['Single Date'],
            disabled=False,
            value='Single Date',
            tooltips=['Single Date'],
        )

        self.glofas_date_vbox = VBox([])
        self.on_single_or_date_range_change({'new': self.single_or_date_range.value}, glofas_option=glofas_option)

        self.single_or_date_range.observe(
            lambda change: self.on_single_or_date_range_change(change, glofas_option=glofas_option),
            names='value'
        )

        self.no_data_helper_checklist = widgets.Checkbox(value=True, description='No-Data Helper Function',
                                                         tooltip="Due to GloFas API framework, some versions and/or "
                                                                 "models aren't available for certain dates. If enabled,"
                                                                 "This will allow the program to automatically alter the version date and "
                                                                 "hydrological model to find a matching dataset.")

        self.system_version.layout.width = 'auto'
        # self.date_picker.layout.width = 'auto'

        self.add_image_to_map = widgets.Checkbox(description='Add Image to Map', value=True)

        self.create_sub_folder = widgets.Checkbox(description='Create Sub-folder', value=True)
        self.clip_to_geometry = widgets.Checkbox(
            value=True,
            description='Clip Image to Geometry Bounds',
            disabled=False,
            indent=False
        )
        self.filechooser = fc.FileChooser(os.getcwd(), show_only_dirs=True)

        self.glofas_end_of_vbox_items = widgets.Accordion([
            widgets.TwoByTwoLayout(
                top_left=self.add_image_to_map, top_right=self.no_data_helper_checklist,
                bottom_left=self.create_sub_folder, bottom_right=self.clip_to_geometry
            )
        ])

        self.glofas_end_of_vbox_items.set_title(0, 'Options')

        # Return a list of widgets
        if glofas_option == 'cems-glofas-seasonal':
            return [self.system_version, self.hydrological_model, self.leadtime, self.single_or_date_range,
                    self.glofas_date_vbox, self.filechooser, self.glofas_end_of_vbox_items]
        else:
            return [self.system_version, self.hydrological_model, self.product_type, self.leadtime,
                    self.single_or_date_range,
                    self.glofas_date_vbox, self.filechooser, self.glofas_end_of_vbox_items]

    def get_available_dates(self, glofas_option):
        """Generate a list of available dates based on the selected GloFas option."""
        min_year = min(self.glofas_dict['products'][glofas_option]['year'])
        max_year = max(self.glofas_dict['products'][glofas_option]['year'])
        min_month = 1  # Assuming January is always included
        max_month = 12  # Assuming December is always included
        min_day = 1

        available_dates = []
        for year in range(min_year, max_year + 1):
            for month in range(min_month, max_month + 1):
                for day in range(min_day, self.get_last_day_of_month(year, month).day + 1):
                    if datetime.date(year, month, day) >= datetime.date.today():
                        break
                    available_dates.append(datetime.date(year, month, day))

        return available_dates

    def update_date_dropdown(self, glofas_option):
        """Update the date dropdown with available dates based on the selected GloFas option."""
        available_dates = self.get_available_dates(glofas_option)
        formatted_date_options = [(date.strftime('%Y-%m-%d'), date) for date in available_dates]
        return formatted_date_options

    def on_single_or_date_range_change(self, change, glofas_option: str):
        """
        Handles the change event when the option for single date or date range is changed.

        :param change: A dictionary containing information about the change event.
        :param glofas_option: The selected Glofas option.
        :return: None

        """

        single_or_date_range_value = change['new']

        options = self.update_date_dropdown(glofas_option)

        if single_or_date_range_value == 'Single Date':
            # Create the DatePicker widget with constraints

            self.date_picker = widgets.Dropdown(
                options=options,
                description='Select Date:',
                disabled=False,
            )

            self.glofas_date_vbox.children = [self.date_picker]

        else:
            # Create the DatePicker widgets with constraints
            self.date_picker = HBox([
                widgets.Dropdown(
                    options=options,
                    description='Select Start Date:',
                    disabled=False
                ),

                widgets.Dropdown(
                    options=options,
                    description='Select End Date:',
                    disabled=False
                )])

            self.glofas_date_vbox.children = [self.date_picker]


    def update_max_date(self, year, month):
        """
        Update the maximum date of the DatePicker when the year or month changes.

        :param year: The selected year.
        :param month: The selected month.
        """
        max_date = self.get_last_day_of_month(year, month)
        self.date_picker.max = max_date

    def get_last_day_of_month(self, year, month):
        """
        Get the last day of the given month and year.

        :param year: The year
        :param month: The month
        :return: The date of the last day of the given month and year.
        """
        next_month = month % 12 + 1
        next_month_first_day = datetime.date(year if next_month != 1 else year + 1, next_month, 1)
        last_day_of_month = next_month_first_day - datetime.timedelta(days=1)
        return last_day_of_month

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

        specific_widgets = self.create_widgets_for_glofas(glofas_value)

        # Replace the children of the glofas_stack with the specific widgets
        self.glofas_stack.children = tuple(specific_widgets)

        # else:
        #     # If the selected GloFAS product is not recognized, clear the glofas_stack
        #     self.glofas_stack.children = ()

    def download_glofas_data(self, bbox, params, index, distinct_values=None):
        """
        :param bbox: The bounding box of the area to download Glofas data for.
        :param glofas_params: The parameters for downloading Glofas data.
        :param index: The index of the Glofas data.
        :param distinct_values: The distinct values for the Glofas data (optional).
        :return: The file path of the downloaded Glofas data.
        """

        request_parameters = {
            'glofas_product': params.get('glofas_product'),
            'variable': 'river_discharge_in_the_last_24_hours',
            'format': 'grib',
            'system_version': params.get('system_version'),
            'hydrological_model': params.get('hydrological_model'),
            'product_type': params.get('product_type', 'ensemble_perturbed_forecasts'),
            'year': params.get('year'),
            'month': params.get('month'),
            # Omit 'day' to use the default value or provide a specific day
            'day': params.get('day', '01'),
            'leadtime_hour': params.get('leadtime_hour'),
            'area': [bbox['maxy'][0], bbox['minx'][0], bbox['miny'][0], bbox['maxx'][0]],
            'folder_location': params.get('folder_location'),
        }

        # Construct file name based on the parameters
        file_name = f"{params['glofas_product']}_{'userdefined' if distinct_values is None else '_'.join(str(value) for value in distinct_values)}_{index}_{params.get('year')}_{params.get('month')}_{request_parameters.get('day', '01')}.grib"

        # Download data and return the file path
        return self.download_data(params['glofas_product'], request_parameters, file_name)

    def gather_parameters(self, glofas_product: str):
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
            year = str(start_date.year)
            month = int(start_date.month)
            day = str(start_date.day)
        folder_location = self.filechooser.selected
        create_sub_folder = self.create_sub_folder.value
        clip_to_geometry = self.clip_to_geometry.value
        add_image_to_map = self.add_image_to_map.value
        no_data_helper = self.no_data_helper_checklist.value

        if glofas_product == 'cems-glofas-seasonal':

            return {
                'glofas_product': glofas_product,
                'system_version': system_version,
                'hydrological_model': hydrological_model,
                'leadtime_hour': leadtime_hour,
                'year': year,
                'month': month,
                'day': day,
                'folder_location': folder_location,
                'create_sub_folder': create_sub_folder,
                'clip_to_geometry': clip_to_geometry,
                'add_image_to_map': add_image_to_map,
                'no_data_helper': no_data_helper
            }
        elif glofas_product == 'cems-glofas-forecast':

            return {
                'glofas_product': glofas_product,
                'system_version': system_version,
                'hydrological_model': hydrological_model,
                'product_type': product_type,
                'leadtime_hour': leadtime_hour,
                'year': year,
                'month': month,
                'day': day,
                'folder_location': folder_location,
                'create_sub_folder': create_sub_folder,
                'clip_to_geometry': clip_to_geometry,
                'add_image_to_map': add_image_to_map,
                'no_data_helper': no_data_helper
            }
        elif glofas_product == 'cems-glofas-reforecast':
            return {
                'glofas_product': glofas_product,
                'system_version': system_version,
                'hydrological_model': hydrological_model,
                'product_type': product_type,
                'leadtime_hour': leadtime_hour,
                'year': year,
                'month': month,
                'day': day,
                'folder_location': folder_location,
                'create_sub_folder': create_sub_folder,
                'clip_to_geometry': clip_to_geometry,
                'add_image_to_map': add_image_to_map,
                'no_data_helper': no_data_helper
            }
        else:
            print("Invalid GloFAS product.")
            return None

    def process_api(self, geometry, distinct_values, index, bbox, params, pbar=None):
        """
        Process the GLOFAS API data.
        """
        try:
            pbar.update(4)
            pbar.set_postfix_str("Downloading data...")

            if params['create_sub_folder']:
                # Create a sub-folder
                params['folder_location'] = self._create_sub_folder(params['folder_location'])



            params_file_path = os.path.join(params['folder_location'], 'parameters.json')



            with open(params_file_path, 'w') as f:
                json.dump(params, f)

            if self.single_or_date_range.value == "Date Range":
                try:

                    start_date = self.date_picker.children[0].value
                    end_date = self.date_picker.children[1].value

                    current_date = start_date
                    if isinstance(start_date, datetime.datetime):
                        start_date = start_date.date()
                    if isinstance(end_date, datetime.datetime):
                        end_date = end_date.date()
                    if isinstance(current_date, datetime.datetime):
                        current_date = current_date.date()

                    while current_date <= end_date:
                        params['year'] = str(current_date.year)
                        params['month'] = current_date.month
                        params['day'] = str(current_date.day)
                        file_path = self.download_glofas_data(bbox=bbox, params=params, index=index, distinct_values=distinct_values)
                        pbar.update(4)
                        pbar.set_postfix_str("Processing data...")
                        processed_raster = process_and_clip_raster(file_path, geometry, params, self.ee_instance)
                        current_date += datetime.timedelta(days=1)

                except Exception as e:
                    print(e)
                    if "no data is available within your requested subset" in str(e) and params['no_data_helper']:
                        return self.no_data_helper_function(bbox, params, geometry, index, distinct_values)
                    else:
                        print("An error occurred that couldn't be handled by the no data helper function.")
                        return None

            else:

                file_path = self.download_glofas_data(bbox=bbox, params=params, index=index, distinct_values=distinct_values)
                pbar.update(4)
                pbar.set_postfix_str("Processing data...")
                processed_raster = process_and_clip_raster(file_path, geometry, params, self.ee_instance)
            # Serialize the geometry to GeoJSON
            if isinstance(geometry, ee.Geometry):
                geojson_geometry = geometry.getInfo()  # If geometry is an Earth Engine object
            elif isinstance(geometry, ee.Feature):
                geojson_geometry = geometry.getInfo()
            elif isinstance(geometry, ee.FeatureCollection):
                geojson_geometry = geometry.getInfo()
            else:
                geojson_geometry = geometry  # If geometry is already in GeoJSON format

            # Define the GeoJSON filename
            geojson_filename = os.path.join(params['folder_location'], 'geometry.geojson')


            # Write the GeoJSON to a file
            with open(geojson_filename, 'w') as f:
                f.write(json.dumps(geojson_geometry))

            pbar.update(2)
            pbar.set_postfix_str("Finished!")

            return processed_raster

        except Exception as e:
            print(e)
            if "no data is available within your requested subset" in str(e) and params['no_data_helper']:
                return self.no_data_helper_function(bbox, params, geometry, index, distinct_values)
            else:
                print("An error occurred that couldn't be handled by the no data helper function.")
                return None

    def setup_global_variables(self):
        self.glofas_dict = {
            "products": {
                # 'cems-glofas-seasonal': {
                #     "system_version": ['operational', 'version_3_1', 'version_2_2'],
                #     'hydrological_model': ['lisflood'],
                #     "variable": "river_discharge_in_the_last_24_hours",
                #     "leadtime_hour": list(range(24, 5161, 24)),
                #     "year": list(range(2019, datetime.date.today().year + 1)),
                #     "month": ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
                #               "11", "12"],
                #     # "day": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                #     # "area": [10.95, -90.95, -30.95, -29.95],
                #     "format": "grib"
                # },
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
                # 'cems-glofas-reforecast': {
                #     "system_version": ['version_4_0', 'version_3_1', 'version_2_2'],
                #     'hydrological_model': ['lisflood', 'htessel_lisflood'],
                #     'product_type': [
                #         'control_forecast', 'ensemble_perturbed_forecasts',
                #     ],
                #     "leadtime_hour": list(range(24, 1105, 24)),
                #     "year": list(range(1999, datetime.date.today().year + 1)),
                #     "month": ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
                #               "11", "12"],
                #     "day": list(range(24, 32)),
                #     # "area": [10.95, -90.95, -30.95, -29.95],
                #     "format": "grib"
                # }
            }
        }







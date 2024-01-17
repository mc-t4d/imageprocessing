import datetime

import ipywidgets as widgets
from ipywidgets import DatePicker
from ipywidgets import VBox, HBox
import itertools

from mcimageprocessing.programmatic.APIs.GloFasAPI import CDSAPI


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
        options=['Single Date', 'Date Range'],
        disabled=False,
        value='Single Date',
        tooltips=['Single Date', 'Date Range'],
    )

    self.glofas_date_vbox = VBox([])
    self.on_single_or_date_range_change({'new': self.single_or_date_range.value}, glofas_option=glofas_option)

    self.single_or_date_range.observe(
        lambda change: self.on_single_or_date_range_change(change, glofas_option=glofas_option),
        names='value'
    )

    self.system_version.layout.width = 'auto'
    # self.date_picker.layout.width = 'auto'

    self.glofas_end_of_vbox_items = widgets.Accordion([
        widgets.TwoByTwoLayout(
            top_left=self.add_to_map_check, top_right=self.no_data_helper_checklist,
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

def download_glofas_data(self, bbox, glofas_params, index, distinct_values=None):
    """
    :param bbox: The bounding box of the area to download Glofas data for.
    :param glofas_params: The parameters for downloading Glofas data.
    :param index: The index of the Glofas data.
    :param distinct_values: The distinct values for the Glofas data (optional).
    :return: The file path of the downloaded Glofas data.

    """
    cds_api = CDSAPI()
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
    return cds_api.download_data(self.glofas_options.value, request_parameters, file_name)

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
    folder_location = self.filechooser.selected
    create_sub_folder = self.create_sub_folder.value
    clip_to_geometry = self.clip_to_geometry.value
    add_to_map = self.add_image_to_map.value
    no_data_helper = self.no_data_helper_checklist.value

    if glofas_product == 'cems-glofas-seasonal':

        return {
            'system_version': system_version,
            'hydrological_model': hydrological_model,
            'leadtime_hour': leadtime_hour,
            'year': year,
            'month': month,
            'day': day,
            'folder_location': folder_location,
            'create_sub_folder': create_sub_folder,
            'clip_to_geometry': clip_to_geometry,
            'add_to_map': add_to_map,
            'no_data_helper': no_data_helper
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
            'create_sub_folder': create_sub_folder,
            'clip_to_geometry': clip_to_geometry,
            'add_to_map': add_to_map,
            'no_data_helper': no_data_helper
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
            'create_sub_folder': create_sub_folder,
            'clip_to_geometry': clip_to_geometry,
            'add_to_map': add_to_map,
            'no_data_helper': no_data_helper
        }
    else:
        print("Invalid GloFAS product.")
        return None

def process_glofas_api(self, geometry, distinct_values, index):
    """
    Process the GLOFAS API data.

    :param geometry: The geometry object representing the area of interest.
    :type geometry: <Geometry type>

    :param distinct_values: The distinct values to filter the data.
    :type distinct_values: list

    :param index: The index value to select the data.
    :type index: int

    :return: None
    """
    with self.out:
        bbox = self.get_bounding_box(distinct_values, geometry)
        glofas_params = self.get_glofas_parameters(self.glofas_options.value)

        # Initially try to download data with the current parameters
        try:
            file_path = self.download_glofas_data(bbox, glofas_params, index, distinct_values)
            self.process_and_clip_raster(file_path, geometry, glofas_params)
            return  # If successful, exit the function here
        except Exception as e:

        # If the initial attempt fails, try other combinations
            if "no data is available within your requested subset" in str(e):
                if glofas_params['no_data_helper']:
                    system_version_list = self.glofas_dict['products'][self.glofas_options.value]['system_version']
                    hydrological_model_list = self.glofas_dict['products'][self.glofas_options.value]['hydrological_model']
                    product_type_list = self.glofas_dict['products'][self.glofas_options.value].get('product_type', [None])

                    # Generate all combinations
                    all_combinations = list(itertools.product(system_version_list, hydrological_model_list, product_type_list))

                    # Remove the last attempted combination
                    last_attempted_combination = (glofas_params['system_version'], glofas_params['hydrological_model'],
                                                  glofas_params['product_type'] if glofas_params.get('product_type') else None)
                    all_combinations.remove(last_attempted_combination)

                    # Try each remaining combination
                    for comb in all_combinations:
                        try:
                            glofas_params['system_version'], glofas_params['hydrological_model'], glofas_params['product_type'] = comb
                            file_path = self.download_glofas_data(bbox, glofas_params, index, distinct_values)
                            self.process_and_clip_raster(file_path, geometry, glofas_params)
                            return
                        except Exception as e:
                            print(e)
                            if "no data is available within your requested subset" not in str(e):
                                break  # Exit the loop if a different error occurs

            # Handle the case where no combination was successful
            print("No suitable data could be found for any combination.")






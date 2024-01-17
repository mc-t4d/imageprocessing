import ee
import geemap
import pkg_resources
from ipywidgets import Layout

from mcimageprocessing.programmatic.APIs.EarthEngine import EarthEngineManager
from mcimageprocessing.jupyter.widget_creation_components.glofas import *

ee_auth_path = pkg_resources.resource_filename('mcimageprocessing', 'ee_auth_file.json')

ee_instance = EarthEngineManager(authentication_file=ee_auth_path)

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
        self.out.clear_output()
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

    self.gee_bands_search_results.options = ee.ImageCollection(selected_layer).first().bandNames().getInfo()

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
            options=['Monthly', 'Yearly', 'All Images', 'One Aggregation'],
            disabled=False,
            value='Monthly',
            tooltips=['Monthly', 'Yearly', 'All Images', 'One Aggregation'],
        )

        aggregation_values = {
            'mode': lambda ic: ic.mode(),
            'median': lambda ic: ic.median(),
            'mean': lambda ic: ic.mean(),
            'max': lambda ic: ic.max(),
            'min': lambda ic: ic.min(),
            'sum': lambda ic: ic.reduce(ee.Reducer.sum()),
            'first': lambda ic: ic.sort('system:time_start', False).first(),
            'last': lambda ic: ic.sort('system:time_start', False).last(),
            # 'none': lambda ic: ic
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
        layout=Layout()
    )

    self.gee_layer_search_widget.layout.width = 'auto'

    self.search_button = widgets.Button(
        description='Search',
        disabled=False,
        button_style='',  # 'success', 'info', 'warning', 'danger' or ''
        tooltip='Click to search',
        icon='search'  # Icons names are available at https://fontawesome.com/icons
    )

    self.search_button.style.button_color = '#c8102e'
    self.search_button.style.text_color = 'white'

    self.search_button.on_click(self.on_gee_search_button_clicked)

    self.search_box = HBox([self.gee_layer_search_widget, self.search_button])

    self.gee_layer_search_results_dropdown = widgets.Dropdown(
        options=[],
        value=None,
        description='Results:',
        disabled=False,
        layout=Layout()
    )

    self.select_layer_gee = widgets.Button(
        description='Select',
        disabled=False,
        button_style='',  # 'success', 'info', 'warning', 'danger' or ''
        tooltip='Select Layer',
        icon='crosshairs'  # Icons names are available at https://fontawesome.com/icons
    )

    self.select_layer_gee.style.button_color = '#c8102e'
    self.select_layer_gee.style.text_color = 'white'


    self.select_layer_gee.on_click(self.on_gee_layer_selected)

    self.layer_select_box = HBox([self.gee_layer_search_results_dropdown, self.select_layer_gee])

    self.gee_bands_search_results = widgets.Dropdown(
        options=[],
        value=None,
        description='Bands:',
        disabled=False,
        layout=Layout()
    )

    self.single_or_range_dates = widgets.ToggleButtons(
        options=['Single Date', 'Date Range'],
        disabled=False,
        value='Date Range',
        tooltips=['Single Date', 'Date Range'],
    )

    self.single_or_range_dates.observe(self.on_single_or_range_dates_change, names='value')
    self.select_layer_gee.on_click(self.on_single_or_range_dates_change)

    self.gee_date_selection = widgets.VBox([])

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

    widget_list = [self.search_box, self.layer_select_box, self.gee_bands_search_results,
                   self.single_or_range_dates, self.gee_date_selection, self.scale_input, self.filechooser,
                   self.gee_end_of_container_options]

    for widget in widget_list:
        widget.layout.width = '100%'

    return widget_list

def process_gee_api(self, geometry, distinct_values, index):
    """
    :param geometry: The geometry to use for the GEE API request.
    :param distinct_values: Boolean indicating whether to return distinct values.
    :param index: The index to use for the GEE API request.
    :return: None
    """
    with self.out:
        gee_params = self.gather_gee_parameters()
        with self.out:
            self.out.clear_output()
            print(gee_params)
        geometry = self.ee_ensure_geometry(geometry)
        if gee_params['multi_date'] == False:
            img, region, gee_params['scale'] = ee_instance.get_image(**gee_params, geometry=geometry)
            url = ee_instance.get_image_download_url(img=img, region=region, scale=gee_params['scale'])
            file_name = 'gee_image.tif'
            ee_instance.download_file_from_url(url=url, destination_path=file_name)
            min_val, max_val, no_data_val = self.get_raster_min_max(file_name)
            if self.gee_bands_search_results.value.lower() in ['ndvi', 'evi']:
                palette = ['FFFFFF', 'CE7E45', 'DF923D', 'F1B555', 'FCD163', '99B718',
                           '74A901', '66A000', '529400', '3E8601', '207401', '056201',
                           '004C00', '023B01', '012E01', '011D01', '011301']
                vis_params = {
                    'min': 0,
                    'max': 10000,
                    'palette': palette,
                    'nodata': no_data_val
                }
            else:
                vis_params = {
                    'min': min_val,
                    'max': max_val,
                    'palette': 'viridis',
                    'nodata': no_data_val
                }
            self.addLayer(img, vis_params)
        else:
            if gee_params['aggregation_period'] == 'Monthly':
                monthly_date_ranges = ee_instance.generate_monthly_date_ranges(gee_params['start_date'],
                                                                               gee_params['end_date'])
                if gee_params['statistics_only']:
                    all_stats = ee.Dictionary()
                for dates in monthly_date_ranges:
                    if gee_params['statistics_only']:
                        image, geometry = ee_instance.get_image(multi_date=True,
                                                                aggregation_method=gee_params[
                                                                    'aggregation_method'],
                                                                geometry=geometry, start_date=dates[0],
                                                                end_date=dates[1],
                                                                band=gee_params['band'],
                                                                image_collection=gee_params[
                                                                    'image_collection'])
                        stats = ee_instance.calculate_statistics(image, geometry, gee_params[
                            'band'])  # This should be a server-side object
                        all_stats = all_stats.set(dates[0], stats)
                    else:
                        img, boundary = ee_instance.get_image(multi_date=True,
                                                              aggregation_method=gee_params[
                                                                  'aggregation_method'],
                                                              geometry=geometry, start_date=dates[0],
                                                              end_date=dates[1],
                                                              band=gee_params['band'],
                                                              image_collection=gee_params[
                                                                  'image_collection'])
                        url = ee_instance.get_image_download_url(img=img, region=boundary,
                                                                 scale=gee_params['scale'])
                        file_name = f"{gee_params['image_collection']}_{dates[0]}_{dates[1]}_{gee_params['aggregation_method']}.tif".replace(
                            '-', '_').replace('/', '_').replace(' ', '_')
                        ee_instance.download_file_from_url(url=url, destination_path=file_name)
                        print(f"Downloaded {file_name}")
                if gee_params['statistics_only']:
                    all_stats_info = all_stats.getInfo()
                    with self.out:
                        self.out.clear_output()
                        print(all_stats_info)

            elif gee_params['aggregation_period'] == 'Yearly':
                yearly_date_ranges = ee_instance.generate_yearly_date_ranges(
                    gee_params['start_date'], gee_params['end_date'])
                if gee_params['statistics_only']:
                    all_stats = ee.Dictionary()
                for dates in yearly_date_ranges:
                    if gee_params['statistics_only']:
                        image, geometry = ee_instance.get_image(multi_date=True,
                                                                aggregation_method=gee_params[
                                                                    'aggregation_method'],
                                                                geometry=geometry, start_date=dates[0],
                                                                end_date=dates[1],
                                                                band=gee_params['band'],
                                                                image_collection=gee_params[
                                                                    'image_collection'])
                        stats = ee_instance.calculate_statistics(image, geometry, gee_params[
                            'band'])  # This should be a server-side object
                        all_stats = all_stats.set(dates[0], stats)

                    else:
                        img, boundary = ee_instance.get_image(multi_date=True,
                                                              aggregation_method=gee_params[
                                                                  'aggregation_method'],
                                                              geometry=geometry, start_date=dates[0],
                                                              end_date=dates[1],
                                                              band=gee_params['band'],
                                                              image_collection=gee_params[
                                                                  'image_collection'])
                        url = ee_instance.get_image_download_url(img=img, region=boundary,
                                                                 scale=gee_params['scale'])
                        file_name = f"{gee_params['image_collection']}_{dates[0]}_{dates[1]}_{gee_params['aggregation_method']}.tif".replace(
                            '-', '_').replace('/', '_').replace(' ', '_')
                        ee_instance.download_file_from_url(url=url, destination_path=file_name)
                        print(f"Downloaded {file_name}")
                if gee_params['statistics_only']:
                    all_stats_info = all_stats.getInfo()
                    with self.out:
                        print(all_stats_info)
            elif gee_params['aggregation_period'] == 'One Aggregation':
                img, boundary = ee_instance.get_image(multi_date=True,
                                                      aggregation_method=gee_params[
                                                          'aggregation_method'],
                                                      geometry=geometry,
                                                      start_date=str(gee_params['start_date']),
                                                      end_date=str(gee_params['end_date']),
                                                      band=gee_params['band'],
                                                      image_collection=gee_params[
                                                          'image_collection'])
                url = ee_instance.get_image_download_url(img=img, region=boundary,
                                                         scale=gee_params['scale'])

                file_name = f"{gee_params['image_collection']}_{str(gee_params['start_date'])}_{str(gee_params['end_date'])}_{gee_params['aggregation_method']}.tif".replace(
                    '-', '_').replace('/', '_').replace(' ', '_')
                ee_instance.download_file_from_url(url=url, destination_path=file_name)
                min_val, max_val, no_data_val = self.get_raster_min_max(file_name)
                if self.gee_bands_search_results.value.lower() in ['ndvi', 'evi']:
                    palette = ['FFFFFF', 'CE7E45', 'DF923D', 'F1B555', 'FCD163', '99B718',
                               '74A901', '66A000', '529400', '3E8601', '207401', '056201',
                               '004C00', '023B01', '012E01', '011D01', '011301']
                    vis_params = {
                        'min': 0,
                        'max': 10000,
                        'palette': palette,
                        'nodata': no_data_val
                    }
                else:
                    vis_params = {
                        'min': min_val,
                        'max': max_val,
                        'palette': 'viridis',
                        'nodata': no_data_val
                    }
                self.addLayer(img, vis_params)
                with self.out:
                    print(f"Downloaded {file_name}")

def gather_gee_parameters(self):
    """
    Retrieves the parameters required for querying and processing data from Google Earth Engine.

    :return: A dictionary containing the gathered parameters.
    """
    image_collection = self.gee_layer_search_results_dropdown.value
    date_type = self.single_or_range_dates.value
    band = self.gee_bands_search_results.value
    statistics_only = self.statistics_only_check.value
    if self.scale_input.value == 'default':
        scale = 'default'
    else:
        scale = int(self.scale_input.value)
    add_image_to_map = self.add_to_map_check.value
    create_sub_folder = self.create_sub_folder.value
    if date_type == 'Single Date':
        date = self.gee_single_date_selector.value
        self.add_to_map_check.value = True
        self.add_to_map_check.disabled = False
        return {
            'statistics_only': statistics_only,
            'image_collection': image_collection,
            'multi_date': False,
            'band': band,
            'date': date,
            'scale': scale,
            'create_sub_folder': create_sub_folder,
            'add_to_map': add_image_to_map,
        }
    elif date_type == 'Date Range':
        aggregation_period = self.gee_multi_date_aggregation_periods.value
        aggregation_method = self.gee_multi_date_aggregation_method.value
        start_date = self.gee_date_picker_start.value
        end_date = self.gee_date_picker_end.value
        band = self.gee_bands_search_results.value
        self.add_to_map_check.value = False
        self.add_to_map_check.disabled = True
        return {
            'statistics_only': statistics_only,
            'image_collection': image_collection,
            'multi_date': True,
            'aggregation_period': aggregation_period,
            'aggregation_method': aggregation_method,
            'start_date': start_date,
            'band': band,
            'end_date': end_date,
            'scale': scale,
            'create_sub_folder': create_sub_folder,
            'add_to_map': add_image_to_map,
        }
    else:
        pass

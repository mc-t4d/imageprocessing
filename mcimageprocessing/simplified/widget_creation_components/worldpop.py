import ipywidgets as widgets
from ipywidgets import HBox
from ipywidgets import Layout
import ee

def create_widgets_for_worldpop(self):
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
        # self.gee_layer_search_widget = widgets.Text(
        #     value='',
        #     placeholder='Search for a layer',
        #     description='Search:',
        #     disabled=False,
        #     layout=Layout()
        # )

        # self.gee_layer_search_widget.layout.width = 'auto'
        #
        # self.search_button = widgets.Button(
        #     description='Search',
        #     disabled=False,
        #     button_style='',  # 'success', 'info', 'warning', 'danger' or ''
        #     tooltip='Click to search',
        #     icon='search'  # Icons names are available at https://fontawesome.com/icons
        # )
        #
        # self.search_button.style.button_color = '#c8102e'
        # self.search_button.style.text_color = 'white'
        #
        # self.search_button.on_click(self.on_gee_search_button_clicked)
        #
        # self.search_box = HBox([self.gee_layer_search_widget, self.search_button])

        self.worldpop_data_source = widgets.ToggleButtons(
            options=['WorldPop API', 'Google Earth Engine'],
            disabled=False,
            value='Google Earth Engine',
            tooltips=['Obtain data directly from WorldPop API (more dynamic and more options)', 'Google Earth Engine (less functionality and optiosn, but potentially faster'],
        )

        self.worldpop_data_type = widgets.Dropdown(
            options=[x for x in ['Residential Population', 'Age and Sex Structures', ]],
            value=None,
            description='Results:',
            disabled=False,
            layout=Layout()
        )

        self.worldpop_year = widgets.Dropdown(
            options=[str(x) for x in range(2000, 2021, 5)],
            value="2020",
            description='Year:',
            disabled=False,
            layout=Layout()
        )

        #
        # self.select_layer_gee = widgets.Button(
        #     description='Select',
        #     disabled=False,
        #     button_style='',  # 'success', 'info', 'warning', 'danger' or ''
        #     tooltip='Select Layer',
        #     icon='crosshairs'  # Icons names are available at https://fontawesome.com/icons
        # )
        #
        # self.select_layer_gee.style.button_color = '#c8102e'
        # self.select_layer_gee.style.text_color = 'white'
        #
        #
        # self.select_layer_gee.on_click(self.on_gee_layer_selected)
        #
        # self.layer_select_box = HBox([self.gee_layer_search_results_dropdown, self.select_layer_gee])
        #
        # self.gee_bands_search_results = widgets.Dropdown(
        #     options=[],
        #     value=None,
        #     description='Bands:',
        #     disabled=False,
        #     layout=Layout()
        # )
        #
        # self.single_or_range_dates = widgets.ToggleButtons(
        #     options=['Single Date', 'Date Range'],
        #     disabled=False,
        #     value='Date Range',
        #     tooltips=['Single Date', 'Date Range'],
        # )
        #
        # self.single_or_range_dates.observe(self.on_single_or_range_dates_change, names='value')
        # self.select_layer_gee.on_click(self.on_single_or_range_dates_change)
        #
        # self.gee_date_selection = widgets.VBox([])

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
            # self.search_box,
            # self.layer_select_box,
            # self.gee_bands_search_results,
            # self.single_or_range_dates,
            # self.gee_date_selection,
            self.scale_input,
            self.filechooser,
            self.gee_end_of_container_options
        ]

        for widget in widget_list:
            widget.layout.width = '100%'

        return widget_list

def gather_worldpop_parameters(self):
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

    datatype=self.worldpop_data_type

    # statistics_only = self.statistics_only_check.value
    # if self.scale_input.value == 'default':
    #     scale = 'default'
    # else:
    #     scale = int(self.scale_input.value)
    # add_image_to_map = self.add_to_map_check.value
    # create_sub_folder = self.create_sub_folder.value
    # if date_type == 'Single Date':
    # date = self.gee_single_date_selector.value
    # self.add_to_map_check.value = True
    # self.add_to_map_check.disabled = False
    return {
        'api_source': self.worldpop_data_source.value,
        'year': self.worldpop_year.value,
        'datatype': self.worldpop_data_type,
        'statistics_only': self.statistics_only_check,
        'add_image_to_map': self.add_image_to_map,
        'create_sub_folder': self.create_sub_folder,
        'folder_output': self.filechooser,
    }
    # elif date_type == 'Date Range':
    #     aggregation_period = self.gee_multi_date_aggregation_periods.value
    #     aggregation_method = self.gee_multi_date_aggregation_method.value
    #     start_date = self.gee_date_picker_start.value
    #     end_date = self.gee_date_picker_end.value
    #     band = self.gee_bands_search_results.value
    #     self.add_to_map_check.value = False
    #     self.add_to_map_check.disabled = True
    #     return {
    #         'statistics_only': statistics_only,
    #         'image_collection': image_collection,
    #         'multi_date': True,
    #         'aggregation_period': aggregation_period,
    #         'aggregation_method': aggregation_method,
    #         'start_date': start_date,
    #         'band': band,
    #         'end_date': end_date,
    #         'scale': scale,
    #         'create_sub_folder': create_sub_folder,
    #         'add_to_map': add_image_to_map,
    #     }
    # else:
    #     pass

def process_worldpop_api(self, geometry, distinct_values, index):
    """
    Method to process WorldPop API data for given parameters.

    :param self: The instance of the class.
    :param geometry: The geometry to process.
    :param distinct_values: The distinct values to filter.
    :param index: The index of the image.
    :return: None
    """
    with self.out:
        worldpop_params = self.gather_worldpop_parameters()
        if self.boundary_type.value == 'User Defined':
            geometries = self.determine_geometries_to_process('User Defined')
            geometry = geometries[0][0].geometry()
            countries = ee.FeatureCollection(f"FAO/GAUL_SIMPLIFIED_500m/2015/level0")
            bounding = geometry.bounds()
            filtered_layer = countries.filterBounds(bounding)
            distinct_countries = filtered_layer.aggregate_array(self.column).distinct().getInfo()
            distinct_values = list(set(distinct_countries))
        elif self.boundary_type.value == 'Predefined Boundaries':
            geometries = self.determine_geometries_to_process()
            geometry = geometries[0]
            countries = ee.FeatureCollection(f"FAO/GAUL_SIMPLIFIED_500m/2015/level0")
            bounding = geometry.bounds()
            filtered_layer = countries.filterBounds(bounding)
            distinct_countries = filtered_layer.aggregate_array('ADM0_NAME').distinct().getInfo()
            distinct_values = list(set(distinct_countries))
            print(distinct_values)

        images = []
        for country in distinct_values:
            image = ee.Image(f"WorldPop/GP/100m/pop/{self.gaul_dictionary[country]['ISO3']}_{worldpop_params['year']}")
            images.append(image)
        mergedImage = ee.ImageCollection(images).mosaic()
        if self.boundary_type.value == 'User Defined':
            geometries2 = self.determine_geometries_to_process('User Defined')
            mergedImage = mergedImage.clip(geometries2[0][0])
        if worldpop_params['add_image_to_map']:
            self.add_ee_layer(mergedImage, {}, 'WorldPop')

import ipywidgets as widgets
from ipywidgets import HBox
from ipywidgets import Layout


def create_widgets_for_global_flood_db(self):
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
        self.search_box,
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

import calendar
import datetime
import json
import os
import re
from typing import ClassVar

import ee
import geemap
import ipyfilechooser as fc
import ipywidgets as widgets
import requests
from ipywidgets import Layout
from pydantic import BaseModel, Extra
from pydantic import root_validator
from shapely.geometry import shape

from mcimageprocessing import config_manager


class EarthEngineManager(BaseModel):
    """
    EarthEngineManager class for managing Earth Engine operations.
    """

    year_ranges: list = []

    aggregation_functions: dict = None

    vis_params: ClassVar[dict] = {'NDVI': {'min': 0, 'max': 1,
                                           'palette': ['FFFFFF', 'CE7E45', 'DF923D', 'F1B555', 'FCD163', '99B718',
                                                       '74A901', '66A000', '529400', '3E8601', '207401', '056201',
                                                       '004C00', '023B01', '012E01', '011D01', '011301']}}
    ee_dates: list = []

    @root_validator(pre=True)
    def set_aggregation_functions(cls, values):
        """Set the aggregation functions for the class.

        :param values: A dictionary specifying the aggregation functions.
            The dictionary keys are the names of the aggregation functions,
            and the values are lambda functions that execute the desired aggregation.
            Supported aggregation functions:
                - 'mode': Mode of the input values.
                - 'median': Median of the input values.
                - 'mean': Mean of the input values.
                - 'max': Maximum value of the input values.
                - 'min': Minimum value of the input values.
                - 'sum': Sum of the input values.
                - 'first': The first value of the input collection after sorting
                  by 'system:time_start' in descending order.
        :type values: dict

        :return: The same input dictionary `values`.
        :rtype: dict
        """
        cls.aggregation_functions = {
            'mode': lambda ic: ic.mode(),
            'median': lambda ic: ic.median(),
            'mean': lambda ic: ic.mean(),
            'max': lambda ic: ic.max(),
            'min': lambda ic: ic.min(),
            'sum': lambda ic: ic.reduce(ee.Reducer.sum()),
            'first': lambda ic: ic.sort('system:time_start', False).first(),
            # 'last': lambda ic: ic.sort('system:time_start', False).last()
        }
        return values

    @root_validator(pre=True)
    def set_vis_params(cls, values):
        """

        """
        values["vis_params"] = {'NDVI': {'min': 0, 'max': 1,
                                         'palette': ['FFFFFF', 'CE7E45', 'DF923D', 'F1B555', 'FCD163', '99B718',
                                                     '74A901', '66A000', '529400', '3E8601', '207401', '056201',
                                                     '004C00', '023B01', '012E01', '011D01', '011301']}}
        return values

    def load_credentials(cls, v):
        """
        Initialize Earth Engine credentials using the provided ServiceAccountCredentials.

        :param cls: The class object.
        :param v: The value to be returned.
        :return: The value passed as 'v'.
        """

        # Initialize Earth Engine credentials
        credentials = ee.ServiceAccountCredentials(
            email=config_manager.config['KEYS']['GEE']['client_email'],
            key_data=config_manager.config['KEYS']['GEE']['private_key']
        )

        ee.Initialize(credentials)
        return v


    @classmethod
    def validate_aggregation_function(cls, function):
        """

        :param function: The aggregation function to validate.
        :return: The validated aggregation function.

        """
        if function not in cls.aggregation_functions:
            raise ValueError(
                f"Invalid aggregation function: {function}. Must be one of: {', '.join(cls.aggregation_functions.keys())}")
        return function

    def generate_monthly_date_ranges(self, start_date, end_date):
        """
        :param start_date: The start date of the date ranges to generate. Should be a datetime.date object.
        :param end_date: The end date of the date ranges to generate. Should be a datetime.date object.
        :return: A list of tuples, where each tuple represents a monthly date range. Each tuple contains the start date and end date of the respective month.

        """
        date_ranges = []

        for year in range(start_date.year, end_date.year + 1):
            for month in range(1, 13):
                # Skip months before the start month in the start year
                if year == start_date.year and month < start_date.month:
                    continue
                # Stop if the month is after the end month in the end year
                if year == end_date.year and month > end_date.month:
                    break
                # Get the last day of the month
                last_day = calendar.monthrange(year, month)[1]
                # Format the start and end dates of the month
                month_start_date = datetime.date(year, month, 1).strftime('%Y-%m-%d')
                month_end_date = datetime.date(year, month, last_day).strftime('%Y-%m-%d')
                # Append the tuple of the start and end date of the month to the list
                date_ranges.append((month_start_date, month_end_date))

        return date_ranges

    def generate_yearly_date_ranges(self, start_date, end_date):
        """
        :param start_date: The start date of the date range.
        :param end_date: The end date of the date range.
        :return: A list of tuples, where each tuple represents the start and end dates for each year within the specified range.

        """
        # Convert start and end dates from strings to date objects
        # start_date_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        # end_date_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d')

        # Check if end_date is supplied and valid
        if not end_date or end_date < start_date:
            raise ValueError("The end date must be provided and must be after the start date.")

        date_ranges = []

        for year in range(start_date.year, end_date.year + 1):
            # Determine the start of the year
            if year == start_date.year:
                year_start_date = start_date
            else:
                year_start_date = datetime.date(year, 1, 1)

            # Determine the end of the year
            if year == end_date.year:
                year_end_date = end_date
            else:
                year_end_date = datetime.date(year, 12, 31)

            # Format the start and end dates of the year
            year_start_date_str = year_start_date.strftime('%Y-%m-%d')
            year_end_date_str = year_end_date.strftime('%Y-%m-%d')

            # Append the tuple of the start and end date of the year to the list
            date_ranges.append((year_start_date_str, year_end_date_str))

        return date_ranges

    def get_image_collection_dates(self, collection: str, min_max_only: bool = False):
        """
        :param collection: The name of the image collection to retrieve dates from. It should be in the format 'path/to/collection'.
        :param min_max_only: A boolean value indicating whether to only return the minimum and maximum dates in the collection. Default is False.
        :return: A list of dates in the image collection. If `min_max_only` is True, it will return a list with two dates, representing the minimum and maximum dates in the collection. Otherwise
        *, it will return a list of all dates in the collection.

        """
        # Regular expression to match both formats
        pattern = r'^[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+){1,2}$'

        def format_dates(img):
            original_date = ee.Date(img.get('system:time_start'))
            current_day = original_date.format('YYYY-MM-dd')
            return ee.Feature(None, {'current_date': current_day})

        def get_min_max_dates(collection):
            # Get the minimum date in the collection.
            min_date = ee.Date(collection.aggregate_min('system:time_start')).format('YYYY-MM-dd')
            # Get the maximum date in the collection.
            max_date = ee.Date(collection.aggregate_max('system:time_start')).format('YYYY-MM-dd')

            min_date = min_date.getInfo()

            max_date = max_date.getInfo()

            return [min_date, max_date]

        collection = ee.ImageCollection(collection)
        if min_max_only:
            return get_min_max_dates(collection)
        else:
            formatted_dates = collection.map(format_dates)
            current_date_list = formatted_dates.aggregate_array('current_date')
            ee_date_list = current_date_list.getInfo()
            self.ee_dates = [x for x in ee_date_list]
            return self.ee_dates


    def calculate_statistics(self, img, geometry, band):
        """
        :param img: The image on which to calculate the statistics.
        :param geometry: The geometry within which to calculate the statistics.
        :param band: The band of the image on which to calculate the statistics.
        :return: The calculated statistics as a dictionary.

        This method calculates various statistics for a given image within a specified geometry and band. It uses the Earth Engine reducers to calculate mean, sum, maximum, minimum, standard
        * deviation, variance, and median.

        The `img` parameter is the image object on which the statistics are calculated.
        The `geometry` parameter is the geometry object that defines the region within which the statistics are calculated.
        The `band` parameter is the name of the band on which the statistics are calculated.

        The method returns the calculated statistics as a dictionary. The keys of the dictionary represent the statistic types ('mean', 'sum', 'max', 'min', 'stdDev', 'variance', 'median') and
        * the values represent the computed statistics for each type.
        """
        # Define the reducers for each statistic you want to calculate
        reducers = ee.Reducer.mean().combine(
            reducer2=ee.Reducer.sum(),
            sharedInputs=True
        ).combine(
            reducer2=ee.Reducer.max(),
            sharedInputs=True
        ).combine(
            reducer2=ee.Reducer.min(),
            sharedInputs=True
        ).combine(
            reducer2=ee.Reducer.stdDev(),
            sharedInputs=True
        ).combine(
            reducer2=ee.Reducer.variance(),
            sharedInputs=True
        ).combine(
            reducer2=ee.Reducer.median(),
            sharedInputs=True
        )

        # Apply the reducers to the image
        stats = img.reduceRegion(reducer=reducers, geometry=geometry, maxPixels=1e12)
        return stats

    def get_image(self,
                  multi_date: bool,
                  aggregation_period: str=None,
                  aggregation_method: str=None,
                  start_date:str=None,
                  end_date:str=None,
                    date:str=None,
                  create_sub_folder=None,
                  scale=None,
                  image_collection:str=None,
                  add_to_map:bool=None,
                  band:str=None,
                  additional_filter=False,
                  filter_argument=None,
                  geometry=None,
                  statistics_only=False
                  ):
        """
        :param multi_date: Boolean indicating whether multiple dates will be used for aggregation
        :param aggregation_period: String indicating the period over which to aggregate the images
        :param aggregation_method: String indicating the method of aggregation to be used
        :param start_date: String indicating the start date of the image collection
        :param end_date: String indicating the end date of the image collection
        :param date: String indicating the date for which to retrieve the image
        :param create_sub_folder: Boolean indicating whether to create a subfolder for the downloaded image
        :param scale: Scale at which to retrieve the image. Default is None.
        :param image_collection: String indicating the Earth Engine image collection to use
        :param add_to_map: Boolean indicating whether to add the retrieved image to the map
        :param band: String indicating the band to retrieve from the image collection
        :param additional_filter: Boolean indicating whether to apply an additional filter to the image collection
        :param filter_argument: Argument to be used for additional filtering. Default is None.
        :param geometry: Geometry object representing the region of interest
        :param statistics_only: Boolean indicating whether to only return additional statistics about the image
        :return: Tuple containing the retrieved image, the boundary of the region, and the nominal scale of the image
        """

        if multi_date:
            self.__class__.validate_aggregation_function(aggregation_method)

            img_function = EarthEngineManager.aggregation_functions.get(aggregation_method)
            if img_function is None:
                raise ValueError(f"Invalid aggregation function: {aggregation_method}")



            boundary = geometry

            img_collection = ee.ImageCollection(image_collection).filter(
                ee.Filter.date(start_date, end_date)).select(band).filter(ee.Filter.bounds(geometry))

            ee_img_scale = img_collection.first().projection().nominalScale().getInfo()

            mask = ee.Image.constant(1).clip(geometry)

            img = self.__class__.aggregation_functions[aggregation_method](img_collection).clip(boundary)


            # Step 1: Mask where value is not -9999
            valid_pixels = img.neq(-9999)

            # Step 2: Combine valid_pixels mask with nigeria_mask
            combined_mask = valid_pixels.And(mask)

            # Step 3: Use the combined mask to mask the aggregated image
            img_masked = img.updateMask(combined_mask)

            nodata_value = 0
            img = img_masked.unmask(nodata_value)

            return img, boundary, ee_img_scale
        else:

            if isinstance(geometry, ee.Feature):
                geometry = geometry.geometry()
            elif isinstance(geometry, ee.Geometry):
                geometry = geometry
            else:
                raise ValueError("The region must be a Feature or Geometry.")

            img_collection = ee.ImageCollection(image_collection).filterDate(ee.Date(date)).select(band).filter(ee.Filter.bounds(geometry))

            ee_img_scale = img_collection.first().projection().nominalScale().getInfo()

            mask = ee.Image.constant(1).clip(geometry)

            img = img_collection.first().clip(geometry)


            # Step 1: Mask where value is not -9999
            valid_pixels = img.neq(-9999)

            # Step 2: Combine valid_pixels mask with nigeria_mask
            combined_mask = valid_pixels.And(mask)

            # Step 3: Use the combined mask to mask the aggregated image
            img_masked = img.updateMask(combined_mask)

            nodata_value = 0
            img = img_masked.unmask(nodata_value)

            return img, geometry, ee_img_scale

    def split_and_sort_geometry(self, geometry, num_sections):
        """
        :param geometry: The geometry to be split and sorted.
        :param num_sections: The number of sections to split the geometry into.
        :return: A list of sorted grid cells obtained by splitting the geometry.

        This method takes a geometry and splits it into a grid of specified number of sections. The grid cells are then sorted based on their area in descending order.

        Example usage:
        ```
        geometry = ee.Geometry.Polygon(<coordinates>)
        num_sections = 4

        sorted_grid = split_and_sort_geometry(geometry, num_sections)
        ```
        """
        bounds = geometry.bounds()
        coords = bounds.getInfo()['coordinates'][0]
        min_x, max_x = min(coords, key=lambda x: x[0])[0], max(coords, key=lambda x: x[0])[0]
        min_y, max_y = min(coords, key=lambda x: x[1])[1], max(coords, key=lambda x: x[1])[1]

        # Calculate dimensions for the grid
        num_rows = num_cols = int(num_sections ** 0.5)
        x_step = (max_x - min_x) / num_cols
        y_step = (max_y - min_y) / num_rows

        grid = []
        for i in range(num_cols):
            for j in range(num_rows):
                x_start = min_x + i * x_step
                y_start = min_y + j * y_step
                cell = ee.Geometry.Rectangle([x_start, y_start, x_start + x_step, y_start + y_step])
                intersected_cell = cell.intersection(geometry, ee.ErrorMargin(x_step))
                grid.append(intersected_cell)

        # Sort the grid cells by area, largest first
        sorted_grid = sorted(grid, key=lambda g: g.area().getInfo(), reverse=True)

        return sorted_grid

    def get_image_download_url(self, region, scale, img, format='GEO_TIFF', crs='EPSG:4326'):
        """
        :param region: The region of interest for the image download. It can be either an ee.Feature or ee.Geometry object.
        :param scale: The scale of the image. It can be either a numerical value or 'default' to use the default scale of the image.
        :param img: The image to download.
        :param format: The format of the downloaded image. Default is 'GEO_TIFF'.
        :param crs: The coordinate reference system of the downloaded image. Default is 'EPSG:4326'.
        :return: The download URL for the image.

        This method takes in a region of interest, scale, image, format, and coordinate reference system (CRS) as parameters and returns the URL to download the image. The region can be specified
        * as an ee.Feature or ee.Geometry object. The scale can be provided as a numerical value or 'default' to use the default scale of the image. The format parameter determines the format
        * in which the image will be downloaded, with the default being 'GEO_TIFF'. The crs parameter specifies the CRS of the downloaded image, with the default being 'EPSG:4326'.
        """
        if isinstance(region, ee.Feature):
            geometry = region.geometry()
        elif isinstance(region, ee.Geometry):
            geometry = region
        else:
            raise ValueError("The region must be a Feature or Geometry.")

        if scale == 'default':
            scale = img.projection().nominalScale().getInfo()
        else:
            pass


        return img.getDownloadURL({
            'region': geometry,
            'scale': scale,
            'crs': crs,
            'format': format
        })

    @staticmethod
    def download_file_from_url(url, destination_path):
        """Download a file from the given URL.

        :param url: The URL of the file to be downloaded.
        :param destination_path: The path where the downloaded file will be saved.
        :return: None
        """
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(destination_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

    def img_min_max(self, img, scale, min_threshold=None, boundary=None, band=None):
        """
        :param img: The input image
        :param scale: The scale at which to compute the min and max values
        :param min_threshold: An optional threshold to exclude values below
        :param boundary: An optional geometry to limit the computation to a specific area
        :param band: The band to compute the min and max values for
        :return: The minimum and maximum values of the specified band as a tuple (min_value, max_value)
        """
        max_pixels = 1e12

        # If a threshold is provided, mask the image to exclude values below the threshold
        if min_threshold is not None:
            img = img.updateMask(img.gte(min_threshold))

        stats = img.reduceRegion(
            reducer=ee.Reducer.minMax(),
            bestEffort=True,
            scale=scale,
            geometry=boundary,  # Add this line
            maxPixels=max_pixels
        ).getInfo()

        min_value = stats[f"{band}_min"]
        max_value = stats[f"{band}_max"]

        return min_value, max_value

    def plot_image(self, img, vis_params):
        """
        Plot an image on a geemap.Map object.

        :param img: The image to be plotted.
        :param vis_params: The visualization parameters for the image.
        :return: The geemap.Map object with the image plotted.
        """
        center_lat = 2
        center_lon = 32
        zoomlevel = 6
        map = geemap.Map(center=[center_lat, center_lon], zoom=zoomlevel)
        map.addLayer(img, vis_params=vis_params)
        map.addLayerControl()
        return map

    def process_images(self, start_date, end_date, image_collection, band, country, aggregation_type, function):
        """
        Process images within a specified date range.

        :param start_date: The start date of the date range.
        :param end_date: The end date of the date range.
        :param image_collection: The collection of images to process.
        :param band: The desired band of the images.
        :param country: The country for which to process the images.
        :param aggregation_type: The type of aggregation for the images (either "monthly" or "yearly").
        :param function: The function to apply to the images.
        :return: None
        """
        # Validate aggregation type
        if aggregation_type.lower() not in ("monthly", "yearly"):
            raise ValueError('Aggregation type should be either "monthly" or "yearly".')

        # Generate date ranges
        if aggregation_type.lower() == "monthly":
            date_ranges = self.generate_monthly_date_ranges(int(start_date[:4]))
        else:
            date_ranges = self.generate_yearly_date_ranges(int(start_date[:4]))

        for start, end in date_ranges:
            start = datetime.datetime.strptime(start, "%Y-%m-%d").date()
            end = datetime.datetime.strptime(end, "%Y-%m-%d").date()

            # If the date range is within the specified start date and end date
            if start >= datetime.datetime.strptime(start_date, "%Y-%m-%d").date() and end <= datetime.datetime.strptime(end_date,
                                                                                                      "%Y-%m-%d").date():
                print(f"Processing images from {start} to {end}...")

                # Proceed to fetch and process image
                img, boundary = self.get_image(function, str(start), str(end), image_collection, band, country=country)

                # Generate download URL
                download_url = self.get_image_download_url(boundary, 1000, img)

                # Prompt the download URL
                print("Download URL: ", download_url)

                # Download the image
                destination_path = f"{band}_{start}_{end}.tif"
                self.download_file_from_url(download_url, destination_path)

    def get_admin_units(self, level=0):
        """
        :param level: An integer representing the administrative level. Default is 0.
        :return: A list of unique administrative units at the specified level.

        This method retrieves administrative units from a dataset based on the specified level. The dataset used is FAO/GAUL_SIMPLIFIED_500m/2015, which contains administrative boundary information
        *. The parameter 'level' specifies the desired administrative level.

        If level is 0, the method returns a sorted list of unique country names found in the dataset.

        If level is 1 or 2, the method creates a dictionary where each key represents a higher-level unit and its value is a list of lower-level units. The dictionary is returned as a Python
        * dictionary.

        Note: This method utilizes the Earth Engine API to interact with geospatial data.

        Example usage:
            my_object = MyClass()
            result = my_object.get_admin_units(level=1)

            # Result may look like:
            {
                'Country A': ['Region 1', 'Region 2'],
                'Country B': ['Region 3', 'Region 4'],
                ...
            }
        """
        # Load the dataset
        gaul_dataset = ee.FeatureCollection(f"FAO/GAUL_SIMPLIFIED_500m/2015/level{level}")

        if level == 0:
            unique_countries = gaul_dataset.aggregate_array('ADM0_NAME').distinct()
            return sorted(unique_countries.getInfo())

        elif level == 1 or level == 2:
            # Get the distinct higher-level units
            unique_higher_level_units = gaul_dataset.aggregate_array(f'ADM{level - 1}_NAME').distinct()

            # Create a FeatureCollection where each feature is a higher-level unit and its property is the list of lower-level units
            def process_higher_level_unit(current, prev):
                prev = ee.Dictionary(prev)
                current = ee.String(current)

                filtered_1 = gaul_dataset.filter(ee.Filter.eq(f'ADM{level - 1}_NAME', current))
                lower_level_units_1 = filtered_1.aggregate_array(f'ADM{level}_NAME').distinct()

                return prev.set(current, lower_level_units_1)

            admin_units_dict = ee.Dictionary(
                ee.List(unique_higher_level_units.iterate(process_higher_level_unit, ee.Dictionary({}))))

            return admin_units_dict.getInfo()


    def get_image_sum(self, img, geometry, scale, band='population'):
        """
        :param img: The input image to calculate the sum.
        :param geometry: The geometry to apply the calculation to.
        :param scale: The scale to use for calculation.
        :param band: The band to calculate the sum for. Defaults to 'population'.
        :return: The sum value calculated for the specified band.
        """
        # Define the reducers for each statistic you want to calculate

        reducers = ee.Reducer.sum()

        # Apply the reducers to the image
        stats = img.reduceRegion(reducer=reducers, geometry=geometry, scale=scale, maxPixels=1e12)

        sum_value = stats.get(band).getInfo()  # Make sure 'band' is the correct key

        return sum_value

    def ee_ensure_geometry(self, geometry):
        """
        :param geometry: The input geometry to ensure that it is a valid Earth Engine Geometry.
        :return: Return the valid Earth Engine Geometry.

        Ensures that the input `geometry` is a valid Earth Engine Geometry. If the `geometry` is an
        instance of `ee.Feature`, it extracts the geometry from the feature and returns it. If the
        `geometry` is already an instance of `ee.Geometry`, it returns it directly. If the `geometry`
        is an instance of `ee.FeatureCollection`, it dissolves it into its outer boundary and returns
        the dissolved geometry. If the `geometry` is a dictionary, it assumes that it is a GeoJSON
        geometry and converts it to an Earth Engine Geometry before ensuring its validity. If the
        `geometry` is of any other type, it raises a `ValueError` with a specific error message
        indicating that the geometry type must be an Earth Engine Geometry, Feature, or FeatureCollection.
        """

        if isinstance(geometry, ee.Feature):
            geometry = geometry.geometry()
            return geometry
        elif isinstance(geometry, ee.Geometry):
            return geometry
        elif isinstance(geometry, ee.FeatureCollection):
            # Dissolve the FeatureCollection into its outer boundary
            combined_geometry = geometry.geometry()
            dissolved_geometry = combined_geometry.dissolve(maxError=1)
            return dissolved_geometry
        elif isinstance(geometry, dict):
            # Assuming geojson is meant to be geometry (typo in the original code)
            return self.ee_ensure_geometry(self.convert_geojson_to_ee(geometry))
        else:
            raise ValueError("Invalid geometry type. Must be an Earth Engine Geometry, Feature, or FeatureCollection.")

    def convert_geojson_to_ee(self, geojson_obj):
        """
        Converts a GeoJSON object to Earth Engine objects.

        :param geojson_obj: The GeoJSON object to be converted.
        :return: The converted Earth Engine object.

        Raises:
            ValueError: If the GeoJSON type is not supported.
        """
        if geojson_obj['type'] == 'FeatureCollection':
            return ee.FeatureCollection(geojson_obj['features'])
        elif geojson_obj['type'] == 'Feature':
            geometry = geojson_obj['geometry']
            return ee.Feature(geometry)
        elif geojson_obj['type'] in ['Polygon', 'MultiPolygon', 'Point', 'LineString', 'MultiPoint', 'MultiLineString']:
            return ee.Geometry(geojson_obj)
        else:
            raise ValueError("Unsupported GeoJSON type")

    def process_drawn_features(self, drawn_features, layer, column):
        """
        :param drawn_features: A list of drawn features, each representing a geometry or a feature in Google Earth Engine.
        :param layer: An Earth Engine asset layer to filter and retrieve distinct values from.
        :param column: The column or property in the asset layer for which to retrieve distinct values.
        :return: A list of distinct values from the specified column"""
        all_distinct_values = []
        for feature in drawn_features:

            if isinstance(feature, ee.Feature) or isinstance(feature, ee.Geometry):
                drawn_geom = feature.geometry()
                bounding = drawn_geom.bounds()
                filtered_layer = layer.filterBounds(bounding)
                distinct_values = filtered_layer.aggregate_array(column).distinct().getInfo()
                all_distinct_values.extend(distinct_values)
        return list(set(all_distinct_values))

    def process_geometry_collection(self, geometry_collection, all_geometries):
        """
        Process a geometry collection and extract polygon and multipolygon geometries

        :param geometry_collection: The input geometry collection to be processed
        :param all_geometries: List to store the extracted geometries
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

    def download_feature_geometry(self, distinct_values, feature_type_prefix=None, column=None, layer=None, dropdown_api=None):
        """
        :param distinct_values: A list of distinct values used to filter the features.
        :param feature_type_prefix: Optional prefix for the feature type.
        :param column: Optional column used for filtering the features.
        :param layer: A layer object containing the features.
        :param dropdown_api: Optional dropdown API type.
        :return: The geometry of the features or None if no valid geometries are found.

        """
        if not distinct_values:
            print("No distinct values provided.")
            return

        if feature_type_prefix not in ['watersheds', 'admin']:
            print("Invalid feature type.")
            return

        all_geometries = []

        for value in distinct_values:
            feature = layer.filter(ee.Filter.eq(column, value)).first()
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

        if feature and dropdown_api in ['glofas', 'modis_nrt']:
            geometry = feature.geometry().getInfo()
            with open('geometry.geojson', "w") as file:
                json.dump(geometry, file)
            return geometry
        else:
            geometry = feature.geometry()
            return geometry

    def download_and_split(self, image, original_geometry, scale, split_count=1, params=None, band=None):
        """
        :param image: The image identifier.
        :param original_geometry: The original geometry of the image.
        :param scale: The scale of the image.
        :param split_count: The number of splits to divide the image into (default is 1).
        :param params: Additional parameters (default is None).
        :param band: The band of the image (default is None).
        :return: A list of file names and a boolean indicating if the download was successful.
        """
        file_names = []
        try:
            geom_list = self.split_and_sort_geometry(original_geometry, split_count)
            for index, geom in enumerate(geom_list):
                url = self.get_image_download_url(img=image, region=geom, scale=scale)
                file_name = f"{band}_{str(params['year'])}_{split_count}_{index}.tif".replace('-', '_').replace('/',
                                                                                                                '_').replace(
                    ' ', '_')
                file_name = os.path.join(params['folder_output'], file_name)
                self.download_file_from_url(url=url, destination_path=file_name)
                file_names.append(file_name)
            if split_count == 1 and len(file_names) == 1:
                # Download successful without splitting, no need to mosaic
                return file_names, True
        except Exception as e:
            if "Total request size" in str(e):
                print(f"Splitting geometry into {split_count * 2} parts and trying again.")
                # Increase split count and try again
                return self.download_and_split(image, original_geometry, scale, split_count * 2, params, band=band)
            else:
                print(f'Unexpected error: {e}')

        return file_names, False

    def ee_geometry_to_shapely(self, geometry):
        """
        Converts an Earth Engine Geometry or Feature, or a GeoJSON dictionary, to a Shapely Geometry.

        :param geometry: An Earth Engine Geometry or Feature, or a GeoJSON dictionary.
        :return: A Shapely Geometry object.

        Examples:
            # Convert an Earth Engine Geometry
            ee_geometry_to_shapely(ee_object)

            # Convert a GeoJSON dictionary
            geo_json = {
                "type": "Point",
                "coordinates": [0, 0]
            }
            ee_geometry_to_shapely(geo_json)
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

    def determine_geometries_to_process(self, override_boundary_type=None, layer=None, column=None, dropdown_api=None,
                                        boundary_type=None, draw_features=None, userlayers=None, boundary_layer=None):
        """
        :param override_boundary_type: (optional) Type of boundary to override the default boundary type.
        :type override_boundary_type: str
        :param layer: (optional) Name of the layer to use for processing features.
        :type layer: str
        :param column: (optional) Name of the column to use for processing features.
        :type column: str
        :param dropdown_api: (optional) API to retrieve dropdown values.
        :type dropdown_api: str
        :param boundary_type: (optional) Type of boundary to process.
        :type boundary_type: str
        :param draw_features: (optional) List of features drawn by the user.
        :type draw_features: list
        :param userlayers: (optional) Dictionary of user uploaded layers.
        :type userlayers: dict
        :param boundary_layer: (optional) Layer name for user defined boundary.
        :type boundary_layer: str
        :return: List of geometries to process.
        :rtype: list
        """
        geometries = []
        if override_boundary_type:
            boundary_type = override_boundary_type
        else:
            boundary_type = boundary_type
        if boundary_type in ['Predefined Boundaries', 'User Defined']:
            for feature in draw_features:
                if boundary_type == 'Predefined Boundaries':
                    distinct_values = self.process_drawn_features([feature], layer=layer, column=column)
                    feature = self.download_feature_geometry(distinct_values, feature_type_prefix=boundary_layer.split('_')[0],
                                                             column=column, layer=layer, dropdown_api=dropdown_api)

                else:  # User Defined
                    distinct_values = None
                    # Assuming feature is the geometry itself in this case
                geometries.append((feature, distinct_values))
        elif boundary_type == 'User Uploaded Data' and 'User Uploaded Data' in userlayers:
            feature = userlayers['User Uploaded Data'].data
            geometries.append((feature, None))
        return geometries


class EarthEngineNotebookInterface(BaseModel):
    class Config:
        """
        This class represents a configuration object.

        Attributes:
            extra (Extra): Specifies whether to allow extra fields in the configuration.

        Enum:
            Extra:
                - allow: Allows extra fields in the configuration.
                - disallow: Disallows extra fields in the configuration.
        """
        extra = Extra.allow  # Allow extra fields

    def __init__(self, **data):
        """Initialize the object with the given parameters.

        :param data: The data used to initialize the object.
        """
        super().__init__(**data)
        self.gee_layer_search_widget = None
        self.create_widgets_gee()

    def on_gee_search_button_clicked(self, b):
        """
        Handle the click event of the Google Earth Engine search button.

        :param b: The button object that was clicked.
        :return: None
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
        Method to handle the selection of a Google Earth Engine layer.

        :param b: The event object triggered by the selection.
        :type b: object

        :return: None
        :rtype: None
        """
        selected_layer = self.gee_layer_search_results_dropdown.value
        self.ee_dates_min_max = self.get_image_collection_dates(selected_layer, min_max_only=True)

        self.gee_bands_search_results.options = ee.ImageCollection(selected_layer).first().bandNames().getInfo()

    def on_single_or_range_dates_change(self, change):
        """
        Method to handle changes in the selection of single or range dates.

        :param change: The change event triggered by the selection.
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

            self.gee_single_date_selector.options = self.get_image_collection_dates(
                self.gee_layer_search_results_dropdown.value, min_max_only=False)
            self.gee_date_selection.children = [self.gee_single_date_selector]
        elif self.single_or_range_dates.value == 'Date Range':
            start_date = datetime.datetime.strptime(self.ee_dates_min_max[0], '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(self.ee_dates_min_max[1], '%Y-%m-%d').date()

            self.gee_date_picker_start = widgets.DatePicker(
                description='Select Start Date:',
                disabled=False,
                min=start_date,
                max=end_date,
                value=start_date
            )
            self.gee_date_picker_end = widgets.DatePicker(
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
            self.gee_date_selection.children = [widgets.HBox([self.gee_date_picker_start, self.gee_date_picker_end]),
                                                self.gee_multi_date_aggregation_periods,
                                                self.gee_multi_date_aggregation_method]

    def create_widgets_gee(self):
        """

        :create_widgets_gee method creates and configures the GEE widgets used for searching layers, selecting layers, selecting bands, and setting processing options.

        :return:  A list of the configured GEE widgets.

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

        self.search_box = widgets.HBox([self.gee_layer_search_widget, self.search_button])

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

        self.layer_select_box = widgets.HBox([self.gee_layer_search_results_dropdown, self.select_layer_gee])

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

        self.add_image_to_map = widgets.Checkbox(description='Add Image to Map')
        self.filechooser = fc.FileChooser(os.getcwd(), show_only_dirs=True)
        self.create_sub_folder = widgets.Checkbox(description='Create Sub-folder')

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

    def process_api(self, geometry, distinct_values, index):
        """
        :param geometry: The geometry for which to retrieve the image data.
        :param distinct_values: Whether to retrieve distinct values or not.
        :param index: The index of the distinct value to retrieve.
        :return: None
        """
        with self.out:
            gee_params = self.gather_gee_parameters()
            with self.out:
                self.out.clear_output()
                print(gee_params)
            geometry = self.ee_ensure_geometry(geometry)
            if gee_params['multi_date'] == False:
                img, region, gee_params['scale'] = self.get_image(**gee_params, geometry=geometry)
                url = self.get_image_download_url(img=img, region=region, scale=gee_params['scale'])
                file_name = 'gee_image.tif'
                self.download_file_from_url(url=url, destination_path=file_name)
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
                    monthly_date_ranges = self.generate_monthly_date_ranges(gee_params['start_date'],
                                                                                   gee_params['end_date'])
                    if gee_params['statistics_only']:
                        all_stats = ee.Dictionary()
                    for dates in monthly_date_ranges:
                        if gee_params['statistics_only']:
                            image, geometry = self.get_image(multi_date=True,
                                                                    aggregation_method=gee_params[
                                                                        'aggregation_method'],
                                                                    geometry=geometry, start_date=dates[0],
                                                                    end_date=dates[1],
                                                                    band=gee_params['band'],
                                                                    image_collection=gee_params[
                                                                        'image_collection'])
                            stats = self.calculate_statistics(image, geometry, gee_params[
                                'band'])  # This should be a server-side object
                            all_stats = all_stats.set(dates[0], stats)
                        else:
                            img, boundary = self.get_image(multi_date=True,
                                                                  aggregation_method=gee_params[
                                                                      'aggregation_method'],
                                                                  geometry=geometry, start_date=dates[0],
                                                                  end_date=dates[1],
                                                                  band=gee_params['band'],
                                                                  image_collection=gee_params[
                                                                      'image_collection'])
                            url = self.get_image_download_url(img=img, region=boundary,
                                                                     scale=gee_params['scale'])
                            file_name = f"{gee_params['image_collection']}_{dates[0]}_{dates[1]}_{gee_params['aggregation_method']}.tif".replace(
                                '-', '_').replace('/', '_').replace(' ', '_')
                            self.download_file_from_url(url=url, destination_path=file_name)
                            print(f"Downloaded {file_name}")
                    if gee_params['statistics_only']:
                        all_stats_info = all_stats.getInfo()
                        with self.out:
                            self.out.clear_output()
                            print(all_stats_info)

                elif gee_params['aggregation_period'] == 'Yearly':
                    yearly_date_ranges = self.generate_yearly_date_ranges(
                        gee_params['start_date'], gee_params['end_date'])
                    if gee_params['statistics_only']:
                        all_stats = ee.Dictionary()
                    for dates in yearly_date_ranges:
                        if gee_params['statistics_only']:
                            image, geometry = self.get_image(multi_date=True,
                                                                    aggregation_method=gee_params[
                                                                        'aggregation_method'],
                                                                    geometry=geometry, start_date=dates[0],
                                                                    end_date=dates[1],
                                                                    band=gee_params['band'],
                                                                    image_collection=gee_params[
                                                                        'image_collection'])
                            stats = self.calculate_statistics(image, geometry, gee_params[
                                'band'])  # This should be a server-side object
                            all_stats = all_stats.set(dates[0], stats)

                        else:
                            img, boundary = self.get_image(multi_date=True,
                                                                  aggregation_method=gee_params[
                                                                      'aggregation_method'],
                                                                  geometry=geometry, start_date=dates[0],
                                                                  end_date=dates[1],
                                                                  band=gee_params['band'],
                                                                  image_collection=gee_params[
                                                                      'image_collection'])
                            url = self.get_image_download_url(img=img, region=boundary,
                                                                     scale=gee_params['scale'])
                            file_name = f"{gee_params['image_collection']}_{dates[0]}_{dates[1]}_{gee_params['aggregation_method']}.tif".replace(
                                '-', '_').replace('/', '_').replace(' ', '_')
                            self.download_file_from_url(url=url, destination_path=file_name)
                            print(f"Downloaded {file_name}")
                    if gee_params['statistics_only']:
                        all_stats_info = all_stats.getInfo()
                        with self.out:
                            print(all_stats_info)
                elif gee_params['aggregation_period'] == 'One Aggregation':
                    img, boundary = self.get_image(multi_date=True,
                                                          aggregation_method=gee_params[
                                                              'aggregation_method'],
                                                          geometry=geometry,
                                                          start_date=str(gee_params['start_date']),
                                                          end_date=str(gee_params['end_date']),
                                                          band=gee_params['band'],
                                                          image_collection=gee_params[
                                                              'image_collection'])
                    url = self.get_image_download_url(img=img, region=boundary,
                                                             scale=gee_params['scale'])

                    file_name = f"{gee_params['image_collection']}_{str(gee_params['start_date'])}_{str(gee_params['end_date'])}_{gee_params['aggregation_method']}.tif".replace(
                        '-', '_').replace('/', '_').replace(' ', '_')
                    self.download_file_from_url(url=url, destination_path=file_name)
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

    def gather_parameters(self):
        """
        Gathers the parameters required for processing.

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


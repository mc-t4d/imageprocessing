import os

import geopandas as gpd
import localtileserver
import numpy as np
import pygrib
import rasterio
from osgeo import gdal
from rasterio.features import geometry_mask
from rasterio.merge import merge
from shapely.geometry import MultiPolygon
from shapely.geometry import shape


def mosaic_images(file_names, output_filename='mosaic.tif'):
    """
    Merges multiple raster files into a mosaic and saves it to an output file.

    :param file_names: A list of file names of the raster files to be merged.
    :param output_filename: The name of the output file to be created. Default is 'mosaic.tif'.
    :return: None
    """
    src_files_to_mosaic = []
    for fn in file_names:
        src = rasterio.open(fn)
        src_files_to_mosaic.append(src)

    mosaic, out_trans = merge(src_files_to_mosaic)
    out_meta = src.meta.copy()
    out_meta.update({"driver": "GTiff",
                     "height": mosaic.shape[1],
                     "width": mosaic.shape[2],
                     "transform": out_trans})

    with rasterio.open(f"{output_filename}", "w", **out_meta) as dest:
        dest.write(mosaic)

    for fn in file_names:
        os.remove(fn)

def process_and_clip_raster(file_path, geometry, params=None, ee_instance=None):
    """
    :param file_path: The file path of the raster file to be processed and clipped.
    :param geometry: The geometry object to be used for clipping the raster.
    :param params: Optional parameters for controlling the processing and clipping.
    :param ee_instance: An instance of the Earth Engine API for using Earth Engine functions.

    :return: If params['clip_to_geometry'] is True, returns the file path of the clipped raster.
             If params['clip_to_geometry'] is False, returns the original file path.
    """
    min_val, max_val, no_data_val = get_raster_min_max(file_path)
    if min_val == -9999:
        min_val = 0

    vis_params = {
        'min': min_val,
        'max': max_val,
        'palette': 'viridis',
        'nodata': no_data_val
    }
    if params['clip_to_geometry']:
        raster_path = clip_raster(file_path, geometry, ee_instance)
        return raster_path
    else:
        raster_path = file_path
        return raster_path
    # if params['add_to_map']:
    #     add_clipped_raster_to_map(map_object, raster_path, vis_params=vis_params)

def get_raster_min_max(raster_path):
    """
    :param raster_path: The file path of the raster to be processed.
    :return: A tuple containing the minimum value, maximum value, and nodata value of the raster.

    This method retrieves the minimum value, maximum value, and nodata value of a given raster file. It assumes that the raster file has only one band.

    First, the method opens the raster file using the GDAL library and gets the first band of the dataset.

    Then, it checks if the band provides the minimum and maximum values. If not, it computes the minimum and maximum values using the ComputeRasterMinMax() method of the band.

    Next, it reads the band data as an array.

    If the band data contains values equal to 9999, it masks the data to ignore those values. It then finds the maximum value in the masked data and sets it as the new maximum value.

    Finally, the method closes the dataset and returns a tuple containing the minimum value, maximum value, and nodata value of the raster.
    """

    dataset = gdal.Open(raster_path)
    band = dataset.GetRasterBand(1)  # Assumes the raster has only one band
    min_val = band.GetMinimum()
    max_val = band.GetMaximum()
    nodata_val = band.GetNoDataValue()

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
    return min_val, max_val, nodata_val

def add_clipped_raster_to_map(map_object, raster_path, vis_params=None):
    """
    :param map_object: The map object to which the clipped raster will be added.
    :param raster_path: The file path or URL of the raster data to be added.
    :param vis_params: Optional visualization parameters for the raster layer. Default is None.
    :return: None

    This method adds a clipped raster layer to the specified map object. The raster data is loaded from the provided raster_path. If visualization parameters are not specified, default parameters
    * will be used. Once the raster layer is created, it is added to the map object and the map view is adjusted to fit the bounds of the raster data.

    If a ValueError is raised during the process, it will be caught and a corresponding error message will be printed. Other types of exceptions will also be caught and an error message
    * will be printed.
    """
    if vis_params is None:
        vis_params = {}
    try:
        client = localtileserver.TileClient(raster_path)
        tile_layer = localtileserver.get_leaflet_tile_layer(client, **vis_params)
        map_object.add_layer(tile_layer)
        map_object.fit_bounds(client.bounds)
    except ValueError as e:
        print(f"ValueError: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

def inspect_grib_file(file_path: str):
    """
    Inspect GRIB File

    :param file_path: The path to the GRIB file to be inspected.
    :return: None

    This method opens the given GRIB file using the pygrib library and prints information about each message in the file. It does not return any value.

    Example usage:
        inspect_grib_file("path/to/grib/file.grib")
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

def clip_raster(file_path, geometry, ee_instance):
    """
    :param file_path: The file path of the raster file to be clipped.
    :param geometry: The geometry to be used for clipping.
    :param ee_instance: The Earth Engine instance used for conversion.

    :return: The file path of the clipped raster file.

    """

    # Check file format and inspect if it's a GRIB file

    if file_path.endswith('.grib'):
        inspect_grib_file(file_path)


    # Convert Earth Engine geometry to shapely geometry
    geometry = ee_instance.ee_geometry_to_shapely(geometry)


    # Convert to MultiPolygon if needed
    try:
        if isinstance(geometry, dict):
            try:
                geometry = shape(geometry['geometries'][1])
            except KeyError:
                geometry = shape(geometry)
        if not isinstance(geometry, MultiPolygon):
            geometry = MultiPolygon([geometry])
    except Exception as e:
        print(f"An error occurred: {e}")

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

def calculate_bounds(geojson_content):
    """
    Calculate the bounds (minimum and maximum coordinates) of a given GeoJSON content.

    :param geojson_content: The GeoJSON content.
    :type geojson_content: dict
    :return: The bounds represented by a list of two coordinate pairs: [[min_lat, min_lon], [max_lat, max_lon]].
    :rtype: list
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

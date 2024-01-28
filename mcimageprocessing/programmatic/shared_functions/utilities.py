import rasterio
import os
from rasterio.merge import merge
import pygrib

import subprocess

import ee
import geopandas as gpd
import localtileserver
import numpy as np
from shapely.geometry import MultiPolygon
from osgeo import gdal

from rasterio.features import geometry_mask

from shapely.geometry import shape


def mosaic_images(file_names, output_filename='mosaic.tif'):
    """Mosaic images and save as a single file."""
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
    Process and clip a raster file.

    :param file_path: The file path of the raster file to be processed and clipped.
    :return: None
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
    :param raster_path: The file path to the raster file.
    :return: A tuple containing the minimum and maximum values of the raster.
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
        map_object.add_layer(tile_layer)
        map_object.fit_bounds(client.bounds)
    except ValueError as e:
        print(f"ValueError: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

def inspect_grib_file(file_path: str):
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

def clip_raster(file_path, geometry, ee_instance):
    """
    :param file_path: The file path of the raster file (GRIB or TIFF) to be clipped.
    :param geometry: The geometry to clip the raster file.
    :return: The file path of the clipped TIFF file.
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

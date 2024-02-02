# File: mcimageprocessing/programmatic/__init__.py

from .APIs.EarthEngine import EarthEngineManager, EarthEngineNotebookInterface
from .APIs.GloFasAPI import GloFasAPI, GloFasAPINotebookInterface
from .APIs.GPWv4 import GPWv4, GPWv4NotebookInterface
from .APIs.ModisNRT import ModisNRT, ModisNRTNotebookInterface
from .APIs.WorldPop import WorldPop, WorldPopNotebookInterface
from .shared_functions.utilities import *

# Add all functions and classes to __all__ for import * support
__all__ = [
    'EarthEngineManager', 'GloFasAPI', 'GPWv4', 'ModisNRT', 'WorldPop',
    'EarthEngineNotebookInterface', 'GloFasAPINotebookInterface', 'GPWv4NotebookInterface',
    'ModisNRTNotebookInterface', 'WorldPopNotebookInterface',
    # Add all functions and classes from utilities to __all__
    'mosaic_images', 'process_and_clip_raster', 'get_raster_min_max', 'add_clipped_raster_to_map',
    'inspect_grib_file', 'clip_raster'
]

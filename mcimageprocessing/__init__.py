# File: mcimageprocessing/__init__.py

"""Top-level package for mcimageprocessing."""

__author__ = """Nicholas Dowhaniuk"""
__email__ = 'nick@kndconsulting.org'
__version__ = '0.1.0'

import os
from .config.config import ConfigManager

# Construct the path to the config.yaml file
config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')

# Initialize the ConfigManager with the path to the config.yaml
config_manager = ConfigManager.get_instance(config_path)


from . import jupyter
__all__ = ['jupyter'] + getattr(jupyter, '__all__', [])

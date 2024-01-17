"""Top-level package for mcimageprocessing."""

__author__ = """Nicholas Dowhaniuk"""
__email__ = 'nick@kndconsulting.org'
__version__ = '0.1.0'


from . import jupyter

__all__ = ['jupyter'] + jupyter.__all__


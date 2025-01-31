#!/usr/bin/env python

with open('./requirements.txt') as f:
    requirements = f.read().splitlines()

"""The setup script."""

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

test_requirements = ['pytest>=3', ]

setup(
    author="Nicholas Dowhaniuk",
    author_email='nick@kndconsulting.org',
    python_requires='>=3.11',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
    ],
    description="A Python package built for Mercy Corps to handle image processing and analysis.",
    install_requires=requirements,
    long_description=readme + '\n\n' + history,
    keywords='mcimageprocessing',
    name='mcimageprocessing',
    packages=find_packages(include=['mcimageprocessing', 'mcimageprocessing.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/mc-t4d/mcimageprocessing',
    version='0.1.0',
    zip_safe=False,
)


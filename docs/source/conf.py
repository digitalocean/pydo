# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys
# This allows sphinx to locate the client source code.
sys.path.insert(0, os.path.abspath('../../src/'))

project = 'PyDo'
copyright = '2022, DigitalOcean'
author = 'DigitalOcean'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration
# This extension generates the documentation
extensions = ['sphinx.ext.autodoc']

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
# This configuration determines the style of the html page
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
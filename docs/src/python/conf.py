import os
import sys

sys.path.append(os.path.join(os.path.dirname(__name__), '../../src'))
# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Authority Contribution Scraper'
copyright = '2023, Mark van Holsteijn'
author = 'Mark van Holsteijn'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx_rtd_theme',
    'autoapi.extension',
]

autoapi_type = 'python'
autoapi_dirs = ['../../../src']
autoapi_python_class_content = 'both'
# autoapi_add_toctree_entry = False
autoapi_options = [
    'members',
    'undoc-members',
    'show-inheritance',
    'show-inheritance-diagram',
    'inherited-members',
    # 'show-module-summary',
    # 'special-members',
]


def skip_module_attributes(app, what, name, obj, skip, options):
    if what == "data":
        skip = True
    return skip


def setup(sphinx):
   sphinx.connect("autoapi-skip-member", skip_module_attributes)


intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'bigquery': ('https://googleapis.dev/python/bigquery/latest', None),
}

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

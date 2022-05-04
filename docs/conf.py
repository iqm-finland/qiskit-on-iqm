# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

# Find the path to the source files we want to to document, relative to the location of this file,
# convert it to an absolute path.
py_path = os.path.join(os.getcwd(), os.path.dirname(__file__), '../src')
sys.path.insert(0, os.path.abspath(py_path))


# -- Project information -----------------------------------------------------

project = 'Qiskit on IQM'
copyright = '2022, Qiskit on IQM developers'
author = 'Qiskit on IQM developers'

# The short X.Y version.
version = ''
# The full version, including alpha/beta/rc tags.
release = ''
try:
    from qiskit_iqm import __version__ as version
except ImportError:
    pass
else:
    release = version


# -- General configuration ---------------------------------------------------

# require a recent version of Sphinx
needs_sphinx = '4.4'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx.ext.mathjax',
    'sphinx.ext.inheritance_diagram',
    'sphinx.ext.todo',
    'sphinx.ext.extlinks',
    'sphinx.ext.intersphinx',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '.*']

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
# today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%Y-%m-%d'

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
show_authors = True


# -- Autodoc ------------------------------------------------------------

# member ordering in autodoc output (default: 'alphabetical')
autodoc_member_order = 'bysource'

# where should signature annotations appear in the docs, function signature or parameter description?
autodoc_typehints = 'description'
# autodoc_typehints = 'description' puts the __init__ annotations into its docstring,
# which we thus have to include in the class documentation.
autoclass_content = 'both'

# Sphinx 3.3+: manually clean up type alias rendering in the docs
# autodoc_type_aliases = {'TypeAlias': 'exa.experiment.somemodule.TypeAlias'}


# -- Autosummary ------------------------------------------------------------

# use autosummary to generate stub pages for API docs
autosummary_generate = True


# -- Options for HTML output -------------------------------------------------

import sphinx_book_theme

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_book_theme'

html_theme_options = {
    'logo_only': True,
}
# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
#html_static_path = ['_static']

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = '_static/images/favicon.ico'

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = '_static/images/logo.png'

# Output file base name for HTML help builder.
htmlhelp_basename = 'qiskit_iqm-doc'


# -- MathJax options ----------------------------------------------------------

# Here we configure MathJax, mostly to define LaTeX macros.
mathjax3_config = {
    'tex': {
        'macros': {
            'vr': r'\vec{r}',  # no arguments
            'ket': [r'\left| #1 \right\rangle', 1],  # one argument
            'iprod': [r'\left\langle #1 | #2 \right\rangle', 2],  # two arguments
        }
    }
}


# -- External mapping ------------------------------------------------------------

python_version = '.'.join(map(str, sys.version_info[0:2]))
intersphinx_mapping = {
    'sphinx': ('https://www.sphinx-doc.org/en/master', None),
    'python': ('https://docs.python.org/' + python_version, None),
    'matplotlib': ('https://matplotlib.org/stable', None),
    'numpy': ('https://numpy.org/doc/stable', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/reference', None),
}

extlinks = {
    'issue': ('https://github.com/iqm-finland/qiskit-on-iqm/issues/%s', 'issue '),
    'mr': ('https://github.com/iqm-finland/qiskit-on-iqm/pull/%s', 'MR '),
}


# -- Options for sphinxcontrib.bibtex -------------------------------------------------

# List of all bibliography files used.
#bibtex_bibfiles = ['references.bib']

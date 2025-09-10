# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

import openstackdocstheme


sys.path.insert(0, os.path.abspath('../..'))
# -- General configuration ----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'openstackdocstheme',
    'sphinx.ext.autodoc',
    'sphinxcontrib.rsvgconverter',
]

# autodoc generation is a bit aggressive and a nuisance when doing heavy
# text edit cycles.
# execute "export SPHINX_DEBUG=1" in your terminal to disable

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'Kolla Ansible'
copyright = '2013, OpenStack Foundation'

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'native'

# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
# html_theme_path = []
html_theme = 'openstackdocs'
# html_static_path = ['static']

# Add any paths that contain "extra" files, such as .htaccess or
# robots.txt.
html_extra_path = ['_extra']

html_theme_options = {
    "show_other_versions": True,
}

# Output file base name for HTML help builder.
htmlhelp_basename = 'kolla-ansibledoc'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass
# [howto/manual]).
latex_documents = [
    ('index',
     'doc-kolla-ansible.tex',
     'Kolla Ansible Documentation',
     'OpenStack Foundation', 'manual'),
]

# Disable usage of xindy https://bugzilla.redhat.com/show_bug.cgi?id=1643664
latex_use_xindy = False

# openstackdocstheme options
openstackdocs_repo_name = 'openstack/kolla-ansible'
openstackdocs_pdf_link = True
openstackdocs_bug_project = 'kolla-ansible'
openstackdocs_bug_tag = ''
openstack_projects = [
    'bifrost',
    'cinder',
    'cloudkitty',
    'designate',
    'glance',
    'ironic',
    'keystone',
    'kayobe',
    'kolla',
    'kolla-ansible',
    'magnum',
    'manila',
    'networking-sfc',
    'neutron-vpnaas',
    'neutron',
    'nova',
    'octavia',
    'oslo.messaging',
    'oslotest',
    'ovn-octavia-provider',
    'watcher',
]

# Global variables
# For replacement, use in docs as |VAR_NAME| (note there's no space around variable name)
# When adding new variables, that you want to use in documentation, make sure you add
# them to GLOBAL_VARIABLE_MAP dictionary as well. KOLLA_OPENSTACK_RELEASE_UNMAINTAINED is
# used only to denote unmaintained branches, and it is not intended to be used for
# replacing anything in documentation.

OPENSTACK_RELEASE = openstackdocstheme.ext._get_series_name()

KOLLA_OPENSTACK_RELEASE_UNMAINTAINED = [
    '2023.1',
]

if OPENSTACK_RELEASE == 'latest':
    KOLLA_OPENSTACK_RELEASE = 'master'
    KOLLA_BRANCH_NAME = 'master'
    TESTED_RUNTIMES_GOVERNANCE_URL = 'https://governance.openstack.org/tc/reference/runtimes/'
elif OPENSTACK_RELEASE in KOLLA_OPENSTACK_RELEASE_UNMAINTAINED:
    KOLLA_OPENSTACK_RELEASE = OPENSTACK_RELEASE
    KOLLA_BRANCH_NAME = 'unmaintained/{}'.format(KOLLA_OPENSTACK_RELEASE)
    TESTED_RUNTIMES_GOVERNANCE_URL =\
        'https://governance.openstack.org/tc/reference/runtimes/{}.html'.format(KOLLA_OPENSTACK_RELEASE)
else:
    KOLLA_OPENSTACK_RELEASE = OPENSTACK_RELEASE
    KOLLA_BRANCH_NAME = 'stable/{}'.format(KOLLA_OPENSTACK_RELEASE)
    TESTED_RUNTIMES_GOVERNANCE_URL =\
        'https://governance.openstack.org/tc/reference/runtimes/{}.html'.format(KOLLA_OPENSTACK_RELEASE)

ANSIBLE_CORE_VERSION_MIN = '2.18'
ANSIBLE_CORE_VERSION_MAX = '2.19'
ANSIBLE_VERSION_MIN = '11'
ANSIBLE_VERSION_MAX = '12'

GLOBAL_VARIABLE_MAP = {
    '|ANSIBLE_CORE_VERSION_MIN|': ANSIBLE_CORE_VERSION_MIN,
    '|ANSIBLE_CORE_VERSION_MAX|': ANSIBLE_CORE_VERSION_MAX,
    '|ANSIBLE_VERSION_MIN|': ANSIBLE_VERSION_MIN,
    '|ANSIBLE_VERSION_MAX|': ANSIBLE_VERSION_MAX,
    '|KOLLA_OPENSTACK_RELEASE|': KOLLA_OPENSTACK_RELEASE,
    '|KOLLA_BRANCH_NAME|': KOLLA_BRANCH_NAME,
    '|KOLLA_BRANCH_NAME_DASHED|': KOLLA_BRANCH_NAME.replace('/', '-'),
    '|OPENSTACK_RELEASE|': OPENSTACK_RELEASE,
    '|TESTED_RUNTIMES_GOVERNANCE_URL|': TESTED_RUNTIMES_GOVERNANCE_URL,
}


def replace_global_vars(app, docname, source):
    # unlike rst_epilog, replaces variables (strings) in code blocks as well
    # thanks to https://github.com/sphinx-doc/sphinx/issues/4054#issuecomment-329097229
    result = source[0]
    for key in app.config.GLOBAL_VARIABLE_MAP:
        result = result.replace(key, app.config.GLOBAL_VARIABLE_MAP[key])
    source[0] = result


def setup(app):
   app.add_config_value('GLOBAL_VARIABLE_MAP', {}, True)
   app.connect('source-read', replace_global_vars)

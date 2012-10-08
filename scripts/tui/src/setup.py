#!/usr/bin/env python

from distutils.core import setup

# bump version
setup(name='ovirt-node-molch',
    version='0.0.1',
    description='oVirt Node COnfiguration TUI',
    author='Fabian Deutsch',
    author_email='fabiand@fedoraproject.org',
    url='http://example.com',
    license="GPLv2+",
    packages=[
        'ovirt',
        'ovirt.node',
        'ovirt.node.ui',
        'ovirt.node.utils',
        'ovirt.node.plugins',
        ]
)

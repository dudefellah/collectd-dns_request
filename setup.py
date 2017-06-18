#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='collectd-dns_request',
    version='0.1',
    description="Simple Python-based plugin to report request times for "
                "specific requests to specific nameservers",
    author="Dan Thomson",
    author_email='dan@fatmoustache.ca',
    url='https://github.com/dudefellah/collectd-dns_request',
    include_package_data=True,
    license="GPLv3",
    keywords='collectd-dns_request',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
    ],
)

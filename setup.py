#!usr/bin/env python
# -*- coding:utf-8 -*-

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

packages = [
    'wind',
    'wind.web'
    ]

requires = []

setup(
    name='wind',
    version='0.1',
    packages=packages,
    package_data={'': ['LICENSE']},
    include_package_data=True,
    author='daftshady',
    author_email='daftonshady@gmail.com',
    license=open('LICENSE').read(),
    description='Web framework based on async networking server',
    install_requires=requires
)

#!/usr/bin/env python
#
#
# To create a source distribution for this module, run this command from a terminal:
#   python setup.py sdist
#

from setuptools import setup
setup(name='autonomia',
      description='Autonomia SDK',
      author='Visible Energy Inc.',
      maintainer='Nicolae Carabut',
      maintainer_email='nicolae@visiblenergy.com',
      url='https://github.com/AUT0N0MIA/Autonomia-SDK-Python',
      version='1.0.0',
      license='Apache 2.0',
      py_modules=['autonomialib','streamer'],
      install_requires=[
          'http-parser',
      ], 
      )

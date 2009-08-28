#! /usr/bin/env python

from distutils.core import setup

setup(name="ocitysmap",
      description="OcitySMap, a tool to render city maps based on OpenStreetMap data",
      long_description="""
OcitySMap is a tool that allows to render city maps based on
OpenStreetMap data, along with an index of the streets. These maps are
designed to be printed.
""",
      version="1.0",
      author="The Hackfest2009 team",
      author_email="staff@maposmatic.org",
      url="http://www.maposmatic.org",
      license="GPL",
      maintainer="The Hackfest2009 team",
      maintainer_email="staff@maposmatic.org",
      packages = ['ocitysmap' ],
      scripts = ['ocitysmap-render' ]
)

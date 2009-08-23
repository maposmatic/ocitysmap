# -*- coding: utf-8; mode: Python -*-

"""OCitySMap.

Provide documentation here.
"""

__author__ = 'The Hackfest2009 team'
__version__ = '0.1'

import logging

l = logging.getLogger('ocitysmap')

class BaseOCitySMapError(Exception):
    """Base class for exceptions thrown by OCitySMap."""

class UnsufficientDataError(BaseOCitySMapError):
    """Not enough data in the OSM database to proceed."""

class OCitySMap:
    def __init__(self, name, boundingbox=None, zooms=[]):
        """Creates a new OCitySMap renderer instance for the given city.

        Args:
            name (string): The name of the city we're created the map of.
            boundingbox (4-uple): Tuple of 4 decimal GPS coordinates defining
                the bounding box of the city in the form (top-left, top-right,
                bottom-right, bottom-left). If not provided, OCitySMap tries to
                find the bounding box from the OSM data. UnsufficientDataError
                will be thrown if OCitySMap can't determine the bounding box.
            zooms (list): A list of zoom sections to add to the map. The list
                contains 5-uples describing each zoom section, starting by its
                title and followed by its boundix box GPS coordinates, in the
                same order as above.
        """
        self.name = name

        if boundingbox and len(boundingbox) != 4:
            raise ValueError, "Invalid bounding box"
        self.boundingbox = boundingbox

        self.zooms = {}
        for zoom in zooms:
            if len(zoom) != 5:
                raise ValueError, "Invalid zoom box"
            self.zooms[zoom[0]] = zoom[1:]

        l.info('OCitySMap renderer for %s.' % self.name)
        l.info('%d zoom section(s).' % len(self.zooms))
        for name, box in self.zooms.iteritems():
            l.debug('"%s": %s' % (name, str(box)))

        if not self.boundingbox:
            self.boundingbox = self.find_bounding_box(self.name)

        l.info('Bounding box is %s.' % str(self.boundingbox))

    def find_bounding_box(self, name):
        """Find the bounding box of a city from its name.
        
        Args:
            name (string): The city name.
        Returns a 4-uple of GPS coordinates describing the bounding box around
        the given city (top-left, top-right, bottom-right, bottom-left).
        """

        l.info('Looking for bounding box around %s...' % name)
        raise UnsufficientDataError, "Not enough data to find city bounding box!"


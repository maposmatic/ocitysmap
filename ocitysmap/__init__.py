# -*- coding: utf-8; mode: Python -*-

"""OCitySMap.

Provide documentation here.
"""

__author__ = 'The Hackfest2009 team'
__version__ = '0.1'

import logging
import pgdb
import math

l = logging.getLogger('ocitysmap')

class BaseOCitySMapError(Exception):
    """Base class for exceptions thrown by OCitySMap."""

class UnsufficientDataError(BaseOCitySMapError):
    """Not enough data in the OSM database to proceed."""

class BoundingBox:
    def __init__(self, lat1, long1, lat2, long2):
        (self._lat1, self._long1) = float(lat1), float(long1)
        (self._lat2, self._long2) = float(lat2), float(long2)

        # Validate bounding box?

    @staticmethod
    def parse(points):
        (lat1, long1) = points[0].split(',')
        (lat2, long2) = points[1].split(',')
        return BoundingBox(lat1, long1, lat2, long2)

    def get_top_left(self):
        return (self._lat1, self._long1)

    def get_bottom_right(self):
        return (self._lat2, self._long2)

    def ptstr(self, point):
        return '%.4f,%.4f' % (point[0], point[1])

    def __str__(self):
        return '(%s %s)' % (self.ptstr(self.get_top_left()),
                            self.ptstr(self.get_bottom_right()))

def _gen_vertical_square_label(x):
    label = ''
    while x != -1:
        label = chr(ord('A') + x % 26) + label
        x /= 26
        x -= 1
    return label

def _gen_horizontal_square_label(x):
    return str(x + 1)

class MapDescriptor:
    def __init__(self, bbox, db):
        self.bbox = bbox
        cursor = db.cursor()

        # Compute width and heights in meters of the bounding box
        cursor.execute("""select
                          st_distance_sphere(st_geomfromtext('POINT(%f %f)', 4002),
                                             st_geomfromtext('POINT(%f %f)', 4002))""" % \
                           (bbox.get_top_left()[0], bbox.get_top_left()[1],
                            bbox.get_top_left()[0], bbox.get_bottom_right()[1]))
        width = cursor.fetchall()[0][0]
        cursor.execute("""select
                          st_distance_sphere(st_geomfromtext('POINT(%f %f)', 4002),
                                             st_geomfromtext('POINT(%f %f)', 4002))""" % \
                           (bbox.get_top_left()[0], bbox.get_top_left()[1],
                            bbox.get_bottom_right()[0], bbox.get_top_left()[1]))
        height = cursor.fetchall()[0][0]

        # Compute number of squares, assumming a size of 500 meters
        # per square
        width_square_count  = width / 500
        height_square_count = height / 500

        # Compute the size in angles of the squares
        self.width_square_angle  = (abs(bbox.get_top_left()[1] - bbox.get_bottom_right()[1]) /
                                    width_square_count)
        self.height_square_angle = (abs(bbox.get_top_left()[0] - bbox.get_bottom_right()[0]) /
                                    height_square_count)

        # Compute the lists of longitudes and latitudes of the
        # horizontal and vertical lines delimiting the square
        self.vertical_lines   = [bbox.get_top_left()[1] + x * self.width_square_angle
                                 for x in xrange(0, int(math.ceil(width_square_count )) + 1)]
        self.horizontal_lines = [bbox.get_top_left()[0] - x * self.height_square_angle
                                 for x in xrange(0, int(math.ceil(height_square_count)) + 1)]

        # Compute the lists of labels
        self.vertical_labels   = [_gen_vertical_square_label(x)
                                  for x in xrange(0, int(math.ceil(width_square_count)))]
        self.horizontal_labels = [_gen_horizontal_square_label(x)
                                  for x in xrange(0, int(math.ceil(height_square_count)))]
        print self.vertical_lines
        print self.horizontal_lines
        print self.vertical_labels
        print self.horizontal_labels

class OCitySMap:
    def __init__(self, name, boundingbox=None, zooms=[]):
        """Creates a new OCitySMap renderer instance for the given city.

        Args:
            name (string): The name of the city we're created the map of.
            boundingbox (BoundingBox): An optional BoundingBox object defining
                the city's bounding box. If not given, OCitySMap will try to
                guess the bounding box from the OSM data. An UnsufficientDataError
                exception will be raised in the bounding box can't be guessed.
            zooms (dict): A dictionnary of zoom sections to add to the map. The
                dictionnary maps a zoom box title to its bounding box
                (BoundingBox objects).
        """
        (self.name, self.boundingbox, self.zooms) = (name, boundingbox, zooms)

        l.info('OCitySMap renderer for %s.' % self.name)
        l.info('%d zoom section(s).' % len(self.zooms))
        for name, box in self.zooms.iteritems():
            l.debug('"%s": %s' % (name, str(box)))

        if not self.boundingbox:
            self.boundingbox = self.find_bounding_box(self.name)

        db = pgdb.connect('Notre Base', 'test', 'test', 'surf.local', 'testdb')
        self.mapdesc = MapDescriptor(self.boundingbox, db)

        l.info('City bounding box is %s.' % str(self.boundingbox))

    def find_bounding_box(self, name):
        """Find the bounding box of a city from its name.
        
        Args:
            name (string): The city name.
        Returns a 4-uple of GPS coordinates describing the bounding box around
        the given city (top-left, top-right, bottom-right, bottom-left).
        """

        l.info('Looking for bounding box around %s...' % name)
        raise UnsufficientDataError, "Not enough data to find city bounding box!"


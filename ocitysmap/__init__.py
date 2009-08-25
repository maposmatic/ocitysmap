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
        self.width_square_count  = width / 500
        self.height_square_count = height / 500

        # Compute the size in angles of the squares
        self.width_square_angle  = (abs(bbox.get_top_left()[1] - bbox.get_bottom_right()[1]) /
                                    self.width_square_count)
        self.height_square_angle = (abs(bbox.get_top_left()[0] - bbox.get_bottom_right()[0]) /
                                    self.height_square_count)

        # Compute the lists of longitudes and latitudes of the
        # horizontal and vertical lines delimiting the square
        self.vertical_lines   = [bbox.get_top_left()[1] + x * self.width_square_angle
                                 for x in xrange(0, int(math.ceil(self.width_square_count )) + 1)]
        self.horizontal_lines = [bbox.get_top_left()[0] - x * self.height_square_angle
                                 for x in xrange(0, int(math.ceil(self.height_square_count)) + 1)]

        # Compute the lists of labels
        self.vertical_labels   = [_gen_vertical_square_label(x)
                                  for x in xrange(0, int(math.ceil(self.width_square_count)))]
        self.horizontal_labels = [_gen_horizontal_square_label(x)
                                  for x in xrange(0, int(math.ceil(self.height_square_count)))]
        l.debug("vertical lines: %s" % self.vertical_lines)
        l.debug("horizontal lines: %s" % self.horizontal_lines)
        l.debug("vertical labels: %s" % self.vertical_labels)
        l.debug("horizontal labels: %s" % self.horizontal_labels)

def _humanize_street_label(street):

    def couple_compare(x,y):
        a = y[0] - x[0]
        if a:
            return a
        return y[1] - x[1]

    def distance(a,b):
        return (b[0]-a[0])**2 + (b[1]-a[1])**2

    name = street[0]
    squares = street[1]
    minx = min([x[0] for x in squares])
    maxx = max([x[0] for x in squares])
    miny = min([x[1] for x in squares])
    maxy = max([x[1] for x in squares])
    if len(squares) == 1:
        label = (_gen_vertical_square_label(squares[0][0]) +
                 _gen_horizontal_square_label(squares[0][1]))
    elif minx == maxx:
        label = ('%s%s-%s' % (_gen_vertical_square_label(minx),
                              _gen_horizontal_square_label(miny),
                              _gen_horizontal_square_label(maxy)))
    elif miny == maxy:
        label = ('%s-%s%s' % (_gen_vertical_square_label(minx),
                              _gen_vertical_square_label(maxx),
                              _gen_horizontal_square_label(miny)))
    elif (maxx - minx + 1) * (maxy - miny + 1) == len(squares):
        label = ('%s-%s%s-%s' % (_gen_vertical_square_label(minx),
                                 _gen_vertical_square_label(maxx),
                                 _gen_horizontal_square_label(miny),
                                 _gen_horizontal_square_label(maxy)))
    else:
        squares_x_first = sorted(squares, couple_compare)
        squares_y_first = sorted(squares, lambda x,y: couple_compare(y,x))
        if (distance(squares_x_first[0], squares_x_first[-1]) >
            distance(squares_y_first[0], squares_y_first[-1])):
            first = squares_x_first[0]
            last = squares_x_first[-1]
        else:
            first = squares_y_first[0]
            last = squares_y_first[-1]

        label = '%s%s...%s%s' % (_gen_vertical_square_label(first[0]),
                                 _gen_horizontal_square_label(first[1]),
                                 _gen_vertical_square_label(last[0]),
                                 _gen_horizontal_square_label(last[1]))
    return (name, label)

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

        self.streets = self.get_streets(db)
        l.debug('Streets: %s' % self.streets)

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

    def get_streets(self, db):

        """Get the list of streets in the bounding box, and for each
        street, the list of squares that it intersects.

        Returns a list of the form [(street_name, [[0, 1], [1, 1]]),
                                    (street2_name, [[1, 2]])]
        """
        cursor = db.cursor()
        cursor.execute("drop table if exists map_areas")
        cursor.execute("create table map_areas (x integer, y integer)")
        cursor.execute("select addgeometrycolumn('map_areas', 'geom', 4002, 'POLYGON', 2)")
        for i in xrange(0, int(math.ceil(self.mapdesc.width_square_count))):
            for j in xrange(0, int(math.ceil(self.mapdesc.height_square_count))):
                lon1 = self.boundingbox.get_top_left()[1] + i * self.mapdesc.width_square_angle
                lon2 = self.boundingbox.get_top_left()[1] + (i + 1) * self.mapdesc.width_square_angle
                lat1 = self.boundingbox.get_top_left()[0] - j * self.mapdesc.height_square_angle
                lat2 = self.boundingbox.get_top_left()[0] - (j + 1) * self.mapdesc.height_square_angle
                poly = "POLYGON((%f %f, %f %f, %f %f, %f %f, %f %f))" % \
                    (lon1, lat1, lon1, lat2, lon2, lat2, lon2, lat1, lon1, lat1)
                cursor.execute("""insert into map_areas (x, y, geom)
                                         values (%d, %d, st_geomfromtext('%s', 4002))""" % \
                                   (i, j, poly))
        db.commit()
        cursor.execute("""select name, textcat_all(x || ',' || y || ';')
                          from (select distinct name, x, y
                                from planet_osm_line
                                join map_areas
                                on st_intersects(way, st_transform(geom, 900913))
                                where name != '' and highway is not null)
                          as foo
                          group by name
                          order by name;""")
        sl = cursor.fetchall()
        sl = [(street[0].decode('utf-8'), [map(int, x.split(',')) for x in street[1].split(';')[:-1]]) for street in sl]
        return map(_humanize_street_label, sl)



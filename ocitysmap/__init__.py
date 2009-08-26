# -*- coding: utf-8; mode: Python -*-

"""OCitySMap.

Provide documentation here.
"""

__author__ = 'The Hackfest2009 team'
__version__ = '0.1'

import logging
import pgdb
import math
import re
import sys

l = logging.getLogger('ocitysmap')

EARTH_RADIUS = 6370986 # meters

APPELLATIONS = [ "Allée", "Avenue", "Boulevard", "Carrefour", "Chaussée",
                 "Chemin", "Cité", "Clos", "Côte", "Cour", "Cours", "Degré",
                 "Esplanade", "Impasse", "Liaison", "Mail", "Montée",
                 "Passage", "Place", "Placette", "Pont", "Promenade", "Quai",
                 "Résidence", "Rond-Point", "Rang", "Route", "Rue", "Ruelle",
                 "Square", "Traboule", "Traverse", "Venelle", "Voie",
                 "Rond-point" ]
DETERMINANTS = [ " des", " du", " de la", " de l'", " de", " d'", "" ]

SPACE_REDUCE = re.compile(r"\s+")
PREFIX_REGEXP = re.compile(r"^(?P<prefix>(%s)(%s)?)\s?\b(?P<name>.*)" %
                           ("|".join(APPELLATIONS),
                            "|".join(DETERMINANTS)), re.IGNORECASE)

class BaseOCitySMapError(Exception):
    """Base class for exceptions thrown by OCitySMap."""

class UnsufficientDataError(BaseOCitySMapError):
    """Not enough data in the OSM database to proceed."""

class BoundingBox:
    def __init__(self, lat1, long1, lat2, long2):
        (self._lat1, self._long1) = float(lat1), float(long1)
        (self._lat2, self._long2) = float(lat2), float(long2)

        # make sure lat1/long1 is the upper left, and the others the btm right
        if (self._lat1 < self._lat2):
            self._lat1, self._lat2 = self._lat2, self._lat1
        if (self._long1 > self._long2):
            self._long1, self._long2 = self._long2, self._long1

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

    def spheric_sizes(self):
        """Metric distances at the bounding box top latitude.
        Returns the tuple (metric_size_lat, metric_size_long)
        """
        delta_lat = abs(self._lat1 - self._lat2)
        delta_long = abs(self._long1 - self._long2)
        radius_lat = EARTH_RADIUS * math.cos(math.radians(self._lat1))
        return (EARTH_RADIUS * math.radians(delta_lat),
                radius_lat * math.radians(delta_long))

    def create_expanded(self, dlat, dlong):
        """Return a new bbox of the same size + dlat/dlong added on the sides"""
        return BoundingBox(self._lat1+dlat, self._long1 - dlong,
                           self._lat2-dlat, self._long2 + dlong)


import map_grid

def _gen_vertical_square_label(x):
    label = ''
    while x != -1:
        label = chr(ord('A') + x % 26) + label
        x /= 26
        x -= 1
    return label

def _gen_horizontal_square_label(x):
    return str(x + 1)

class GridDescriptor:
    def __init__(self, bbox, db):
        self.bbox = bbox
        height, width = bbox.spheric_sizes()

        # Compute number of squares, assumming a size of 500 meters
        # per square
        self.width_square_count  = width / 500
        self.height_square_count = height / 500

        # Compute the size in angles of the squares
        self.width_square_angle  = (abs(bbox.get_top_left()[1] -
                                        bbox.get_bottom_right()[1]) /
                                    self.width_square_count)
        self.height_square_angle = (abs(bbox.get_top_left()[0] -
                                        bbox.get_bottom_right()[0]) /
                                    self.height_square_count)

        # Compute the lists of longitudes and latitudes of the
        # horizontal and vertical lines delimiting the square
        self.vertical_lines   = [bbox.get_top_left()[1] +
                                 x * self.width_square_angle
                                 for x in xrange(0, int(math.ceil(self.width_square_count )) + 1)]
        self.horizontal_lines = [bbox.get_top_left()[0] -
                                 x * self.height_square_angle
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

    def generate_shape_file(self, filename):
        g = map_grid.GridFile(filename)
        for v in self.vertical_lines:
            g.add_vert_line(v)
        for h in self.horizontal_lines:
            g.add_horiz_line(h)
        g.flush()
        return g


def _humanize_street_label(street):
    """Creates a street label usable in the street list adjacent to the map
    (like 'Bréhat (Allée des)' from the street definition tuple."""

    def unprefix_street(name):
        name = name.strip()
        name = SPACE_REDUCE.sub(" ", name)
        return PREFIX_REGEXP.sub(r"\g<name> (\g<prefix>)", name)

    def couple_compare(x,y):
        a = y[0] - x[0]
        if a:
            return a
        return y[1] - x[1]

    def distance(a,b):
        return (b[0]-a[0])**2 + (b[1]-a[1])**2

    name = unprefix_street(street[0])
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
        self.griddesc = GridDescriptor(self.boundingbox, db)

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
        for i in xrange(0, int(math.ceil(self.griddesc.width_square_count))):
            for j in xrange(0, int(math.ceil(self.griddesc.height_square_count))):
                lon1 = (self.boundingbox.get_top_left()[1] +
                        i * self.griddesc.width_square_angle)
                lon2 = (self.boundingbox.get_top_left()[1] +
                        (i + 1) * self.griddesc.width_square_angle)
                lat1 = (self.boundingbox.get_top_left()[0] -
                        j * self.griddesc.height_square_angle)
                lat2 = (self.boundingbox.get_top_left()[0] -
                        (j + 1) * self.griddesc.height_square_angle)
                poly = ("POLYGON((%f %f, %f %f, %f %f, %f %f, %f %f))" %
                        (lon1, lat1, lon1, lat2, lon2,
                         lat2, lon2, lat1, lon1, lat1))
                cursor.execute("""insert into map_areas (x, y, geom)
                                  values (%d, %d, st_geomfromtext('%s', 4002))""" %
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
        sl = [(street[0], [map(int, x.split(','))
            for x in street[1].split(';')[:-1]]) for street in sl]
        return sorted(map(_humanize_street_label, sl),
                          lambda x, y: cmp(x[0].lower(), y[0].lower()))

    def render_into_files(self, osm_map_file, out_filenames):
        GRID_COLOR = '#8BB381'
        l.debug('rendering from %s to %s...' % (osm_map_file, out_filenames))
        g = self.griddesc.generate_shape_file('x.shp')

        bbox = self.boundingbox.create_expanded(self.griddesc.height_square_angle/2.,
                                                self.griddesc.width_square_angle/2.)
        city = map_grid.MapCanvas(osm_map_file, bbox)
        city.add_shapefile(g.get_filepath(), GRID_COLOR)
        l.debug('adding labels...')
        for idx, label in enumerate(self.griddesc.vertical_labels):
            x = self.griddesc.vertical_lines[idx] \
                + self.griddesc.width_square_angle/2.
            y = self.griddesc.horizontal_lines[0] \
                + self.griddesc.height_square_angle/4.
            city.add_label(x, y, label,
                           str_color = GRID_COLOR,
                           font_size = 25,
                           font_family = "DejaVu Sans Bold")
        for idx, label in enumerate(self.griddesc.horizontal_labels):
            x = self.griddesc.vertical_lines[0] \
                - self.griddesc.width_square_angle/4.
            y = self.griddesc.horizontal_lines[idx] \
                - self.griddesc.height_square_angle/2.
            city.add_label(x, y, label,
                           str_color = GRID_COLOR,
                           font_size = 25,
                           font_family = "DejaVu Sans Bold")
        l.debug('rendering map...')
        city.render_map()
        for fname in out_filenames:
            l.debug('saving as %s...' % fname)
            try:
                city.save_map(fname)
            except Exception, ex:
                print >>sys.stderr, \
                    "Error while rendering to %s: %s" % (fname, ex)
            except:
                print >>sys.stderr, \
                    "Error while rendering to %s." % (fname)

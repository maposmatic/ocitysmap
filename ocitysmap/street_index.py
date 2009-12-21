# -*- coding: utf-8; mode: Python -*-

# ocitysmap, city map and street index generator from OpenStreetMap data
# Copyright (C) 2009  David Decotigny
# Copyright (C) 2009  Frédéric Lehobey
# Copyright (C) 2009  David Mentré
# Copyright (C) 2009  Maxime Petazzoni
# Copyright (C) 2009  Thomas Petazzoni
# Copyright (C) 2009  Gaël Utard

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging, traceback
import sys, os, tempfile, pgdb, re, math, cairo, locale, gzip, csv
import ConfigParser
import i18n
from coords import BoundingBox

import map_canvas, grid, utils

from draw_utils import enclose_in_frame

LOG = logging.getLogger('ocitysmap')

class BaseOCitySMapError(Exception):
    """Base class for exceptions thrown by OCitySMap."""

class UnsufficientDataError(BaseOCitySMapError):
    """Not enough data in the OSM database to proceed."""

def _user_readable_label(squares):
    """Creates a label usable in the street index adjacent to the map
       from a square list."""

    def couple_compare(x,y):
        a = y[0] - x[0]
        if a:
            return a
        return y[1] - x[1]

    def distance(a,b):
        return (b[0]-a[0])**2 + (b[1]-a[1])**2

    minx = min([x[0] for x in squares])
    maxx = max([x[0] for x in squares])
    miny = min([x[1] for x in squares])
    maxy = max([x[1] for x in squares])
    if len(squares) == 1:
        label = (utils.gen_vertical_square_label(squares[0][0]) +
                 utils.gen_horizontal_square_label(squares[0][1]))
    elif minx == maxx:
        label = ('%s%s-%s' % (utils.gen_vertical_square_label(minx),
                              utils.gen_horizontal_square_label(miny),
                              utils.gen_horizontal_square_label(maxy)))
    elif miny == maxy:
        label = ('%s-%s%s' % (utils.gen_vertical_square_label(minx),
                              utils.gen_vertical_square_label(maxx),
                              utils.gen_horizontal_square_label(miny)))
    elif (maxx - minx + 1) * (maxy - miny + 1) == len(squares):
        label = ('%s-%s%s-%s' % (utils.gen_vertical_square_label(minx),
                                 utils.gen_vertical_square_label(maxx),
                                 utils.gen_horizontal_square_label(miny),
                                 utils.gen_horizontal_square_label(maxy)))
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

        label = '%s%s...%s%s' % (utils.gen_vertical_square_label(first[0]),
                                 utils.gen_horizontal_square_label(first[1]),
                                 utils.gen_vertical_square_label(last[0]),
                                 utils.gen_horizontal_square_label(last[1]))
    return label

class IndexPageGenerator:
    def __init__(self, streets, i18n):
        self.streets = streets
        self.i18n = i18n

    def _get_font_parameters(self, cr, fontsize):
        cr.select_font_face("DejaVu", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(fontsize * 1.2)
        heading_fascent, heading_fdescent, heading_fheight = cr.font_extents()[:3]

        cr.select_font_face("DejaVu", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(fontsize)
        fascent, fdescent, fheight, fxadvance, fyadvance = cr.font_extents()

        em = cr.text_extents("m")[2]

        widths = map(lambda x: cr.text_extents(x[1])[2] + cr.text_extents(x[2])[2], self.streets)
        maxwidth = max(widths)
        colwidth = maxwidth + 3 * em

        return {
            'colwidth' : colwidth,
            'heading_fascent' : heading_fascent,
            'heading_fheight' : heading_fheight,
            'fheight' : fheight,
            'em' : em,
            }

    def _fits_in_page(self, cr, paperwidth, paperheight, fontsize):
        fp = self._get_font_parameters(cr, fontsize)

        prevletter = u''
        heading_letter_count = 0
        for street in self.streets:
            if not self.i18n.first_letter_equal(street[0], prevletter):
                heading_letter_count += 1
                prevletter = street[0]

        colheight = len(self.streets) * fp['fheight'] + heading_letter_count * fp['heading_fheight']

        paperncols = math.floor(paperwidth / fp['colwidth'])
        if paperncols == 0:
            return False
        # Add a small space before/after each column
        colheight += paperncols * fp['fheight']
        colheight /= paperncols
        return colheight < paperheight

    def _compute_font_size(self, cr, paperwidth, paperheight):
        minfontsize = 6
        maxfontsize = 128

        if not self._fits_in_page(cr, paperwidth, paperheight, minfontsize):
            print "Index does not fit even with font size %d" % minfontsize
            sys.exit(1)

        while maxfontsize - minfontsize != 1:
            meanfontsize = int((maxfontsize + minfontsize) / 2)
            if self._fits_in_page(cr, paperwidth, paperheight, meanfontsize):
                minfontsize = meanfontsize
            else:
                maxfontsize = meanfontsize

        return minfontsize

    def render(self, cr, paperwidth, paperheight):
        cr.set_source_rgb(1, 1, 1)
        cr.paint()
        cr.set_source_rgb(0.0, 0.0, 0.0)

        fontsize = self._compute_font_size(cr, paperwidth, paperheight)

        fp = self._get_font_parameters(cr, fontsize)
        heading_fheight = fp['heading_fheight']
        heading_fascent = fp['heading_fascent']
        fheight = fp['fheight']
        colwidth = fp['colwidth']
        em = fp['em']

        remaining = paperwidth % colwidth
        colwidth += (remaining / int(paperwidth / colwidth))

        y = 0
        x = em
        prevletter = u''
        for street in self.streets:
            # Letter label
            firstletter = street[0]
            if not self.i18n.first_letter_equal(firstletter, prevletter):
                # Make sure we have no orphelin heading letter label at the
                # end of a column
                if y + heading_fheight + fheight > paperheight:
                    y = 0
                    x += colwidth
                # Reserve height for the heading letter label
                y += heading_fheight

                cr.set_source_rgb(0.9, 0.9, 0.9)
                cr.rectangle(x, y - heading_fascent, colwidth - em, heading_fheight)
                cr.fill()

                cr.set_source_rgb(0, 0, 0)

                # Draw the heading letter label
                cr.select_font_face("DejaVu", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
                cr.set_font_size(fontsize * 1.2)
                w = cr.text_extents(firstletter)[2]
                indent = (colwidth - 2 * em - w) / 2
                cr.move_to(x + indent, y)
                cr.show_text(firstletter)
                prevletter = firstletter

            # Reserve height for the street
            y += fheight
            cr.select_font_face("DejaVu", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(fontsize)
            # Compute length of the dashed line between the street name and
            # the squares label
            street_name_width = cr.text_extents(street[1])[4]
            squares_label_width = cr.text_extents(street[2])[2]
            line_width = colwidth - street_name_width - squares_label_width - 2 * em
            # Draw street name
            cr.move_to(x, y)
            cr.show_text(street[1])
            # Draw dashed line
            strokewidth = max(fontsize / 12, 1)
            cr.set_line_width(strokewidth)
            cr.set_dash([ strokewidth, strokewidth * 2 ])
            cr.move_to(x + street_name_width + em / 2, y - 0.1 * em)
            cr.rel_line_to(line_width, 0)
            cr.stroke()
            # Draw squares label
            cr.move_to(x + colwidth - em - squares_label_width, y)
            cr.show_text(street[2])
            if y + fheight > paperheight:
                y = 0
                x += colwidth

class OCitySMap:
    SELECTED_AMENITIES = [
        ("Places of worship", "place_of_worship", "Places of worship"),
        ("Education", "kindergarten", "Kindergarten"),
        ("Education", "school", "School"),
        ("Education", "college", "College"),
        ("Education", "university", "University"),
        ("Education", "library", "Library"),
        ("Public buildings", "townhall", "Town hall"),
        ("Public buildings", "post_office", "Post office"),
        ("Public buildings", "police", "Police")]

    def __init__(self, config_file=None, city_name=None, boundingbox=None,
                 osmid=None, language=None):
        """Creates a new OCitySMap renderer instance for the given city.

        Args:
            config_file: location of the config file
            city_name (string): The name of the city we're created the map of.
            boundingbox (BoundingBox): An optional BoundingBox object defining
                the city's bounding box. If not given, OCitySMap will try to
                guess the bounding box from the OSM data. An UnsufficientDataError
                exception will be raised in the bounding box can't be guessed.
            osmid (integer): The OSM id of the polygon of the city to render
        """

        optcnt = 0
        for var in city_name, boundingbox, osmid:
            if var:
                optcnt += 1

        assert optcnt == 1

        (self.city_name, self.boundingbox, self.osmid) = (city_name, boundingbox, osmid)

        self.i18n = i18n.language_map[language]
        LOG.info('Language ' + self.i18n.language_code())

        if self.city_name:
            LOG.info('OCitySMap renderer for %s.' % self.city_name)
        elif self.boundingbox:
            LOG.info('OCitySMap renderer for %s.' % self.boundingbox)
        else:
            LOG.info('OCitySMap renderer for %s.' % self.osmid)

        LOG.info('Reading config file.')
        self.parser = ConfigParser.RawConfigParser()
        if config_file:
            config_files = [config_file]
        else:
            config_files = ['/etc/ocitysmap.conf',
                            os.getenv('HOME') + '/.ocitysmap.conf']
        if not self.parser.read(config_files):
            raise IOError, 'Failed to load the config file'
        datasource = dict(self.parser.items('datasource'))

        db = pgdb.connect('Notre Base', datasource['user'],
                          datasource['password'], datasource['host'],
                          datasource['dbname'])

        if self.city_name:
            self.boundingbox = self.find_bounding_box_by_name(db, self.city_name)
        elif self.osmid:
            self.boundingbox = self.find_bounding_box_by_osmid(db, self.osmid)

        self.griddesc = grid.GridDescriptor(self.boundingbox, db)

        self.gen_map_areas(db)

        if self.osmid:
            self.streets = self.get_streets_by_osmid(db, self.osmid)
            self.amenities = self.get_amenities_by_osmid(db, self.osmid)
        elif self.city_name:
            self.streets = self.get_streets_by_name(db, self.city_name)
            self.amenities = self.get_amenities_by_name(db, self.city_name)
        else:
            self.streets = self.get_streets_by_name(db, None)
            self.amenities = self.get_amenities_by_name(db, None)

        if self.city_name:
            self.contour = self.get_city_contour_by_name(db, self.city_name)
        elif self.osmid:
            self.contour = self.get_city_contour_by_osmid(db, self.osmid)
        else:
            self.contour = None

        LOG.info('City bounding box is %s.' % str(self.boundingbox))

    def find_bounding_box_by_name(self, db, name):
        """Find the bounding box of a city from its name.

        Args:
            db: connection to the database
            name (string): The city name.
        Returns a BoundingBox object describing the bounding box around
        the given city.
        """

        LOG.info('Looking for bounding box around %s...' % name)

        cursor = db.cursor()
        cursor.execute("""select st_astext(st_transform(st_envelope(way), 4002))
                          from planet_osm_line
                          where boundary='administrative' and
                                admin_level='8' and
                                name='%s';""" % \
                           pgdb.escape_string(name.encode('utf-8')))
        records = cursor.fetchall()
        if not records:
            raise UnsufficientDataError, "Wrong city name (%s) or missing administrative boundary in database!" % (repr(name))

        return BoundingBox.parse_wkt(records[0][0])

    def find_bounding_box_by_osmid(self, db, osmid):
        """Find the bounding box of a city from its OSM id.

        Args:
            db: connection to the database
            osmid (integer): The city OSM id.
        Returns a BoundingBox object describing the bounding box around
        the given city.
        """

        LOG.info('Looking for bounding box around %s...' % osmid)

        cursor = db.cursor()
        cursor.execute("""select st_astext(st_transform(st_envelope(way), 4002))
                          from planet_osm_polygon
                          where osm_id=%d;""" % \
                           osmid)
        records = cursor.fetchall()
        if not records:
            raise UnsufficientDataError, "Wrong OSM id (%s) !" % (repr(osmid))

        return BoundingBox.parse_wkt(records[0][0])

    _regexp_contour = re.compile('^POLYGON\(\(([^)]*)\),\(([^)]*)\)\)$')
    _regexp_coords  = re.compile('^(\S*)\s+(\S*)$')

    def parse_city_contour(self, contour):
        LOG.info("Parsing contour: %s" % contour)
        try:
            cell00 = contour[0][0].strip()
        except (KeyError,IndexError,AttributeError):
            LOG.error("Invalid DB contour structure")
            return None

        # Got nothing usable
        if not cell00:
            return None

        # Parse the answer, in order to add a margin around the area
        prev_locale = locale.getlocale(locale.LC_ALL)
        locale.setlocale(locale.LC_ALL, "C")
        try:
            matches = self._regexp_contour.match(cell00)
            if not matches:
                print "Area not conformant"
                LOG.error("Area not conformant")
                return None
            scoords, inside = matches.groups()

            # Determine bbox envelope
            xmin, ymin, ymax, xmax = (None,)*4
            lcoords = scoords.split(',')
            if len(lcoords) != 5:
                print "Coords look atypical"
                LOG.warning("Coords look atypical: %s", lcoords)
            for scoord in lcoords:
                matches = self._regexp_coords.match(scoord)
                y,x = map(float,matches.groups())
                if (xmax is None) or xmax < x: xmax = x
                if (xmin is None) or xmin > x: xmin = x
                if (ymax is None) or ymax < y: ymax = y
                if (ymin is None) or ymin > y: ymin = y

            # Add one degree around the area
            xmin -= 1. ; xmax += 1.
            ymin -= 1. ; ymax += 1.
            l = "POLYGON((%f %f, %f %f, %f %f, %f %f, %f %f),(%s))" \
                % (ymin, xmin, ymin, xmax, ymax, xmax, ymax, xmin, ymin, xmin,
                  inside)
            print l
            return l
        except:
            # Regexp error: area is not a "simple" polygon
            LOG.exception("Unexpected exception")
            return None
        finally:
            locale.setlocale(locale.LC_ALL, prev_locale)

    def get_city_contour_by_name(self, db, city):
        assert city is not None
        cursor = db.cursor()
        cursor.execute("""select st_astext(st_transform(
                                    st_difference(st_envelope(way),
                                                  st_buildarea(way)), 4002))
                              from planet_osm_line
                              where boundary='administrative'
                                 and admin_level='8' and name='%s';""" % \
                               pgdb.escape_string(city.encode('utf-8')))
        contour = cursor.fetchall()
        return self.parse_city_contour(contour)

    def get_city_contour_by_osmid(self, db, osmid):
        cursor = db.cursor()
        cursor.execute("""select st_astext(st_transform(
                                    st_difference(st_envelope(way),
                                                  st_buildarea(way)), 4002))
                              from planet_osm_polygon
                              where osm_id=%d;""" % \
                           osmid)
        contour = cursor.fetchall()
        return self.parse_city_contour(contour)

    # This function creates a map_areas table that contains the list
    # of the squares used to divide the global city map. Each entry of
    # this table represent one of these square, with x, y being the
    # square identifiers, and geom being its geographical
    # geometry. This temporary table allows to conveniently perform a
    # joint with the planet_osm_line or planet_osm_polygon tables, so
    # that getting the list of squares for a given set of streets can
    # be performed in a single query
    def gen_map_areas(self, db):
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

    # Given a list of street and their corresponding squares, do some
    # cleanup and pass it through the internationalization layer to
    # get proper sorting, filtering of common prefixes, etc. Returns a
    # updated street list.
    def humanize_street_list(self, sl):
        # We transform the string representing the squares list into a
        # Python list
        sl = [( unicode(street[0].decode("utf-8")),
                [ map(int, x.split(',')) for x in street[1].split(';')[:-1] ] )
              for street in sl]

        # Street prefixes are postfixed, a human readable label is
        # built to represent the list of squares, and the list is
        # alphabetically-sorted.
        prev_locale = locale.getlocale(locale.LC_COLLATE)
        locale.setlocale(locale.LC_COLLATE, self.i18n.language_code())

        def _humanize_street_label(street):
            return (self.i18n.user_readable_street(street[0]),
                    _user_readable_label(street[1]))

        try:
            sl = sorted(map(_humanize_street_label, sl),
                        lambda x, y: locale.strcoll(x[0].lower(), y[0].lower()))
        finally:
            locale.setlocale(locale.LC_COLLATE, prev_locale)

        # Add the first letter of the street name as category
        sl = [(street[0][0], street[0], street[1]) for street in sl]

        return sl

    def get_streets_by_name(self, db, city):

        """Get the list of streets in the administrative area if city is
        defined or in the bounding box otherwise, and for each
        street, the list of squares that it intersects.

        Returns a list of the form [(street_name, 'A-B1'),
                                    (street2_name, 'B3')]
        """

        cursor = db.cursor()

        # pgdb.escape_string() doesn't like None strings, and when the
        # city is not passed, we don't want to match any existing
        # city. So the empty string doesn't sound like a good
        # candidate, and the "-1" string is probably better.
        #
        # TODO: improve the following request to remove this hack
        if city is None:
            city = "-1"

        # The inner select query creates the list of (street, square)
        # for all the squares in the temporary map_areas table. The
        # left_join + the test on cities_area is used to filter out
        # the streets outside the city administrative boundaries. The
        # outer select builds an easy to parse list of the squares for
        # each street.
        #
        # A typical result entry is:
        #  [ "Rue du Moulin", "0,1;1,2;1,3" ]
        #
        # REMARKS:
        #
        #  * The cities_area view is created once for all at
        #    installation. It associates the name of a city with the
        #    area covering it. As of today, only parts of the french
        #    cities have these administrative boundaries available in
        #    OSM. When available, this boundary is used to filter out
        #    the streets that are not inside the selected city but
        #    still in the bounding box rendered on the map. So these
        #    streets will be shown but not listed in the street index.
        #
        #  * The textcat_all() aggregate must also be installed in the
        #    database
        #
        # See ocitysmap-init.sql for details
        cursor.execute("""select name, textcat_all(x || ',' || y || ';')
                          from (select distinct name, x, y
                                from planet_osm_line
                                join map_areas
                                on st_intersects(way, st_transform(geom, 900913))
                                left join cities_area_by_name on city='%s'
                                where trim(name) != '' and highway is not null
                                and case when cities_area_by_name.area is null
                                then
                                  true
                                else
                                  st_intersects(way, cities_area_by_name.area)
                                end)
                          as foo
                          group by name
                          order by name;""" % \
                           pgdb.escape_string(city.encode('utf-8')))

        sl = cursor.fetchall()

        return self.humanize_street_list(sl)

    def get_streets_by_osmid(self, db, osmid):

        """Get the list of streets in the administrative area if city is
        defined or in the bounding box otherwise, and for each
        street, the list of squares that it intersects.

        Returns a list of the form [(street_name, 'A-B1'),
                                    (street2_name, 'B3')]
        """

        cursor = db.cursor()

        # The inner select query creates the list of (street, square)
        # for all the squares in the temporary map_areas table. The
        # left_join + the test on cities_area is used to filter out
        # the streets outside the city administrative boundaries. The
        # outer select builds an easy to parse list of the squares for
        # each street.
        #
        # A typical result entry is:
        #  [ "Rue du Moulin", "0,1;1,2;1,3" ]
        #
        # REMARKS:
        #
        #  * The cities_area view is created once for all at
        #    installation. It associates the name of a city with the
        #    area covering it. As of today, only parts of the french
        #    cities have these administrative boundaries available in
        #    OSM. When available, this boundary is used to filter out
        #    the streets that are not inside the selected city but
        #    still in the bounding box rendered on the map. So these
        #    streets will be shown but not listed in the street index.
        #
        #  * The textcat_all() aggregate must also be installed in the
        #    database
        #
        # See ocitysmap-init.sql for details
        cursor.execute("""select name, textcat_all(x || ',' || y || ';')
                          from (select distinct name, x, y
                                from planet_osm_line
                                join map_areas
                                on st_intersects(way, st_transform(geom, 900913))
                                left join cities_area_by_osmid on cities_area_by_osmid.osm_id=%d
                                where trim(name) != '' and highway is not null
                                and case when cities_area_by_osmid.area is null
                                then
                                  true
                                else
                                  st_intersects(way, cities_area_by_osmid.area)
                                end)
                          as foo
                          group by name
                          order by name;""" % \
                           osmid)

        sl = cursor.fetchall()

        return self.humanize_street_list(sl)

    # Given a list of amenities and their corresponding squares, do some
    # cleanup and pass it through the internationalization layer to
    # get proper sorting, filtering of common prefixes, etc. Returns a
    # updated amenity list.
    def humanize_amenity_list(self, am):
        # We transform the string representing the squares list into a
        # Python list
        am = [( unicode(amenity[0].decode("utf-8")),
		unicode(amenity[1].decode("utf-8")),
                [ map(int, x.split(',')) for x in amenity[2].split(';')[:-1] ] )
              for amenity in am]

        # Street prefixes are postfixed and a human readable label is
        # built to represent the list of squares.
        def _humanize_amenity_label(amenity):
            return (amenity[0], amenity[1],
                    _user_readable_label(amenity[2]))
        
        am = map(_humanize_amenity_label, am)

        return am

    def get_amenities_by_name(self, db, city):

        """Get the list of amenities in the administrative area if city is
        defined or in the bounding box otherwise, and for each
        amenity, the list of squares that it intersects.

        Returns a list of the form [(category, name, 'A-B1'),
                                    (category, name, 'B3')]
        """

        cursor = db.cursor()

        # pgdb.escape_string() doesn't like None strings, and when the
        # city is not passed, we don't want to match any existing
        # city. So the empty string doesn't sound like a good
        # candidate, and the "-1" string is probably better.
        #
        # TODO: improve the following request to remove this hack
        if city is None:
            city = "-1"

        # The inner select query creates the list of (amenity, square)
        # for all the squares in the temporary map_areas table. The
        # left_join + the test on cities_area is used to filter out
        # the amenities outside the city administrative boundaries. The
        # outer select builds an easy to parse list of the squares for
        # each amenity.
        #
        # A typical result entry is:
        #  [ "Places of worship", "Basilique Sainte Germaine", "0,1;1,2;1,3" ]
        #
        # REMARKS:
        #
        #  * The cities_area view is created once for all at
        #    installation. It associates the name of a city with the
        #    area covering it. As of today, only parts of the french
        #    cities have these administrative boundaries available in
        #    OSM. When available, this boundary is used to filter out
        #    the streets that are not inside the selected city but
        #    still in the bounding box rendered on the map. So these
        #    streets will be shown but not listed in the street index.
        #
        #  * The textcat_all() aggregate must also be installed in the
        #    database
        #
        # See ocitysmap-init.sql for details
        al = []
        for cat, amenity, human in self.SELECTED_AMENITIES:
            cursor.execute("""select '%s', name, textcat_all(x || ',' || y || ';')
                              from (select distinct amenity, name, x, y
                                    from planet_osm_point
                                    join map_areas
                                    on st_intersects(way, st_transform(geom, 900913))
                                    left join cities_area_by_name on city='%s'
                                    where amenity = '%s'
                                    and case when cities_area_by_name.area is null
                                    then
                                      true
                                    else
                                      st_intersects(way, cities_area_by_name.area)
                                    end)
                              as foo
                              group by amenity, name
                              order by amenity, name;""" % \
                              (cat, pgdb.escape_string(city.encode('utf-8')), amenity))
            sub_al = cursor.fetchall()
            for a in sub_al:
                if a[1] == None:
                    a[1] = human
            sub_al = self.humanize_amenity_list(sub_al)
            al.extend(sub_al)

        return al

    def get_amenities_by_osmid(self, db, osmid):

        """Get the list of amenities in the administrative area if city is
        defined or in the bounding box otherwise, and for each
        amenity, the list of squares that it intersects.

        Returns a list of the form [(category, name, 'A-B1'),
                                    (category, name2, 'B3')]
        """

        cursor = db.cursor()

        # The inner select query creates the list of (amenity, square)
        # for all the squares in the temporary map_areas table. The
        # left_join + the test on cities_area is used to filter out
        # the streets outside the city administrative boundaries. The
        # outer select builds an easy to parse list of the squares for
        # each amenity.
        #
        # A typical result entry is:
        #  [ "Place of worship", "Basilique Sainte Germaine", "0,1;1,2;1,3" ]
        #
        # REMARKS:
        #
        #  * The cities_area view is created once for all at
        #    installation. It associates the name of a city with the
        #    area covering it. As of today, only parts of the french
        #    cities have these administrative boundaries available in
        #    OSM. When available, this boundary is used to filter out
        #    the streets that are not inside the selected city but
        #    still in the bounding box rendered on the map. So these
        #    streets will be shown but not listed in the street index.
        #
        #  * The textcat_all() aggregate must also be installed in the
        #    database
        #
        # See ocitysmap-init.sql for details
        al = []
        for cat, amenity, human in self.SELECTED_AMENITIES:
            cursor.execute("""select '%s', name, textcat_all(x || ',' || y || ';')
                              from (select distinct amenity, name, x, y
                                    from planet_osm_point
                                    join map_areas
                                    on st_intersects(way, st_transform(geom, 900913))
                                    left join cities_area_by_osmid on cities_area_by_osmid.osm_id=%d
                                    where amenity = '%s'
                                    and case when cities_area_by_osmid.area is null
                                    then
                                      true
                                    else
                                      st_intersects(way, cities_area_by_osmid.area)
                                    end)
                              as foo
                              group by amenity, name
                              order by amenity, name;""" % \
                              (cat, osmid, amenity))
            sub_al = cursor.fetchall()
            for a in sub_al:
                if a[1] == None:
                    a[1] = human
            sub_al = self.humanize_amenity_list(sub_al)
            al.extend(sub_al)

        return al

    def _render_one_prefix(self, title, output_prefix, file_type,
                           paperwidth, paperheight):
        file_type   = file_type.lower()
        frame_width = int(max(paperheight / 20., 30))

        output_filename = "%s_index.%s" % (output_prefix, file_type)
        LOG.debug("rendering " + output_filename + "...")

        generator = IndexPageGenerator(self.streets + self.amenities, self.i18n)

        if file_type == 'xml':
            LOG.debug('not rendering index as xml (not supported)')
            return

        elif file_type == 'csv':
            try:
                writer = csv.writer(open(output_filename, 'w'))
            except Exception,ex:
                LOG.warning('error while opening destination file %s: %s'
                          % (output_filename, ex))
            else:
                copyright_notice = (u'© 2009 MapOSMatic/ocitysmap authors. '
                                    u'Map data © 2009 OpenStreetMap.org '
                                    u'and contributors (CC-BY-SA)').encode('UTF-8')
                if title is not None:
                    writer.writerow(['# (UTF-8)', title.encode('UTF-8'), copyright_notice])
                else:
                    writer.writerow(['# (UTF-8)', '', copyright_notice])

                for street in self.streets:
                    writer.writerow([e.encode('UTF-8') for e in street])
            return

        if file_type in ('png', 'png24'):
            cairo_factory = \
                lambda w,h: cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)

        elif file_type == 'svg':
            cairo_factory = lambda w,h: cairo.SVGSurface(output_filename, w, h)

        elif file_type == 'svgz':
            def cairo_factory(w,h):
                gz = gzip.GzipFile(output_filename, 'wb')
                return cairo.SVGSurface(gz, w, h)

        elif file_type == 'pdf':
            cairo_factory = lambda w,h: cairo.PDFSurface(output_filename, w, h)

        elif file_type == 'ps':
            cairo_factory = lambda w,h: cairo.PSSurface(output_filename, w, h)

        else:
            raise ValueError('Unsupported output format: %s' % file_type)

        if title is not None:
            surface = cairo_factory(paperwidth + frame_width*2,
                                    paperheight + frame_width*2)
            enclose_in_frame(lambda ctx: generator.render(ctx, paperwidth,
                                                          paperheight),
                             paperwidth, paperheight,
                             title, surface,
                             paperwidth + frame_width*2,
                             paperheight + frame_width*2, frame_width)
        else:
            surface = cairo_factory(paperwidth, paperheight)
            ctx = cairo.Context(surface)
            generator.render(ctx, paperwidth, paperheight)

        surface.flush()

        if file_type in ('png', 'png24'):
            surface.write_to_png(output_filename)

        surface.finish()

    def render_index(self, title, output_prefix, output_format,
                     paperwidth, paperheight):

        if not self.streets:
            LOG.warning('No street to write to index')
            return

        for fmt in output_format:
            LOG.debug('saving %s.%s...' % (output_prefix, fmt))
            try:
                self._render_one_prefix(title, output_prefix, fmt,
                                        paperwidth, paperheight)
            except:
                print >>sys.stderr, \
                    "Error while rendering %s:" % (fmt)
                traceback.print_exc()
                # Not fatal !


    def render_map_into_files(self, title,
                              out_prefix, out_formats,
                              zoom_factor):
        """
        Render the current boundingbox into the destination files.
        @param title (string/None) title of the map, or None: no frame
        @param out_prefix (string) prefix to use for generated files
        @param out_formats (iterable of strings) format of image files
        to generate
        @param zoom_factor None, a tuple (pixels_x, pixel_y) or
        'zoom:X' with X an integer [1..18]
        returns the MApnik map object used to render the map
        """
        # Create a temporary dir for the shapefiles and call _render_into_files

        osm_map_file = self.parser.get('mapnik', 'map')
        if not os.path.exists(osm_map_file):
            raise IOError, 'Invalid path to the osm.xml file (%s)' % osm_map_file

        tmpdir = tempfile.mkdtemp(prefix='ocitysmap')
        LOG.debug('rendering tmp dir: %s' % tmpdir)
        try:
            return self._render_map_into_files(tmpdir, osm_map_file,
                                               title,
                                               out_prefix, out_formats,
                                               zoom_factor)
        finally:
            for root, dirs, files in os.walk(tmpdir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(tmpdir)

    def _render_map_into_files(self, tmpdir,
                               osm_map_file, title, out_prefix, out_formats,
                               zoom_factor):
        # Does the real job of rendering the map
        GRID_COLOR = '#8BB381'
        LOG.debug('rendering from %s to %s.%s...' % (osm_map_file,
                                                   out_prefix,
                                                   out_formats))
        bbox = self.boundingbox.create_expanded(self.griddesc.height_square_angle*.7,
                                                self.griddesc.width_square_angle*.7)
        LOG.debug('bbox is: %s' % bbox)
        city = map_canvas.MapCanvas(osm_map_file, bbox, zoom_factor)
        LOG.debug('adding labels...')

        # Add the greyed-out area
        if self.contour is not None:
            path_contour = os.path.join(tmpdir, 'contour.shp')
            map_canvas.create_shapefile_polygon_from_wkt(path_contour,
                                                         self.contour)
            city.add_shapefile(path_contour, str_color = 'grey', alpha = .1)

        # Determine font size, depending on the zoom factor
        half_km_in_pixels = city.one_meter_in_pixels * 500.
        LOG.debug('500m = %f pixels' % half_km_in_pixels)
        if half_km_in_pixels < 10:
            font_size  = 6
            line_width = 1
        elif half_km_in_pixels < 25:
            font_size = 10
            line_width = 1
        elif half_km_in_pixels < 50:
            font_size = 20
            line_width = 2
        elif half_km_in_pixels < 100:
            font_size = 40
            line_width = 3
        elif half_km_in_pixels < 150:
            font_size = 65
            line_width = 4
        elif half_km_in_pixels < 200:
            font_size = 80
            line_width = 5
        elif half_km_in_pixels < 400:
            font_size = 120
            line_width = 6
        else:
            font_size = 200
            line_width = 7

        # Add the grid
        g = self.griddesc.generate_shape_file(os.path.join(tmpdir,
                                                           'grid.shp'), bbox)
        city.add_shapefile(g.get_filepath(), GRID_COLOR, .6, line_width)

        # Add the labels
        for idx, label in enumerate(self.griddesc.vertical_labels):
            x = self.griddesc.vertical_lines[idx] \
                + self.griddesc.width_square_angle/2.
            y = self.griddesc.horizontal_lines[0] \
                + self.griddesc.height_square_angle*.35
            city.add_label(x, y, label,
                           str_color = GRID_COLOR,
                           alpha = .9,
                           font_size = font_size,
                           font_family = "DejaVu Sans Bold")
        for idx, label in enumerate(self.griddesc.horizontal_labels):
            x = self.griddesc.vertical_lines[0] \
                - self.griddesc.width_square_angle*.35
            y = self.griddesc.horizontal_lines[idx] \
                - self.griddesc.height_square_angle/2.
            city.add_label(x, y, label,
                           str_color = GRID_COLOR,
                           alpha = .9,
                           font_size = font_size,
                           font_family = "DejaVu Sans Bold")

        # Add the scale
        T = self.griddesc.generate_scale_shape_file(os.path.join(tmpdir,
                                                                 'scale.shp'),
                                                    bbox.get_bottom_right()[0])
        if T is not None:
            s, lat, lg = T
            city.add_shapefile(s.get_filepath(), 'black', .9, 1)
            city.add_label(lg, lat, "500m", font_size = 16, str_color = 'black')

        # Determine parameters
        try:
            copyright_logo = self.parser.get('ocitysmap', 'copyright_logo')
        except Exception:
            copyright_logo = None

        # Rendering...
        LOG.debug('rendering map...')
        _map = city.render_map()
        for fmt in out_formats:
            LOG.debug('saving %s.%s...' % (out_prefix, fmt))
            try:
                city.save_map("%s.%s" % (out_prefix, fmt),
                              title,
                              file_type = fmt,
                              copyright_logo_png = copyright_logo)
            except:
                print >>sys.stderr, \
                    "Error while rendering %s:" % (fmt)
                traceback.print_exc()
                # Not fatal !

        return _map

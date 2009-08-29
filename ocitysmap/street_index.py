# -*- coding: utf-8; mode: Python -*-

import logging, traceback
import sys, os, tempfile, pgdb, re, math, cairo, locale, gzip, csv
import ConfigParser
from coords import BoundingBox

import map_canvas, grid, utils

from draw_utils import enclose_in_frame

l = logging.getLogger('ocitysmap')

APPELLATIONS = [ u"Allée", u"Avenue", u"Boulevard", u"Carrefour", u"Chaussée",
                 u"Chemin", u"Cité", u"Clos", u"Côte", u"Cour", u"Cours", u"Degré",
                 u"Esplanade", u"Impasse", u"Liaison", u"Mail", u"Montée",
                 u"Passage", u"Place", u"Placette", u"Pont", u"Promenade", u"Quai",
                 u"Résidence", u"Rond-Point", u"Rang", u"Route", u"Rue", u"Ruelle",
                 u"Square", u"Traboule", u"Traverse", u"Venelle", u"Voie",
                 u"Rond-point" ]
DETERMINANTS = [ u" des", u" du", u" de la", u" de l'", u" de", u" d'", u"" ]

SPACE_REDUCE = re.compile(r"\s+")
PREFIX_REGEXP = re.compile(r"^(?P<prefix>(%s)(%s)?)\s?\b(?P<name>.*)" %
                           ("|".join(APPELLATIONS),
                            "|".join(DETERMINANTS)), re.IGNORECASE | re.UNICODE)
# for IndexPageGenerator._upper_unaccent_string
E_ACCENT = re.compile(ur"[éèêëẽ]", re.IGNORECASE | re.UNICODE)
I_ACCENT = re.compile(ur"[íìîïĩ]", re.IGNORECASE | re.UNICODE)
A_ACCENT = re.compile(ur"[áàâäã]", re.IGNORECASE | re.UNICODE)
O_ACCENT = re.compile(ur"[óòôöõ]", re.IGNORECASE | re.UNICODE)
U_ACCENT = re.compile(ur"[úùûüũ]", re.IGNORECASE | re.UNICODE)

class BaseOCitySMapError(Exception):
    """Base class for exceptions thrown by OCitySMap."""

class UnsufficientDataError(BaseOCitySMapError):
    """Not enough data in the OSM database to proceed."""

def _humanize_street_label(street):
    """Creates a street label usable in the street list adjacent to the map
    (like 'Bréhat (Allée des)' from the street definition tuple."""

    def unprefix_street(name):
        name = name.strip()
        name = SPACE_REDUCE.sub(" ", name)
        name = PREFIX_REGEXP.sub(r"\g<name> (\g<prefix>)", name)
        return name

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
    return (name, label)

class IndexPageGenerator:
    def __init__(self, streets):
        self.streets = streets

    def _get_font_parameters(self, cr, fontsize):
        cr.select_font_face("DejaVu", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(fontsize * 1.2)
        heading_fascent, heading_fdescent, heading_fheight = cr.font_extents()[:3]

        cr.select_font_face("DejaVu", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(fontsize)
        fascent, fdescent, fheight, fxadvance, fyadvance = cr.font_extents()

        em = cr.text_extents("m")[2]

        widths = map(lambda x: cr.text_extents(x[0])[2] + cr.text_extents(x[1])[2], self.streets)
        maxwidth = max(widths)
        colwidth = maxwidth + 3 * em

        return {
            'colwidth' : colwidth,
            'heading_fascent' : heading_fascent,
            'heading_fheight' : heading_fheight,
            'fheight' : fheight,
            'em' : em,
            }

    def _upper_unaccent_string(self, s):
        s = E_ACCENT.sub("e", s)
        s = I_ACCENT.sub("i", s)
        s = A_ACCENT.sub("a", s)
        s = O_ACCENT.sub("o", s)
        s = U_ACCENT.sub("u", s)
        return s.upper()

    def _equal_without_accent(self, a, b):
        return self._upper_unaccent_string(a) == self._upper_unaccent_string(b)

    def _fits_in_page(self, cr, paperwidth, paperheight, fontsize):
        fp = self._get_font_parameters(cr, fontsize)

        prevletter = u''
        heading_letter_count = 0
        for street in self.streets:
            if not self._equal_without_accent(street[0][0], prevletter):
                heading_letter_count += 1
                prevletter = street[0][0]

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
            firstletter = street[0][0]
            if not self._equal_without_accent(firstletter, prevletter):
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
            street_name_width = cr.text_extents(street[0])[4]
            squares_label_width = cr.text_extents(street[1])[2]
            line_width = colwidth - street_name_width - squares_label_width - 2 * em
            # Draw street name
            cr.move_to(x, y)
            cr.show_text(street[0])
            # Draw dashed line
            strokewidth = max(fontsize / 12, 1)
            cr.set_line_width(strokewidth)
            cr.set_dash([ strokewidth, strokewidth * 2 ])
            cr.move_to(x + street_name_width + em / 2, y - 0.1 * em)
            cr.rel_line_to(line_width, 0)
            cr.stroke()
            # Draw squares label
            cr.move_to(x + colwidth - em - squares_label_width, y)
            cr.show_text(street[1])
            if y + fheight > paperheight:
                y = 0
                x += colwidth

class OCitySMap:
    def __init__(self, config_file=None, city_name=None, boundingbox=None):
        """Creates a new OCitySMap renderer instance for the given city.

        Args:
            config_file: location of the config file
            city_name (string): The name of the city we're created the map of.
            boundingbox (BoundingBox): An optional BoundingBox object defining
                the city's bounding box. If not given, OCitySMap will try to
                guess the bounding box from the OSM data. An UnsufficientDataError
                exception will be raised in the bounding box can't be guessed.
        """
        assert bool(city_name) ^ bool(boundingbox)
        (self.city_name, self.boundingbox) = (city_name, boundingbox)

        if self.city_name:
            l.info('OCitySMap renderer for %s.' % self.city_name)
        else:
            l.info('OCitySMap renderer for %s.' % self.boundingbox)
               
        l.info('Reading config file.')
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
                                                                 
        if not self.boundingbox:
            self.boundingbox = self.find_bounding_box(db, self.city_name)

        self.griddesc = grid.GridDescriptor(self.boundingbox, db)

        self.streets = self.get_streets(db, self.city_name)
        self.contour = self.get_city_contour(db, self.city_name)

        l.info('City bounding box is %s.' % str(self.boundingbox))

    def find_bounding_box(self, db, name):
        """Find the bounding box of a city from its name.

        Args:
            db: connection to the database
            name (string): The city name.
        Returns a BoundingBox object describing the bounding box around
        the given city.
        """

        l.info('Looking for bounding box around %s...' % name)

        cursor = db.cursor()
        cursor.execute("""select st_astext(st_transform(st_envelope(way), 4002))
                          from planet_osm_line
                          where boundary='administrative' and
                                admin_level='8' and
                                name='%s';""" % pgdb.escape_string(name))
        records = cursor.fetchall()
        if not records:
            raise UnsufficientDataError, "Wrong city name or missing administrative boundary in database!"
        
        return BoundingBox.parse_wkt(records[0][0])

    _regexp_contour = re.compile('^POLYGON\(\((\S*) (\S*),\S* (\S*),(\S*) \S*,\S* \S*,\S* \S*\),\(([^)]*)\)\)$')

    def get_city_contour(self, db, city):

        if city is None:
            return None

        cursor = db.cursor()
        cursor.execute("""select st_astext(st_transform(
                                    st_difference(st_envelope(way),
                                                  st_buildarea(way)), 4002))
                           from planet_osm_line
                           where boundary='administrative'
                                 and admin_level='8' and name='%s';""" % pgdb.escape_string(city))
        sl = cursor.fetchall()
        cell00 = sl[0][0].strip()
        if not cell00: return None

        # Parse the answer, in order to add a margin around the area
        prev_locale = locale.getlocale(locale.LC_ALL)
        locale.setlocale(locale.LC_ALL, "C")
        try:
            matches = self._regexp_contour.match(cell00)
            ymin, xmin, xmax, ymax, inside = matches.groups()
            xmin, ymin, ymax, xmax = map(float, (xmin, ymin, ymax, xmax))
            xmin -= 1. ; xmax += 1. # Add one degree around the area
            ymin -= 1. ; ymax += 1.
            return "POLYGON((%f %f, %f %f, %f %f, %f %f, %f %f),(%s))" \
                % (ymin, xmin, ymin, xmax, ymax, xmax, ymax, xmin, ymin, xmin,
                   inside)
        finally:
            locale.setlocale(locale.LC_ALL, prev_locale)

    def get_streets(self, db, city):

        """Get the list of streets in the administrative area if city is
        defined or in the bounding box otherwise, and for each
        street, the list of squares that it intersects.

        Returns a list of the form [(street_name, [[0, 1], [1, 1]]),
                                    (street2_name, [[1, 2]])]
        """
        cursor = db.cursor()

        # We start by building a map_areas table that contains the
        # list of the squares used to divide the global city map. Each
        # entry of this table represent one of these square, with x, y
        # being the square identifiers, and geom being its
        # geographical geometry. This temporary table allows to
        # conveniently perform a joint with the planet_osm_line table,
        # so that getting the list of squares for a given set of
        # streets can be performed in a single query
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
                                left join cities_area on city='%s'
                                where trim(name) != '' and highway is not null
                                and case when cities_area.area is null
                                then
                                  true
                                else
                                  st_intersects(way, cities_area.area)
                                end)
                          as foo
                          group by name
                          order by name;""" % pgdb.escape_string(city))

        sl = cursor.fetchall()

        # We transform the string representing the squares list into a
        # Python list
        sl = [( unicode(street[0].decode("utf-8")),
                [ map(int, x.split(',')) for x in street[1].split(';')[:-1] ] )
              for street in sl]

        # Street prefixes are postfixed, a human readable label is
        # built to represent the list of squares, and the list is
        # alphabetically-sorted.
        prev_locale = locale.getlocale(locale.LC_COLLATE)
        locale.setlocale(locale.LC_COLLATE, "fr_FR.UTF-8")
        try:
            sl = sorted(map(_humanize_street_label, sl),
                        lambda x, y: locale.strcoll(x[0].lower(), y[0].lower()))
        finally:
            locale.setlocale(locale.LC_COLLATE, prev_locale)

        return sl


    def _render_one_prefix(self, title, output_prefix, file_type,
                           paperwidth, paperheight):
        file_type   = file_type.lower()
        frame_width = int(max(paperheight / 20., 30))

        output_filename = "%s_index.%s" % (output_prefix, file_type)
        l.debug("rendering " + output_filename + "...")

        generator = IndexPageGenerator(self.streets)

        if file_type == 'xml':
            l.debug('not rendering index as xml (not supported)')
            return

        elif file_type == 'csv':
            try:
                writer = csv.writer(open(output_filename, 'w'))
            except Exception,ex:
                l.warning('error while opening destination file %s: %s'
                          % (output_filename, ex))
            else:
                writer.writerow(['#', 'MapOSMatic', 'ISO-8859-1'])
                for street in self.streets:
                    s = [e.encode('latin1', 'replace') for e in street]
                    writer.writerow(s)
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
            l.warning('No street to write to index')
            return

        for f in output_format:
            self._render_one_prefix(title, output_prefix, f,
                                    paperwidth, paperheight)

    def render_into_files(self, title,
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
        l.debug('rendering tmp dir: %s' % tmpdir)
        try:
            return self._render_into_files(tmpdir, osm_map_file,
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

    def _render_into_files(self, tmpdir,
                           osm_map_file, title, out_prefix, out_formats,
                           zoom_factor):
        # Does the real job of rendering the map
        GRID_COLOR = '#8BB381'
        l.debug('rendering from %s to %s.%s...' % (osm_map_file,
                                                   out_prefix,
                                                   out_formats))
        bbox = self.boundingbox.create_expanded(self.griddesc.height_square_angle*.7,
                                                self.griddesc.width_square_angle*.7)
        l.debug('bbox is: %s' % bbox)
        city = map_canvas.MapCanvas(osm_map_file, bbox, zoom_factor)
        l.debug('adding labels...')

        # Add the greyed-out area
        if self.contour is not None:
            path_contour = os.path.join(tmpdir, 'contour.shp')
            map_canvas.create_shapefile_polygon_from_wkt(path_contour,
                                                         self.contour)
            city.add_shapefile(path_contour, str_color = 'grey', alpha = .1)

        # Determine font size, depending on the zoom factor
        half_km_in_pixels = city.one_meter_in_pixels * 500.
        l.debug('500m = %f pixels' % half_km_in_pixels)
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
        l.debug('rendering map...')
        _map = city.render_map()
        for fmt in out_formats:
            l.debug('saving %s.%s...' % (out_prefix, fmt))
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

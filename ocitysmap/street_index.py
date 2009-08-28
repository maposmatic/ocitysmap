# -*- coding: utf-8; mode: Python -*-

import logging, traceback
import sys, os, tempfile, pgdb, re, math, cairo, locale

import map_canvas, grid, utils

from draw_utils import enclose_in_frame

l = logging.getLogger('ocitysmap')

locale.setlocale(locale.LC_ALL, "fr_FR.UTF-8")

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
        self.griddesc = grid.GridDescriptor(self.boundingbox, db)

        self.streets = self.get_streets(db, self.name)

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

    def get_streets(self, db, city):

        """Get the list of streets in the bounding box, and for each
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

        # Create a view that associates the name of a city with the
        # area covering it. As of today, only parts of the french
        # cities have these administrative boundaries available in
        # OSM. When available, this boundary is used to filter out the
        # streets that are not inside the selected city but still in
        # the bounding box rendered on the map. So these streets will
        # be shown but not listed in the street index.
        cursor.execute("""create or replace view cities_area
                          as select name as city, st_buildarea(way) as area
                          from planet_osm_line
                          where boundary='administrative' and admin_level='8';""")
        db.commit()

        # The inner select query creates the list of (street, square)
        # for all the squares in the temporary map_areas table. The
        # left_join + the test on cities_area is used to filter out
        # the streets outside the city administrative boundaries. The
        # outer select builds an easy to parse list of the squares for
        # each street. A typical result entry is:
        #  [ "Rue du Moulin", "0,1;1,2;1,3" ]
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
                          order by name;""" % city)

        sl = cursor.fetchall()

        # We transform the string representing the squares list into a
        # Python list
        sl = [( unicode(street[0].decode("utf-8")),
                [ map(int, x.split(',')) for x in street[1].split(';')[:-1] ] )
              for street in sl]

        # Street prefixes are postfixed, a human readable label is
        # built to represent the list of squares, and the list is
        # alphabetically-sorted.
        sl = sorted(map(_humanize_street_label, sl),
                          lambda x, y: locale.strcoll(x[0].lower(), y[0].lower()))
        return sl


    def _render_one_prefix(self, title, output_prefix, format, paperwidth, paperheight):
        format = format.lower()
        outfile = "%s_index.%s" % (output_prefix, format)
        l.debug("rendering " + outfile + "...")

        generator = IndexPageGenerator(self.streets)
        if format == 'png' or format == 'png24':
            surface = cairo.ImageSurface(cairo.FORMAT_RGB24,
                                         paperwidth + 400, paperheight + 400)
            enclose_in_frame(lambda ctx: generator.render(ctx, paperwidth, paperheight),
                      paperwidth, paperheight,
                      title, surface,
                      paperwidth + 400, paperheight + 400, 200)
            surface.write_to_png(outfile)
            surface.finish()
        elif format == 'svg':
            surface = cairo.SVGSurface(outfile, paperwidth + 400, paperheight + 400)
            enclose_in_frame(lambda ctx: generator.render(ctx, paperwidth, paperheight),
                      paperwidth, paperheight,
                      title, surface,
                      paperwidth + 400, paperheight + 400, 200)
            surface.finish()
        elif format == 'pdf':
            surface = cairo.PDFSurface(outfile, paperwidth + 400, paperheight + 400)
            enclose_in_frame(lambda ctx: generator.render(ctx, paperwidth, paperheight),
                      paperwidth, paperheight,
                      title, surface,
                      paperwidth + 400, paperheight + 400, 200)
            surface.finish()
        elif format == 'ps':
            surface = cairo.PSSurface(outfile, paperwidth + 400, paperheight + 400)
            enclose_in_frame(lambda ctx: generator.render(ctx, paperwidth, paperheight),
                      paperwidth, paperheight,
                      title, surface,
                      paperwidth + 400, paperheight + 400, 200)
            surface.finish()
        else:
            raise ValueError

    def render_index(self, title, output_prefix, output_format, paperwidth, paperheight):
        for f in output_format:
            self._render_one_prefix(title, output_prefix, f, paperwidth, paperheight)

    def render_into_files(self, osm_map_file, title,
                          out_prefix, out_formats,
                          zoom_factor):
        """
        Render the current boundingbox into the destination files.
        @param osm_map_file (string) path to the osm.xml file
        @param title (string/None) title of the map, or None: no frame
        @param out_prefix (string) prefix to use for generated files
        @param out_formats (iterable of strings) format of image files
        to generate
        @param zoom_factor None, a tuple (pixels_x, pixel_y) or
        'zoom:X' with X an integer [1..18]
        returns the MApnik map object used to render the map
        """
        # Create a temporary dir for the shapefiles and call _render_into_files
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
        bbox = self.boundingbox.create_expanded(self.griddesc.height_square_angle/2.,
                                                self.griddesc.width_square_angle/2.)
        l.debug('bbox is: %s' % bbox)
        city = map_canvas.MapCanvas(osm_map_file, bbox, zoom_factor)
        l.debug('adding labels...')

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
                + self.griddesc.height_square_angle/4.
            city.add_label(x, y, label,
                           str_color = GRID_COLOR,
                           alpha = .7,
                           font_size = font_size,
                           font_family = "DejaVu Sans Bold")
        for idx, label in enumerate(self.griddesc.horizontal_labels):
            x = self.griddesc.vertical_lines[0] \
                - self.griddesc.width_square_angle/4.
            y = self.griddesc.horizontal_lines[idx] \
                - self.griddesc.height_square_angle/2.
            city.add_label(x, y, label,
                           str_color = GRID_COLOR,
                           alpha = .7,
                           font_size = font_size,
                           font_family = "DejaVu Sans Bold")

        # Add the scale
        s, lat, lg \
            = self.griddesc.generate_scale_shape_file(os.path.join(tmpdir,
                                                                   'scale.shp'),
                                                      bbox.get_bottom_right()[0])
        city.add_shapefile(s.get_filepath(), 'black', .9, 1)

        city.add_label(lg, lat, "500m", font_size = 16, str_color = 'black')

        # Rendering...
        l.debug('rendering map...')
        _map = city.render_map()
        for fmt in out_formats:
            l.debug('saving %s...' % fmt)
            try:
                city.save_map("%s.%s" % (out_prefix, fmt),
                              title,
                              file_type = fmt)
            except:
                print >>sys.stderr, \
                    "Error while rendering %s:" % (fmt)
                traceback.print_exc()
                # Not fatal !

        return _map

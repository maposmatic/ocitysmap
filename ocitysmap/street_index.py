# -*- coding: utf-8; mode: Python -*-

import logging
import sys, os, tempfile, pgdb, re, math, cairo

import map_canvas, grid, utils

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
        heading_fheight = cr.font_extents()[2]

        cr.select_font_face("DejaVu", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(fontsize)
        fascent, fdescent, fheight, fxadvance, fyadvance = cr.font_extents()

        em = cr.text_extents("m")[2]

        widths = map(lambda x: cr.text_extents(x[0])[2] + cr.text_extents(x[1])[2], self.streets)
        maxwidth = max(widths)
        colwidth = maxwidth + 3 * em

        return {
            'colwidth' : colwidth,
            'heading_fheight' : heading_fheight,
            'fheight' : fheight,
            'em' : em,
            }

    def _fits_in_page(self, cr, paperwidth, paperheight, fontsize):
        fp = self._get_font_parameters(cr, fontsize)

        prevletter = None
        heading_letter_count = 0
        for street in self.streets:
            if street[0][0] != prevletter:
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

    def render(self, surface):
        paperwidth = surface.get_width()
        paperheight = surface.get_height()
        cr = cairo.Context(surface)
        cr.set_source_rgb(1, 1, 1)
        cr.paint()
        cr.set_source_rgb(0.0, 0.0, 0.0)

        fontsize = self._compute_font_size(cr, paperwidth, paperheight)

        fp = self._get_font_parameters(cr, fontsize)
        heading_fheight = fp['heading_fheight']
        fheight = fp['fheight']
        colwidth = fp['colwidth']
        em = fp['em']

        y = 0
        x = em
        prevletter = None
        for street in self.streets:
            # Letter label
            if street[0][0] != prevletter:
                # Make sure we have no orphelin heading letter label at the
                # end of a column
                if y + heading_fheight + fheight > paperheight:
                    y = 0
                    x += colwidth
                # Reserve height for the heading letter label
                y += heading_fheight
                # Draw the heading letter label
                cr.move_to(x, y)
                cr.select_font_face("DejaVu", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
                cr.set_font_size(fontsize * 1.2)
                cr.show_text(street[0][0])
                prevletter = street[0][0]

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
        cr.show_page()



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
        sl = [(unicode(street[0].decode("utf-8")), [map(int, x.split(','))
            for x in street[1].split(';')[:-1]]) for street in sl]
        sl = sorted(map(_humanize_street_label, sl),
                          lambda x, y: cmp(x[0].lower(), y[0].lower()))
        return sl

    def render_index(self, filename, paperwidth, paperheight):
        surface = cairo.ImageSurface(cairo.FORMAT_RGB24, paperwidth, paperheight)
        generator = IndexPageGenerator(self.streets)
        generator.render(surface)
        surface.write_to_png(filename)
        surface.finish()

    def render_into_files(self, osm_map_file, out_filenames, zoom_factor):
        """
        Render the current boundingbox into the destination files.
        @param osm_map_file (string) path to the osm.xml file
        @param out_filenames (iterable of strings) image files to generate
        @param zoom_factor None, a tuple (pixels_x, pixel_y) or
        'zoom:X' with X an integer [1..18]
        """
        # Create a temporary dir for the shapefiles and call _render_into_files
        tmpdir = tempfile.mkdtemp(prefix='ocitysmap')
        l.debug('rendering tmp dir: %s' % tmpdir)
        try:
            return self._render_into_files(tmpdir, osm_map_file,
                                           out_filenames, zoom_factor)
        finally:
            for root, dirs, files in os.walk(tmpdir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(tmpdir)

    def _render_into_files(self, tmpdir,
                           osm_map_file, out_filenames, zoom_factor):
        # Does the real job of rendering the map
        GRID_COLOR = '#8BB381'
        l.debug('rendering from %s to %s...' % (osm_map_file, out_filenames))
        bbox = self.boundingbox.create_expanded(self.griddesc.height_square_angle/2.,
                                                self.griddesc.width_square_angle/2.)
        l.debug('bbox is: %s' % bbox)
        city = map_canvas.MapCanvas(osm_map_file, bbox, zoom_factor)
        l.debug('adding labels...')

        # Determine font size, depending on the zoom factor
        half_km_in_pixels = city.one_meter_in_pixels * 500.
        if half_km_in_pixels < 10:
            font_size  = 8
            line_width = 1
        elif half_km_in_pixels < 25:
            font_size = 12
            line_width = 1
        elif half_km_in_pixels < 50:
            font_size = 25
            line_width = 2
        elif half_km_in_pixels < 100:
            font_size = 50
            line_width = 3
        elif half_km_in_pixels < 150:
            font_size = 75
            line_width = 4
        elif half_km_in_pixels < 200:
            font_size = 100
            line_width = 5
        elif half_km_in_pixels < 400:
            font_size = 200
            line_width = 6
        else:
            font_size = 250
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

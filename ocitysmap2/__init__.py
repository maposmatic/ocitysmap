# -*- coding: utf-8 -*-

# ocitysmap, city map and street index generator from OpenStreetMap data
# Copyright (C) 2010  David Decotigny
# Copyright (C) 2010  Frédéric Lehobey
# Copyright (C) 2010  Pierre Mauduit
# Copyright (C) 2010  David Mentré
# Copyright (C) 2010  Maxime Petazzoni
# Copyright (C) 2010  Thomas Petazzoni
# Copyright (C) 2010  Gaël Utard

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

"""OCitySMap 2.
"""

__author__ = 'The MapOSMatic developers'
__version__ = '0.2'

import cairo
import ConfigParser
import gzip
import logging
import os
import psycopg2
import re
import tempfile

import coords
import i18n
import index
import renderers

l = logging.getLogger('ocitysmap')

class RenderingConfiguration:
    """
    The RenderingConfiguration class encapsulate all the information concerning
    a rendering request. This data is used by the layout renderer, in
    conjonction with its rendering mode (defined by its implementation), to
    produce the map.
    """

    def __init__(self):
        self.title           = None # str
        self.osmid           = None # None / int (shading + city name)
        self.bounding_box    = None # bbox (from osmid if None)
        self.language        = None # str (locale)

        self.stylesheet      = None # Obj Stylesheet

        self.paper_width_mm  = None
        self.paper_height_mm = None

class Stylesheet:
    """
    A Stylesheet object defines how the map features will be rendered. It
    contains information pointing to the Mapnik stylesheet and other styling
    parameters.
    """

    def __init__(self):
        self.name        = None # str
        self.path        = None # str
        self.description = '' # str
        self.zoom_level = 16

        self.grid_line_color = 'black'
        self.grid_line_alpha = 0.5
        self.grid_line_width = 3

        self.shade_color = 'black'
        self.shade_alpha = 0.1

    @staticmethod
    def create_from_config_section(parser, section_name):
        """Creates a Stylesheet object from the OCitySMap configuration.

        Args:
            parser (ConfigParser.ConfigParser): the configuration parser
                object.
            section_name (string): the stylesheet section name in the
                configuration.
        """
        s = Stylesheet()

        def assign_if_present(key, cast_fn=str):
            if parser.has_option(section_name, key):
                setattr(s, key, cast_fn(parser.get(section_name, key)))

        s.name = parser.get(section_name, 'name')
        s.path = parser.get(section_name, 'path')
        assign_if_present('description')
        assign_if_present('zoom_level', int)

        assign_if_present('grid_line_color')
        assign_if_present('grid_line_alpha', float)
        assign_if_present('grid_line_width', int)

        assign_if_present('shade_color')
        assign_if_present('shade_alpha', float)
        return s

    @staticmethod
    def create_all_from_config(parser):
        styles = parser.get('rendering', 'available_stylesheets')
        if not styles:
            raise ValueError, \
                    'OCitySMap configuration does not contain any stylesheet!'

        return [Stylesheet.create_from_config_section(parser, name)
                for name in styles.split(',')]

class OCitySMap:

    DEFAULT_REQUEST_TIMEOUT_MIN = 15

    DEFAULT_ZOOM_LEVEL = 16
    DEFAULT_RESOLUTION_KM_IN_MM = 150

    STYLESHEET_REGISTRY = []

    def __init__(self, config_files=['/etc/ocitysmap.conf', '~/.ocitysmap.conf'],
                 grid_table_prefix=None):
        """..."""

        config_files = map(os.path.expanduser, config_files)
        l.info('Reading OCitySMap configuration from %s...' %
                 ', '.join(config_files))

        self._parser = ConfigParser.RawConfigParser()
        if not self._parser.read(config_files):
            raise IOError, 'None of the configuration files could be read!'

        self._locale_path = os.path.join(os.path.dirname(__file__), '..', 'locale')
        self._grid_table_prefix = '%sgrid_squares' % (grid_table_prefix or '')

        # Database connection
        datasource = dict(self._parser.items('datasource'))
        l.info('Connecting to database %s on %s as %s...' %
                 (datasource['dbname'], datasource['host'], datasource['user']))
        self._db = psycopg2.connect(user=datasource['user'],
                                    password=datasource['password'],
                                    host=datasource['host'],
                                    database=datasource['dbname'])

        # Force everything to be unicode-encoded, in case we run along Django
        # (which loads the unicode extensions for psycopg2)
        self._db.set_client_encoding('utf8')

        try:
            timeout = self._parser.get('datasource', 'request_timeout')
        except ConfigParser.NoOptionError:
            timeout = OCitySMap.DEFAULT_REQUEST_TIMEOUT_MIN
        self._set_request_timeout(timeout)

        # Read stylesheet configuration
        self.STYLESHEET_REGISTRY = Stylesheet.create_all_from_config(self._parser)

    def _set_request_timeout(self, timeout_minutes=15):
        """Sets the PostgreSQL request timeout to avoid long-running queries on
        the database."""
        cursor = self._db.cursor()
        cursor.execute('set session statement_timeout=%d;' %
                       (timeout_minutes * 60 * 1000))
        cursor.execute('show statement_timeout;')
        l.debug('Configured statement timeout: %s.' %
                  cursor.fetchall()[0][0])

    def _get_bounding_box(self, osmid):
        l.debug('Searching bounding box around OSM ID %d...' % osmid)
        cursor = self._db.cursor()
        cursor.execute("""select st_astext(st_transform(st_envelope(way), 4002))
                              from planet_osm_polygon where osm_id=%d;""" %
                       osmid)
        records = cursor.fetchall()

        if not records:
            raise ValueError, 'OSM ID %d not found in the database!' % osmid

        bbox = coords.BoundingBox.parse_wkt(records[0][0])
        l.debug('Found bounding box %s.' % bbox)
        return bbox

    def _cleanup_tempdir(self, tmpdir):
        l.debug('Cleaning up %s...' % tmpdir)
        for root, dirs, files in os.walk(tmpdir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(tmpdir)


    _regexp_polygon = re.compile('^POLYGON\(\(([^)]*)\)\)$')

    def _get_shade_wkt(self, bounding_box, osmid):
        l.info('Looking for contour around OSM ID %d...' % osmid)
        cursor = self._db.cursor()
        cursor.execute("""select st_astext(st_transform(st_buildarea(way), 4002))
                                   as polygon
                              from planet_osm_polygon
                              where osm_id=%d;""" % osmid)
        data = cursor.fetchall()

        try:
            polygon = data[0][0].strip()
        except (KeyError, IndexError, AttributeError):
            l.error('Invalid database structure!')
            return None

        if not polygon:
            return None

        matches = self._regexp_polygon.match(polygon)
        if not matches:
            l.error('Administrative boundary looks invalid!')
            return None
        inside = matches.groups()[0]

        bounding_box = bounding_box.create_expanded(0.05, 0.05)
        xmax, ymin = bounding_box.get_top_left()
        xmin, ymax = bounding_box.get_bottom_right()

        poly = "MULTIPOLYGON(((%f %f, %f %f, %f %f, %f %f, %f %f)),((%s)))" % \
                (ymin, xmin, ymin, xmax, ymax, xmax, ymax, xmin, ymin, xmin,
                 inside)
        return poly

    def get_all_style_configurations(self):
        """Returns the list of all available stylesheet configurations (list of
        Stylesheet objects)."""
        return self.STYLESHEET_REGISTRY

    def get_stylesheet_by_name(self, name):
        """Returns a stylesheet by its key name."""
        for style in self.STYLESHEET_REGISTRY:
            if style.name == name:
                return style
        raise LookupError, 'The requested stylesheet %s was not found!' % name

    def get_all_renderers(self):
        """Returns the list of all available layout renderers (list of Renderer
        objects)."""
        pass

    def render(self, config, renderer_name, output_formats, file_prefix):
        """Renders a job with the given rendering configuration, using the
        provided renderer, to the given output formats.

        Args:
            config (RenderingConfiguration): the rendering configuration
                object.
            renderer_name (string): the layout renderer to use for this rendering.
            output_formats (list): a list of output formats to render to, from
                the list of supported output formats (pdf, svgz, etc.).
            file_prefix (string): filename prefix for all output files.
        """

        assert config.osmid or config.bbox, \
                'At least an OSM ID or a bounding box must be provided!'

        output_formats = map(lambda x: x.lower(), output_formats)
        self._i18n = i18n.install_translation(config.language,
                                              self._locale_path)
        l.info('Rendering language: %s.' % self._i18n.language_code())

        # Make sure we have a bounding box
        config.bounding_box = (config.bounding_box or
                               self._get_bounding_box(config.osmid))

        # Create a temporary directory for all our shape files
        tmpdir = tempfile.mkdtemp(prefix='ocitysmap')
        l.debug('Rendering in temporary directory %s' % tmpdir)

        # TODO: For now, hardcode plain renderer
        renderer_cls = renderers.get_renderer_class_by_name(renderer_name)
        renderer = renderer_cls(config, tmpdir)
        renderer.create_map_canvas()

        if config.osmid:
            shade_wkt = self._get_shade_wkt(
                    renderer.canvas.get_actual_bounding_box(),
                    config.osmid)
            renderer.render_shade(shade_wkt)

        renderer.canvas.render()
        street_index = index.StreetIndex(config.osmid,
                                         renderer.canvas.get_actual_bounding_box(),
                                         config.language, renderer.grid)

        try:
            for output_format in output_formats:
                output_filename = '%s.%s' % (file_prefix, output_format)
                self._render_one(renderer, street_index, output_filename,
                                 output_format)

            # TODO: street_index.as_csv()
        finally:
            self._cleanup_tempdir(tmpdir)

    def _render_one(self, renderer, street_index, filename, output_format):
        l.info('Rendering %s...' % filename)

        factory = None

        if output_format == 'png':
            raise NotImplementedError

        elif output_format == 'svg':
            factory = lambda w,h: cairo.SVGSurface(filename, w, h)
        elif output_format == 'svgz':
            factory = lambda w,h: cairo.SVGSurface(
                    gzip.GzipFile(filename, 'wb'), w, h)
        elif output_format == 'pdf':
            factory = lambda w,h: cairo.PDFSurface(filename, w, h)

        elif output_format == 'ps':
            factory = lambda w,h: cairo.PDFSurface(filename, w, h)

        else:
            raise ValueError, \
                'Unsupported output format: %s!' % output_format.upper()

        surface = factory(renderer.paper_width_pt, renderer.paper_height_pt)
        renderer.render(surface, street_index)
        surface.finish()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    o = OCitySMap(['/home/sam/src/python/maposmatic/ocitysmap/ocitysmap.conf.mine'])

    c = RenderingConfiguration()
    c.title = 'Chevreuse'
    c.osmid = -943886 # -7444 (Paris)
    c.language = 'fr_FR'
    c.paper_width_mm = 594
    c.paper_height_mm = 420
    c.stylesheet = o.get_stylesheet_by_name('Default')

    o.render(c, 'plain', ['pdf'], '/tmp/mymap')

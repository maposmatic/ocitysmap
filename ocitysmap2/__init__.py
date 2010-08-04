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
import logging
import os
import psycopg2
import tempfile

import coords
import i18n
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
        self.dpi             = None


class Stylesheet:
    def __init__(self):
        self.name        = None # str
        self.description = None # str
        self.path        = None # str

        self.grid_line_color = 'black'
        self.grid_line_alpha = 0.8
        self.grid_line_width = 3


class OCitySMap:

    DEFAULT_REQUEST_TIMEOUT_MIN = 15

    DEFAULT_ZOOM_LEVEL = 16
    DEFAULT_RESOLUTION_DPI = 300.0

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

    def get_all_style_configurations(self):
        """Returns the list of all available stylesheet configurations (list of
        Stylesheet objects)."""
        pass

    def get_all_renderers(self):
        """Returns the list of all available layout renderers (list of Renderer
        objects)."""
        pass

    def render(self, config, renderer, output_formats, file_prefix):
        """Renders a job with the given rendering configuration, using the
        provided renderer, to the given output formats.

        Args:
            config (RenderingConfiguration): the rendering configuration
                object.
            renderer (Renderer): the layout renderer to use for this rendering.
            output_formats (list): a list of output formats to render to, from
                the list of supported output formats (pdf, svgz, etc.).
            file_prefix (string): filename prefix for all output files.
        """

        assert config.osmid or config.bbox, \
                'At least an OSM ID or a bounding box must be provided!'

        self._i18n = i18n.install_translation(config.language, self._locale_path)
        l.info('Rendering language: %s.' % self._i18n.language_code())

        # Make sure we have a bounding box
        config.bounding_box = (config.bounding_box or
                               self._get_bounding_box(config.osmid))

        # Create a temporary directory for all our shape files
        tmpdir = tempfile.mkdtemp(prefix='ocitysmap')
        l.debug('Rendering in temporary directory %s' % tmpdir)

        try:
            surface = cairo.PDFSurface('/tmp/plain.pdf', 2000, 2000)
            renderer.render(config, surface, None, tmpdir)
            surface.finish()
        finally:
            self._cleanup_tempdir(tmpdir)

if __name__ == '__main__':
    s = Stylesheet()
    s.name = 'osm'
    s.path = '/home/sam/src/python/maposmatic/mapnik-osm/osm.xml'

    c = RenderingConfiguration()
    c.title = 'Chevreuse'
    c.osmid = -943886
    c.language = 'fr_FR'
    c.stylesheet = s
    c.paper_width_mm = 210
    c.paper_height_mm = 297
    c.dpi = 300

    logging.basicConfig(level=logging.DEBUG)

    o = OCitySMap(['/home/sam/src/python/maposmatic/ocitysmap/ocitysmap.conf.mine'])
    o.render(c, renderers.PlainRenderer(), None, None)

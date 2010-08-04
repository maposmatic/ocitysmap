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

import logging
import mapnik
import os

import grid
import map_canvas

l = logging.getLogger('ocitysmap')

class Renderer:
    """
    The job of an OCitySMap layout renderer is to lay out the resulting map and
    render it from a given rendering configuration.
    """

    # Portrait paper sizes in milimeters
    PAPER_SIZES = [('A5', 148, 210),
                   ('A4', 210, 297),
                   ('A3', 297, 420),
                   ('A2', 420, 594),
                   ('A1', 594, 841),
                   ('A0', 841, 1189),

                   ('US letter', 216, 279),

                   ('100x75cm', 750, 1000),
                   ('80x60cm', 600, 800),
                   ('60x45cm', 450, 600),
                   ('40x30cm', 300, 400),

                   ('60x60cm', 600, 600),
                   ('50x50cm', 500, 500),
                   ('40x40cm', 400, 400),
                  ]

    def _get_dpi_from_dpmm(self, dpmm):
        return dpmm * 2.54 * 10

    def _get_dpmm_from_dpi(self, dpi):
        return dpi / 2.54 / 10

    def render(self, rendering_configuration, surface,
               street_index, tmpdir):
        raise NotImplementedError

    def get_compatible_paper_sizes(self, bounding_box, zoom_level,
                                   resolution_dpmm):
        raise NotImplementedError

class PlainRenderer(Renderer):
    def __init__(self):
        self.name = 'plain'
        self.description = 'A basic, full-page layout for the map.'

    def render(self, rendering_configuration, surface,
               street_index, tmpdir):
        """..."""

        resolution_dpmm = self._get_dpmm_from_dpi(rendering_configuration.dpi)

        l.info('PlainRenderer rendering on %dx%dmm paper at %d dpi (%dx%dpx)...' %
               (rendering_configuration.paper_width_mm,
                rendering_configuration.paper_height_mm,
                rendering_configuration.dpi,
                rendering_configuration.paper_width_mm * resolution_dpmm,
                rendering_configuration.paper_height_mm * resolution_dpmm))

        canvas = map_canvas.MapCanvas(rendering_configuration.stylesheet,
              rendering_configuration.bounding_box,
              int(rendering_configuration.paper_width_mm * resolution_dpmm),
              int(rendering_configuration.paper_height_mm * resolution_dpmm))

        grid_shape = (grid.Grid(rendering_configuration.bounding_box)
                .generate_shape_file(os.path.join(tmpdir, 'grid.shp')))
        canvas.add_shape_file(grid_shape,
                rendering_configuration.stylesheet.grid_line_color,
                rendering_configuration.stylesheet.grid_line_alpha,
                rendering_configuration.stylesheet.grid_line_width)

        rendered_map = canvas.render()
        ctx = cairo.Context(surface)
        mapnik.render(rendered_map, ctx)
        surface.flush()

        # TODO: scale
        # TODO: compass rose

        return surface

    def get_compatible_paper_sizes(self, bounding_box, zoom_level,
                                   resolution_dpmm):
        """Returns a list of paper sizes that can accomodate the provided
        bounding box at the given zoom level and print resolution."""

        px, py = bounding_box.get_pixel_size_for_zoom_factor(zoom_level)

        pw = min(px, py)
        ph = max(px, py)

        l.debug('Map needs %.2fx%.2f mm for %dx%dpx, filter paper sizes...' %
                (px / resolution_dpmm,
                 py / resolution_dpmm,
                 px, py))

        valid_sizes = filter(lambda (name,w,h):
                pw <= w * resolution_dpmm and
                ph <= h * resolution_dpmm,
            Renderer.PAPER_SIZES)
        return valid_sizes

class MapWithIndexRenderer(Renderer):
    pass

class MapWithRightIndexRenderer(MapWithIndexRenderer):
    pass

class MapWithBottomIndexRenderer(MapWithIndexRenderer):
    pass

class BookletRenderer(Renderer):
    pass

AVAILABLE_RENDERERS = [PlainRenderer()]


if __name__ == '__main__':
    import coords
    import cairo

    logging.basicConfig(level=logging.DEBUG)

    bbox = coords.BoundingBox(48.7158, 2.0179, 48.6960, 2.0694)
    zoom = 17
    dpmm = 132 / 2.54 / 10

    plain = PlainRenderer()
    print plain.get_compatible_paper_sizes(bbox, zoom, dpmm)

    class StylesheetMock:
        def __init__(self):
            self.path = '/home/sam/src/python/maposmatic/mapnik-osm/osm.xml'
            self.grid_line_color = 'black'
            self.grid_line_alpha = 0.9
            self.grid_line_width = 2

    class RenderingConfigurationMock:
        def __init__(self):
            self.stylesheet = StylesheetMock()
            self.bounding_box = bbox
            self.paper_width_mm = 297
            self.paper_height_mm = 210
            self.dpi = 132

    config = RenderingConfigurationMock()

    surface = cairo.PDFSurface('/tmp/plain.pdf',
                               config.paper_width_mm * dpmm,
                               config.paper_height_mm * dpmm)
    plain.render(config, surface, None, '/tmp')
    surface.finish()



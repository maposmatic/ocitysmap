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

import map_canvas

l = logging.getLogger('ocitysmap')

class Renderer:
    """
    The job of an OCitySMap layout renderer is to lay out the resulting map and
    render it from a given rendering configuration.
    """

    DEFAULT_ZOOM_LEVEL = 16
    DEFAULT_RESOLUTION_DPI = 300.0
    DEFAULT_RESOLUTION_DPCM = (DEFAULT_RESOLUTION_DPI / 2.54)

    # Portrait paper sizes
    PAPER_SIZES = [('A5', 14.8, 21.0),
                   ('A4', 21.0, 29.7),
                   ('A3', 29.7, 42.0),
                   ('A2', 42.0, 59.4),
                   ('A1', 59.4, 84.1),
                   ('A0', 84.1, 118.9),

                   ('US letter', 21.6, 27.9),

                   ('100x75cm', 75.0, 100.0),
                   ('80x60cm', 60.0, 80.0),
                   ('60x45cm', 45.0, 60.0),
                   ('40x30cm', 30.0, 40.0),

                   ('60x60cm', 60.0, 60.0),
                   ('50x50cm', 50.0, 50.0),
                   ('40x40cm', 40.0, 40.0),
                  ]

    def __init__(self):
        self.name        = None # str
        self.description = None # str

    def render(self, rendering_configuration, surface,
               street_index, zoom_level=DEFAULT_ZOOM_LEVEL,
               resolution_dpcm=DEFAULT_RESOLUTION_DPCM):
        raise NotImplementedError

    def get_compatible_paper_sizes(self, bounding_box,
                                   zoom_level=DEFAULT_ZOOM_LEVEL,
                                   resolution_dpcm=DEFAULT_RESOLUTION_DPCM):
        raise NotImplementedError

class PlainRenderer(Renderer):
    def __init__(self):
        self.name = 'plain'
        self.description = 'A basic, full-page layout for the map.'

    def render(self, rendering_configuration, surface,
               street_index, zoom_level=Renderer.DEFAULT_ZOOM_LEVEL,
               resolution_dpcm=Renderer.DEFAULT_RESOLUTION_DPCM):
        """..."""
        canvas = map_canvas.MapCanvas(rendering_configuration.stylesheet,
                                      rendering_configuration.bounding_box,
                                      rendering_configuration.width_px,
                                      rendering_configuration.height_px)

        # TODO: grid (variable granularity)
        # TODO: scale
        # TODO: compass rose

        rendered_map = canvas.render()
        ctx = cairo.Context(surface)
        mapnik.render(rendered_map, ctx)
        surface.flush()
        return surface

    def get_compatible_paper_sizes(self, bounding_box,
                                   zoom_level=Renderer.DEFAULT_ZOOM_LEVEL,
                                   resolution_dpcm=Renderer.DEFAULT_RESOLUTION_DPCM):
        """Returns a list of paper sizes that can accomodate the provided
        bounding box at the given zoom level and print resolution."""

        px, py = bounding_box.get_pixel_size_for_zoom_factor(zoom_level)

        pw = min(px, py)
        ph = max(px, py)

        l.debug('Map needs %.2fx%.2f cm, filter paper sizes...' %
                (px / resolution_dpcm,
                 py / resolution_dpcm))

        valid_sizes = filter(lambda (name,w,h):
                pw <= w * resolution_dpcm and
                ph <= h * resolution_dpcm,
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


if __name__ == '__main__':
    import coords
    import cairo

    logging.basicConfig(level=logging.DEBUG)

    bbox = coords.BoundingBox(48.8989, 2.2332, 48.8198, 2.4392)
    plain = PlainRenderer()
    print plain.get_compatible_paper_sizes(bbox)

    class StylesheetMock:
        def __init__(self):
            self.path = '/home/sam/src/python/maposmatic/mapnik-osm/osm.xml'

    class RenderingConfigurationMock:
        def __init__(self):
            self.stylesheet = StylesheetMock()
            self.bounding_box = bbox
            self.width_px = 2400
            self.height_px = 1400


    surface = cairo.PDFSurface('/tmp/plain.pdf', 2000, 2000)
    plain.render(RenderingConfigurationMock(), surface)
    surface.finish()


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

    def render(self, rc, surface, street_index, zoom_level, tmpdir):
        raise NotImplementedError

    def get_compatible_paper_sizes(self, bounding_box, zoom_level,
                                   resolution_km_in_mm):
        raise NotImplementedError

class PlainRenderer(Renderer):
    def __init__(self):
        self.name = 'plain'
        self.description = 'A basic, full-page layout for the map.'

    def render(self, rc, surface, street_index, zoom_level, tmpdir):
        """..."""

        l.info('PlainRenderer rendering on %dx%dmm paper.' %
               (rc.paper_width_mm, rc.paper_height_mm))

        canvas = map_canvas.MapCanvas(rc.stylesheet, rc.bounding_box,
                                      (float(rc.paper_width_mm) /
                                       rc.paper_height_mm),
                                      zoom_level)

        grid_shape = (grid.Grid(canvas.get_actual_bounding_box())
                .generate_shape_file(os.path.join(tmpdir, 'grid.shp')))
        canvas.add_shape_file(grid_shape,
                rc.stylesheet.grid_line_color,
                rc.stylesheet.grid_line_alpha,
                rc.stylesheet.grid_line_width)

        rendered_map = canvas.render()
        ctx = cairo.Context(surface)

        def mm_to_pt(mm):
            return ((mm/10.0) / 2.54) * 72

        ctx.scale(mm_to_pt(rc.paper_width_mm) / rendered_map.width,
                  mm_to_pt(rc.paper_height_mm) / rendered_map.height)

        mapnik.render(rendered_map, ctx)
        surface.flush()

        # TODO: scale
        # TODO: compass rose

        return surface

    def get_compatible_paper_sizes(self, bounding_box, zoom_level,
                                   resolution_km_in_mm):
        """Returns a list of paper sizes that can accomodate the provided
        bounding box at the given zoom level and print resolution."""

        geo_width_m, geo_height_m = bounding_box.spheric_sizes()
        paper_width_mm = geo_width_m/1000.0 * resolution_km_in_mm
        paper_height_mm = geo_height_m/1000.0 * resolution_km_in_mm

        l.debug('Map represents %dx%dm, needs at least %.1fx%.1fcm '
                'on paper.' % (geo_width_m, geo_height_m,
                 paper_width_mm/10, paper_height_mm/10))

        valid_sizes = filter(lambda (name,w,h):
                paper_width_mm <= w and paper_height_mm <= h,
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
    zoom = 16

    plain = PlainRenderer()

    papers = plain.get_compatible_paper_sizes(bbox, zoom, resolution_km_in_mm=150)
    print 'Compatible paper sizes:'
    for p in papers:
        print '  * %s (%.1fx%.1fcm)' % (p[0], p[1]/10.0, p[2]/10.0)
    print 'Using first available:', papers[0]

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
            self.paper_width_mm = papers[0][2]
            self.paper_height_mm = papers[0][1]
            self.min_km_in_mm = 110

    config = RenderingConfigurationMock()

    def mm_to_pt(mm):
        return ((mm/10.0) / 2.54) * 72

    surface = cairo.PDFSurface('/tmp/plain.pdf',
                               mm_to_pt(config.paper_width_mm),
                               mm_to_pt(config.paper_height_mm))
    plain.render(config, surface, None, zoom, '/tmp')
    surface.finish()



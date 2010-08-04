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

import cairo
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


    def _create_map_canvas(self, rc, graphical_ratio, tmpdir):
        canvas = map_canvas.MapCanvas(rc.stylesheet, rc.bounding_box,
                                      graphical_ratio)

        _grid = grid.Grid(canvas.get_actual_bounding_box())
        grid_shape = _grid.generate_shape_file(os.path.join(tmpdir, 'grid.shp'))
        canvas.add_shape_file(grid_shape,
                rc.stylesheet.grid_line_color,
                rc.stylesheet.grid_line_alpha,
                rc.stylesheet.grid_line_width)

        return canvas, _grid

    def create_map_canvas(self, rc, tmpdir):
        """Returns the map canvas object and the grid object that has been
        overlayed on the created map.

        Args:
            rc (RenderingConfiguration): the rendering configuration.
            tmpdir (path): path to a directory for temporary shape files.
        """
        raise NotImplementedError

    def render(self, rc, canvas, surface, street_index):
        raise NotImplementedError

    def get_compatible_paper_sizes(self, bounding_box, zoom_level,
                                   resolution_km_in_mm):
        raise NotImplementedError

    @staticmethod
    def convert_mm_to_pt(mm):
        return ((mm/10.0) / 2.54) * 72

class PlainRenderer(Renderer):
    def __init__(self):
        self.name = 'plain'
        self.description = 'A basic, full-page layout for the map.'

    def create_map_canvas(self, rc, tmpdir):
        return self._create_map_canvas(rc, (float(rc.paper_width_mm) /
                                       rc.paper_height_mm), tmpdir)

    def render(self, rc, canvas, surface, street_index):
        """..."""

        l.info('PlainRenderer rendering on %dx%dmm paper.' %
               (rc.paper_width_mm, rc.paper_height_mm))

        rendered_map = canvas.get_rendered_map()

        ctx = cairo.Context(surface)
        ctx.scale(Renderer.convert_mm_to_pt(rc.paper_width_mm) /
                    rendered_map.width,
                  Renderer.convert_mm_to_pt(rc.paper_height_mm) /
                    rendered_map.height)

        # TODO: scale
        # TODO: compass rose

        mapnik.render(rendered_map, ctx)
        surface.flush()
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

    papers = plain.get_compatible_paper_sizes(bbox, zoom,
                                              resolution_km_in_mm=110)
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
            self.zoom_level = 16

    class RenderingConfigurationMock:
        def __init__(self):
            self.stylesheet = StylesheetMock()
            self.bounding_box = bbox
            self.paper_width_mm = papers[0][2]
            self.paper_height_mm = papers[0][1]
            self.min_km_in_mm = 110

    config = RenderingConfigurationMock()

    surface = cairo.PDFSurface('/tmp/plain.pdf',
                   Renderer.convert_mm_to_pt(config.paper_width_mm),
                   Renderer.convert_mm_to_pt(config.paper_height_mm))

    canvas, _ = plain.create_map_canvas(config, '/tmp')
    canvas.render()
    plain.render(config, canvas, surface, None)
    surface.finish()



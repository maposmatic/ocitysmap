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
import math
import os

import grid
import map_canvas
import shapes

l = logging.getLogger('ocitysmap')

class RenderingSession:

    PT_PER_INCH = 72.0

    def __init__(self, surface, street_index,
                 dpi=PT_PER_INCH):
        self.surface = surface
        self.street_index = street_index
        self.dpi = dpi

    def pt_to_dots(self, pt):
        return RenderingSession.pt_to_dots_with_dpi(pt, self.dpi)

    @staticmethod
    def pt_to_dots_with_dpi(pt, dpi):
        return float(pt * dpi) / RenderingSession.PT_PER_INCH


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

                   ('Best fit', None, None),
                  ]

    # The PRINT_SAFE_MARGIN_PT is a small margin we leave on all page borders
    # to ease printing as printers often eat up margins with misaligned paper,
    # etc.
    PRINT_SAFE_MARGIN_PT = 15

    GRID_LEGEND_MARGIN_RATIO = .02

    # The DEFAULT_KM_IN_MM represents the minimum acceptable size in milimeters
    # on the rendered map of a kilometer
    DEFAULT_KM_IN_MM = 80

    def __init__(self, rc, tmpdir):
        self.rc = rc
        self.tmpdir = tmpdir
        self.canvas = None
        self.grid = None

        self.paper_width_pt = \
                Renderer.convert_mm_to_pt(self.rc.paper_width_mm)
        self.paper_height_pt = \
                Renderer.convert_mm_to_pt(self.rc.paper_height_mm)

    @staticmethod
    def convert_mm_to_pt(mm):
        return ((mm/10.0) / 2.54) * 72

    def _create_map_canvas(self, graphical_ratio):
        self.canvas = map_canvas.MapCanvas(self.rc.stylesheet,
                                           self.rc.bounding_box,
                                           graphical_ratio)

        # Add the grid
        self.grid = grid.Grid(self.canvas.get_actual_bounding_box(),
                              self.rc.rtl)
        grid_shape = self.grid.generate_shape_file(
                os.path.join(self.tmpdir, 'grid.shp'))
        self.canvas.add_shape_file(grid_shape,
                                   self.rc.stylesheet.grid_line_color,
                                   self.rc.stylesheet.grid_line_alpha,
                                   self.rc.stylesheet.grid_line_width)

    def _draw_rectangle(self, ctx, x, y, width, height, line_width):
        ctx.save()
        ctx.set_line_width(line_width)
        ctx.move_to(x, y)
        ctx.rel_line_to(0, height)
        ctx.rel_line_to(width, 0)
        ctx.rel_line_to(0, - height)
        ctx.close_path()
        ctx.stroke()
        ctx.restore()

    def _draw_centered_text(self, ctx, text, x, y):
        ctx.save()
        xb, yb, tw, th, xa, ya = ctx.text_extents(text)
        ctx.move_to(x - tw/2.0 - xb, y - yb/2.0)
        ctx.show_text(text)
        ctx.stroke()
        ctx.restore()

    def _draw_labels(self, ctx, map_area_width_dots, map_area_height_dots,
                     grid_legend_margin_dots):
        ctx.save()

        step_horiz = map_area_width_dots / self.grid.horiz_count
        last_horiz_portion = math.modf(self.grid.horiz_count)[0]

        step_vert = map_area_height_dots / self.grid.vert_count
        last_vert_portion = math.modf(self.grid.vert_count)[0]

        ctx.set_font_size(min(0.75 * grid_legend_margin_dots,
                              0.5 * step_horiz))

        for i, label in enumerate(self.grid.horizontal_labels):
            x = grid_legend_margin_dots + i * step_horiz

            if i < len(self.grid.horizontal_labels) - 1:
                x += step_horiz/2.0
            elif last_horiz_portion >= 0.25:
                x += step_horiz * last_horiz_portion/2.0
            else:
                continue

            self._draw_centered_text(ctx, label,
                                     x, grid_legend_margin_dots/2.0)
            self._draw_centered_text(ctx, label,
                                     x, map_area_height_dots +
                                        3*grid_legend_margin_dots/2.0)

        for i, label in enumerate(self.grid.vertical_labels):
            y = grid_legend_margin_dots + i * step_vert

            if i < len(self.grid.vertical_labels) - 1:
                y += step_vert/2.0
            elif last_vert_portion >= 0.25:
                y += step_vert * last_vert_portion/2.0
            else:
                continue

            self._draw_centered_text(ctx, label,
                                     grid_legend_margin_dots/2.0, y)
            self._draw_centered_text(ctx, label,
                                     map_area_width_dots +
                                     3*grid_legend_margin_dots/2.0, y)

        ctx.restore()

    def render_shade(self, shade_wkt):
        # Add the grey shade
        shade_shape = shapes.PolyShapeFile(
                self.canvas.get_actual_bounding_box(),
                os.path.join(self.tmpdir, 'shade.shp'),
                'shade')
        shade_shape.add_shade_from_wkt(shade_wkt)
        self.canvas.add_shape_file(shade_shape, self.rc.stylesheet.shade_color,
                                   self.rc.stylesheet.shade_alpha)

    # The next three methods are to be overloaded by the actual renderer.

    def create_map_canvas(self):
        """Creates the Mapnik map canvas to the appropriate graphical ratio so
        it can be scaled and fitted into the zone on the page dedicated to the
        map."""
        raise NotImplementedError

    def create_rendering_session(self, surface, street_index,
                                 dpi=RenderingSession.PT_PER_INCH):
        """
        """
        return RenderingSession(surface, street_index, dpi)

    def render(self, rs):
        """Renders the map, the index and all other visual map features on the
        given Cairo surface.

        Args:
            surface (cairo.Surface): the Cairo surface to render into.
            street_index (index.StreetIndex): the street index, that would be
                rendered by a renderer that supports it.
        """
        raise NotImplementedError

    @staticmethod
    def get_compatible_paper_sizes(bounding_box, zoom_level,
                                   resolution_km_in_mm):
        """Returns a list of the compatible paper sizes for the given bounding
        box. The list is sorted, smaller papers first, and a "custom" paper
        matching the dimensions of the bounding box is added at the end.

        Args:
            bounding_box (coords.BoundingBox): the map geographic bounding box.
            zoom_level (int): the Mapnik zoom level to use, generally 16.
            resolution_km_in_mm (int): size of a geographic kilometer in
                milimeters on the rendered map.

        Returns a list of tuples (paper name, width in mm, height in mm). Paper
        sizes are represented in portrait mode.
        """

        raise NotImplementedError


class PlainRenderer(Renderer):
    """
    The PlainRenderer is the simplest renderer we have. It creates a full-page
    map, with the overlayed features like the grid, grid labels, scale and
    compass rose but no index.
    """

    name = 'plain'
    description = 'A basic, full-page layout for the map.'

    def __init__(self, rc, tmpdir):
        Renderer.__init__(self, rc, tmpdir)

        self.grid_legend_margin_pt = \
                min(Renderer.GRID_LEGEND_MARGIN_RATIO * self.paper_width_pt,
                    Renderer.GRID_LEGEND_MARGIN_RATIO * self.paper_height_pt)

        self.map_area_width_pt = (self.paper_width_pt -
                                  2 * (Renderer.PRINT_SAFE_MARGIN_PT +
                                       self.grid_legend_margin_pt))
        self.map_area_height_pt = (self.paper_height_pt -
                                   2 * (Renderer.PRINT_SAFE_MARGIN_PT +
                                        self.grid_legend_margin_pt))

    def create_rendering_session(self, surface, street_index,
                                 dpi=RenderingSession.PT_PER_INCH):
        rs = Renderer.create_rendering_session(self, surface, street_index, dpi)
        rs.safe_margin_dots = rs.pt_to_dots(Renderer.PRINT_SAFE_MARGIN_PT)
        rs.grid_legend_margin_dots = rs.pt_to_dots(self.grid_legend_margin_pt)
        rs.map_area_width_dots = rs.pt_to_dots(self.map_area_width_pt)
        rs.map_area_height_dots = rs.pt_to_dots(self.map_area_height_pt)
        return rs

    def create_map_canvas(self):
        self._create_map_canvas(float(self.map_area_width_pt) /
                                float(self.map_area_height_pt))

    def render(self, rs):
        """
        Args:
            rs (RenderingSession): ...
        """

        l.info('PlainRenderer rendering on %dx%dmm paper at %d dpi.' %
               (self.rc.paper_width_mm, self.rc.paper_height_mm, rs.dpi))


        rendered_map = self.canvas.get_rendered_map()
        ctx = cairo.Context(rs.surface)

        # Print margin
        ctx.translate(rs.safe_margin_dots, rs.safe_margin_dots)

        ctx.save()
        ctx.translate(rs.grid_legend_margin_dots, rs.grid_legend_margin_dots)

        ctx.scale(rs.map_area_width_dots / rendered_map.width,
                  rs.map_area_height_dots / rendered_map.height)

        # Render the map canvas to the Cairo surface
        mapnik.render(rendered_map, ctx)

        # Draw a rectangle around the map
        self._draw_rectangle(ctx, 0, 0, rendered_map.width, rendered_map.height,
                             self.rc.stylesheet.grid_line_width)
        ctx.restore()

        # Place the vertical and horizontal square labels
        self._draw_labels(ctx, rs.map_area_width_dots, rs.map_area_height_dots,
                          rs.grid_legend_margin_dots)

        # TODO: map scale
        # TODO: compass rose

        rs.surface.flush()

    @staticmethod
    def get_compatible_paper_sizes(bounding_box, zoom_level,
                                   resolution_km_in_mm=Renderer.DEFAULT_KM_IN_MM):
        """Returns a list of paper sizes that can accomodate the provided
        bounding box at the given zoom level and print resolution.

        The compatible paper sizes is a list of 5-uples (name, width in
        millimeters, height in millimeters, portrait capable, landscape
        capable).
        """

        geo_width_m, geo_height_m = bounding_box.spheric_sizes()
        paper_width_mm = geo_width_m/1000.0 * resolution_km_in_mm
        paper_height_mm = geo_height_m/1000.0 * resolution_km_in_mm

        l.debug('Map represents %dx%dm, needs at least %.1fx%.1fcm '
                'on paper.' % (geo_width_m, geo_height_m,
                 paper_width_mm/10, paper_height_mm/10))

        # Test both portrait and landscape orientations when checking for paper
        # sizes.
        valid_sizes = []
        for name, w, h in Renderer.PAPER_SIZES:
            portrait_ok = paper_width_mm <= w and paper_height_mm <= h
            landscape_ok = paper_width_mm <= h and paper_height_mm <= w

            if portrait_ok or landscape_ok:
                valid_sizes.append((name, w, h, portrait_ok, landscape_ok))

        # Add a 'Custom' paper format to the list that perfectly matches the
        # bounding box.
        valid_sizes.append(('Best fit',
                            min(paper_width_mm, paper_height_mm),
                            max(paper_width_mm, paper_height_mm),
                            paper_width_mm < paper_height_mm,
                            paper_width_mm > paper_height_mm))

        return valid_sizes

# The renderers registry
_RENDERERS = [PlainRenderer]

def get_renderer_class_by_name(name):
    """Retrieves a renderer class, by name."""
    for renderer in _RENDERERS:
        if renderer.name == name:
            return renderer
    raise LookupError, 'The requested renderer %s was not found!' % name

def get_renderers():
    """Returns the list of available renderers' names."""
    return _RENDERERS

if __name__ == '__main__':
    import coords
    import cairo

    logging.basicConfig(level=logging.DEBUG)

    bbox = coords.BoundingBox(48.8162, 2.3417, 48.8063, 2.3699)
    zoom = 16

    renderer_cls = get_renderer_class_by_name('plain')

    papers = renderer_cls.get_compatible_paper_sizes(bbox, zoom)

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
            self.paper_width_mm = papers[0][1]
            self.paper_height_mm = papers[0][2]
            self.rtl = False

    config = RenderingConfigurationMock()

    plain = renderer_cls(config, '/tmp')
    surface = cairo.PDFSurface('/tmp/plain.pdf',
                   Renderer.convert_mm_to_pt(config.paper_width_mm),
                   Renderer.convert_mm_to_pt(config.paper_height_mm))

    plain.create_map_canvas()
    plain.canvas.render()
    plain.render(surface, None)
    surface.finish()

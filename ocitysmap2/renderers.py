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
import datetime
import logging
import mapnik
import math
import os
import re
import pango
import pangocairo

from map_canvas import MapCanvas
from grid import Grid
import shapes
import index

LOG = logging.getLogger('ocitysmap')

class UTILS:
    PT_PER_INCH = 72.0

    @staticmethod
    def convert_pt_to_dots(pt, dpi = PT_PER_INCH):
        return float(pt * dpi) / UTILS.PT_PER_INCH

    @staticmethod
    def convert_mm_to_pt(mm):
        return ((mm/10.0) / 2.54) * 72


class Renderer:
    """
    The job of an OCitySMap layout renderer is to lay out the resulting map and
    render it from a given rendering configuration.
    """
    name = 'abstract'
    description = 'The abstract interface of a renderer'

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
    DEFAULT_KM_IN_MM = 100

    def __init__(self, rc, tmpdir, street_index):
        """
        Create the renderer.

        Args:
           rc (RenderingConfiguration): rendering parameters.
           tmpdir (os.path): Path to a temp dir that can hold temp files.
           street_index (StreetIndex): None or the street index object.
        """
        # Note: street_index may be None
        self.rc           = rc
        self.tmpdir       = tmpdir
        self.grid         = None # The implementation is in charge of it
        self.street_index = street_index

        self.paper_width_pt = \
                UTILS.convert_mm_to_pt(self.rc.paper_width_mm)
        self.paper_height_pt = \
                UTILS.convert_mm_to_pt(self.rc.paper_height_mm)

    @staticmethod
    def _draw_centered_text(ctx, text, x, y):
        """
        Draw the given text centered at x,y.

        Args:
           ctx (cairo.Context): The cairo context to use to draw.
           text (str): the text to draw.
           x,y (numbers): Location of the center (cairo units).
        """
        ctx.save()
        xb, yb, tw, th, xa, ya = ctx.text_extents(text)
        ctx.move_to(x - tw/2.0 - xb, y - yb/2.0)
        ctx.show_text(text)
        ctx.stroke()
        ctx.restore()

    @staticmethod
    def _adjust_font_size(layout, fd, constraint_x, constraint_y):
        """
        Grow the given font description (20% by 20%) until it fits in
        designated area and then draw it.

        Args:
           layout (pango.Layout): The text block parameters.
           fd (pango.FontDescriptor): The font object.
           constraint_x/constraint_y (numbers): The area we want to
               write into (cairo units).
        """
        while (layout.get_size()[0] / pango.SCALE < constraint_x and
               layout.get_size()[1] / pango.SCALE < constraint_y):
            fd.set_size(int(fd.get_size()*1.2))
            layout.set_font_description(fd)
        fd.set_size(int(fd.get_size()/1.2))
        layout.set_font_description(fd)

    @staticmethod
    def _get_osm_logo(ctx, height):
        """
        Read the OSM logo file and rescale it to fit within height.

        Args:
           ctx (cairo.Context): The cairo context to use to draw.
           height (number): final height of the logo (cairo units).

        Return a tuple (cairo group object for the logo, logo width in
                        cairo units).
        """
        # TODO: read vector logo
        logo_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', 'images', 'osm-logo.png'))
        try:
            with open(logo_path, 'rb') as f:
                png = cairo.ImageSurface.create_from_png(f)
                LOG.debug('Using copyright logo: %s.' % logo_path)
        except IOError:
            LOG.warning('Cannot open logo from %s.' % logo_path)
            return None

        ctx.push_group()
        ctx.save()
        ctx.move_to(0, 0)
        factor = height / png.get_height()
        ctx.scale(factor, factor)
        ctx.set_source_surface(png)
        ctx.paint()
        ctx.restore()
        return ctx.pop_group(), png.get_width()*factor

    @staticmethod
    def _draw_labels(ctx, map_grid,
                     map_area_width_dots, map_area_height_dots,
                     grid_legend_margin_dots):
        """
        Draw the Grid labels at current position.

        Args:
           ctx (cairo.Context): The cairo context to use to draw.
           map_grid (Grid): the grid objects whose labels we want to draw.
           map_area_width_dots/map_area_height_dots (numbers): size of the
              map (cairo units).
           grid_legend_margin_dots (number): margin between border of
              map and grid labels (cairo units).
        """
        ctx.save()

        step_horiz = map_area_width_dots / map_grid.horiz_count
        last_horiz_portion = math.modf(map_grid.horiz_count)[0]

        step_vert = map_area_height_dots / map_grid.vert_count
        last_vert_portion = math.modf(map_grid.vert_count)[0]

        ctx.set_font_size(min(0.75 * grid_legend_margin_dots,
                              0.5 * step_horiz))

        for i, label in enumerate(map_grid.horizontal_labels):
            x = i * step_horiz

            if i < len(map_grid.horizontal_labels) - 1:
                x += step_horiz/2.0
            elif last_horiz_portion >= 0.3:
                x += step_horiz * last_horiz_portion/2.0
            else:
                continue

            Renderer._draw_centered_text(ctx, label,
                                         x, grid_legend_margin_dots/2.0)
            Renderer._draw_centered_text(ctx, label,
                                         x, map_area_height_dots -
                                         grid_legend_margin_dots/2.0)

        for i, label in enumerate(map_grid.vertical_labels):
            y = i * step_vert

            if i < len(map_grid.vertical_labels) - 1:
                y += step_vert/2.0
            elif last_vert_portion >= 0.3:
                y += step_vert * last_vert_portion/2.0
            else:
                continue

            Renderer._draw_centered_text(ctx, label,
                                         grid_legend_margin_dots/2.0, y)
            Renderer._draw_centered_text(ctx, label,
                                         map_area_width_dots -
                                         grid_legend_margin_dots/2.0, y)

        ctx.restore()

    def _create_map_canvas(self, graphical_ratio,
                           draw_contour_shade = True):
        """
        Create a new MapCanvas object.

        Args:
           graphical_ratio (float): ratio W/H of the area to render into.
           draw_contour_shade (bool): whether to draw a shade around
               the area of interest or not.

        Return the MapCanvas object.
        """

        # Prepare the map canvas
        canvas = MapCanvas(self.rc.stylesheet,
                           self.rc.bounding_box,
                           graphical_ratio)

        if draw_contour_shade:
            # Determine the shade WKT
            regexp_polygon = re.compile('^POLYGON\(\(([^)]*)\)\)$')
            matches = regexp_polygon.match(self.rc.polygon_wkt)
            if not matches:
                LOG.error('Administrative boundary looks invalid!')
                return None
            inside = matches.groups()[0]

            bounding_box \
                = canvas.get_actual_bounding_box().create_expanded(0.05, 0.05)
            shade_wkt = "MULTIPOLYGON(((%s)),((%s)))" % \
                (bounding_box.as_wkt(with_polygon_statement = False), inside)

            # Prepare the shade SHP
            shade_shape = shapes.PolyShapeFile(
                canvas.get_actual_bounding_box(),
                os.path.join(self.tmpdir, 'shade.shp'),
                'shade')
            shade_shape.add_shade_from_wkt(shade_wkt)

            # Add the shade SHP to the map
            canvas.add_shape_file(shade_shape,
                                  self.rc.stylesheet.shade_color,
                                  self.rc.stylesheet.shade_alpha)

        return canvas

    def _create_grid(self, canvas):
        """
        Create a new Grid object for the given MapCanvas.

        Args:
           canvas (MapCanvas): Map Canvas (see _create_map_canvas).

        Return a new Grid object.
        """
        # Prepare the grid SHP
        map_grid = Grid(canvas.get_actual_bounding_box(), self.rc.i18n.isrtl())
        grid_shape = map_grid.generate_shape_file(
            os.path.join(self.tmpdir, 'grid.shp'))

        # Add the grid SHP to the map
        canvas.add_shape_file(grid_shape,
                              self.rc.stylesheet.grid_line_color,
                              self.rc.stylesheet.grid_line_alpha,
                              self.rc.stylesheet.grid_line_width)

        return map_grid

    # The next two methods are to be overloaded by the actual renderer.
    def render(self, cairo_surface, dpi):
        """Renders the map, the index and all other visual map features on the
        given Cairo surface.

        Args:
            cairo_surface (Cairo.Surface): the destination Cairo device.
            dpi (int): dots per inch of the device.
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


class SinglePageRenderer(Renderer):
    """
    This Renderer creates a full-page map, with the overlayed features
    like the grid, grid labels, scale and compass rose and can draw an
    index.
    """

    name = 'generic_single_page'
    description = 'A generic full-page layout with or without index.'

    MAX_INDEX_OCCUPATION_RATIO = 1/3.

    def __init__(self, rc, tmpdir,
                 street_index = None, index_position = 'side'):
        """
        Create the renderer.

        Args:
           rc (RenderingConfiguration): rendering parameters.
           tmpdir (os.path): Path to a temp dir that can hold temp files.
           street_index (StreetIndex): None or the street index object.
           index_position (str): None or 'side' (index on side),
              'bottom' (index at bottom).
        """
        Renderer.__init__(self, rc, tmpdir, street_index)

        self._grid_legend_margin_pt = \
            min(Renderer.GRID_LEGEND_MARGIN_RATIO * self.paper_width_pt,
                Renderer.GRID_LEGEND_MARGIN_RATIO * self.paper_height_pt)
        self._title_margin_pt = 0.05 * self.paper_height_pt
        self._copyright_margin_pt = 0.02 * self.paper_height_pt

        self._usable_area_width_pt = (self.paper_width_pt -
                                      2 * Renderer.PRINT_SAFE_MARGIN_PT)
        self._usable_area_height_pt = (self.paper_height_pt -
                                       (2 * Renderer.PRINT_SAFE_MARGIN_PT +
                                        self._title_margin_pt +
                                        self._copyright_margin_pt))

        # Prepare the Index (may raise a IndexDoesNotFitError)
        if self.street_index and len(self.street_index) and index_position:
            self._index_renderer, self._index_area \
                = self._create_index_rendering(index_position == "side")
        else:
            self._index_renderer, self._index_area = None, None

        # Prepare the layout of the whole page
        if not self._index_area:
            # No index displayed
            self._map_coords = ( Renderer.PRINT_SAFE_MARGIN_PT,
                                 ( Renderer.PRINT_SAFE_MARGIN_PT
                                   + self._title_margin_pt ),
                                 self._usable_area_width_pt,
                                 self._usable_area_height_pt )
        elif index_position == 'side':
            # Index present, displayed on the side
            if self._index_area.x > Renderer.PRINT_SAFE_MARGIN_PT:
                # Index on the right -> map on the left
                self._map_coords = ( Renderer.PRINT_SAFE_MARGIN_PT,
                                     ( Renderer.PRINT_SAFE_MARGIN_PT
                                       + self._title_margin_pt ),
                                     ( self._usable_area_width_pt
                                       - self._index_area.w ),
                                     self._usable_area_height_pt )
            else:
                # Index on the left -> map on the right
                self._map_coords = ( self._index_area.x + self._index_area.w,
                                     ( Renderer.PRINT_SAFE_MARGIN_PT
                                       + self._title_margin_pt ),
                                     ( self._usable_area_width_pt
                                       - self._index_area.w ),
                                     self._usable_area_height_pt )
        elif index_position == 'bottom':
            # Index present, displayed at the bottom -> map on top
            self._map_coords = ( Renderer.PRINT_SAFE_MARGIN_PT,
                                 ( Renderer.PRINT_SAFE_MARGIN_PT
                                   + self._title_margin_pt ),
                                 self._usable_area_width_pt,
                                 ( self._usable_area_height_pt
                                   - self._index_area.h ) )
        else:
            raise AssertionError("Invalid index position %s"
                                 % repr(index_position))

        # Prepare the map
        self._map_canvas = self._create_map_canvas(
            float(self._map_coords[2]) / # W
            float(self._map_coords[3]) ) # H

        # Prepare the grid
        self.grid = self._create_grid(self._map_canvas)

        # Commit the internal rendering stack of the map
        self._map_canvas.render()


    def _create_index_rendering(self, on_the_side):
        """
        Prepare to render the Street index.

        Args:
           on_the_side (bool): True=index on the side, False=at bottom.

        Return a couple (StreetIndexRenderer, StreetIndexRenderingArea).
        """
        # Now we determine the actual occupation of the index
        index_renderer = index.StreetIndexRenderer(self.rc.i18n,
                                                   self.street_index.categories)

        # We use a fake vector device to determine the actual
        # rendering characteristics
        fake_surface = cairo.PDFSurface(None,
                                        self.paper_width_pt,
                                        self.paper_height_pt)

        if on_the_side:
            index_max_width_pt \
                = self.MAX_INDEX_OCCUPATION_RATIO * self._usable_area_width_pt

            if not self.rc.i18n.isrtl():
                # non-RTL: Index is on the right
                index_area = index_renderer.precompute_occupation_area(
                    fake_surface,
                    ( self.paper_width_pt - Renderer.PRINT_SAFE_MARGIN_PT
                      - index_max_width_pt ),
                    ( Renderer.PRINT_SAFE_MARGIN_PT + self._title_margin_pt ),
                    index_max_width_pt,
                    self._usable_area_height_pt,
                    'width', 'right')
            else:
                # RTL: Index is on the left
                index_area = index_renderer.precompute_occupation_area(
                    fake_surface,
                    Renderer.PRINT_SAFE_MARGIN_PT,
                    ( Renderer.PRINT_SAFE_MARGIN_PT + self._title_margin_pt ),
                    index_max_width_pt,
                    self._usable_area_height_pt,
                    'width', 'left')
        else:
            # Index at the bottom of the page
            index_max_height_pt \
                = self.MAX_INDEX_OCCUPATION_RATIO * self._usable_area_height_pt

            index_area = index_renderer.precompute_occupation_area(
                fake_surface,
                Renderer.PRINT_SAFE_MARGIN_PT,
                ( self.paper_height_pt
                  - Renderer.PRINT_SAFE_MARGIN_PT
                  - self._copyright_margin_pt
                  - index_max_height_pt ),
                self._usable_area_width_pt,
                index_max_height_pt,
                'height', 'bottom')

        return index_renderer, index_area


    def _draw_title(self, ctx, w_dots, h_dots, font_face):
        """
        Draw the title at the current position inside a
        w_dots*h_dots rectangle.

        Args:
           ctx (cairo.Context): The Cairo context to use to draw.
           w_dots,h_dots (number): Rectangle dimension (ciaro units)
           font_face (str): Pango font specification.
        """

        # Title background
        ctx.save()
        ctx.set_source_rgb(0.8, 0.9, 0.96)
        ctx.rectangle(0, 0, w_dots, h_dots)
        ctx.fill()
        ctx.restore()

        # Retrieve and paint the OSM logo
        ctx.save()
        grp, logo_width = self._get_osm_logo(ctx, 0.8*h_dots)

        ctx.translate(w_dots - logo_width - 0.1*h_dots, 0.1*h_dots)
        ctx.set_source(grp)
        ctx.paint_with_alpha(0.5)
        ctx.restore()

        # Prepare the title
        pc = pangocairo.CairoContext(ctx)
        layout = pc.create_layout()
        layout.set_width(int((w_dots - 0.1*w_dots - logo_width) * pango.SCALE))
        if not self.rc.i18n.isrtl(): layout.set_alignment(pango.ALIGN_LEFT)
        else:                        layout.set_alignment(pango.ALIGN_RIGHT)
        fd = pango.FontDescription(font_face)
        fd.set_size(pango.SCALE)
        layout.set_font_description(fd)
        layout.set_text(self.rc.title)
        self._adjust_font_size(layout, fd, layout.get_width(), 0.8*h_dots)

        # Draw the title
        ctx.save()
        ctx.rectangle(0, 0, w_dots, h_dots)
        ctx.stroke()
        ctx.translate(0.1*h_dots,
                      (h_dots -
                       (layout.get_size()[1] / pango.SCALE)) / 2.0)
        pc.show_layout(layout)
        ctx.restore()


    def _draw_copyright_notice(self, ctx, w_dots, h_dots, notice=None):
        """
        Draw a copyright notice at current location and within the
        given w_dots*h_dots rectangle.

        Args:
           ctx (cairo.Context): The Cairo context to use to draw.
           w_dots,h_dots (number): Rectangle dimension (ciaro units).
           font_face (str): Pango font specification.
           notice (str): Optional notice to replace the default.
        """
        today = datetime.date.today()
        notice = notice or \
            _(u'Copyright © %(year)d MapOSMatic/OCitySMap developers. '
              u'Map data © %(year)d OpenStreetMap.org '
              u'and contributors (cc-by-sa).\n'
              u'This map has been rendered on %(date)s and may be '
              u'incomplete or innacurate. '
              u'You can contribute to improve this map. '
              u'See http://wiki.openstreetmap.org')

        notice = notice % {'year': today.year,
                           'date': today.strftime("%d %B %Y")}

        ctx.save()
        pc = pangocairo.CairoContext(ctx)
        fd = pango.FontDescription('DejaVu')
        fd.set_size(pango.SCALE)
        layout = pc.create_layout()
        layout.set_font_description(fd)
        layout.set_text(notice)
        self._adjust_font_size(layout, fd, w_dots, h_dots)
        pc.show_layout(layout)
        ctx.restore()


    def render(self, cairo_surface, dpi):
        """Renders the map, the index and all other visual map features on the
        given Cairo surface.

        Args:
            cairo_surface (Cairo.Surface): the destination Cairo device.
            dpi (int): dots per inch of the device.
        """
        LOG.info('SinglePageRenderer rendering on %dx%dmm paper at %d dpi.' %
                 (self.rc.paper_width_mm, self.rc.paper_height_mm, dpi))

        # First determine some useful drawing parameters
        safe_margin_dots \
            = UTILS.convert_pt_to_dots(Renderer.PRINT_SAFE_MARGIN_PT, dpi)
        usable_area_width_dots \
            = UTILS.convert_pt_to_dots(self._usable_area_width_pt, dpi)
        usable_area_height_dots \
            = UTILS.convert_pt_to_dots(self._usable_area_height_pt, dpi)

        title_margin_dots \
            = UTILS.convert_pt_to_dots(self._title_margin_pt, dpi)

        copyright_margin_dots \
            = UTILS.convert_pt_to_dots(self._copyright_margin_pt, dpi)

        map_coords_dots = map(lambda l: UTILS.convert_pt_to_dots(l, dpi),
                              self._map_coords)

        ctx = cairo.Context(cairo_surface)

        ##
        ## Draw the map, scaled to fit the designated area
        ##
        ctx.save()

        # Prepare to draw the map at the right location
        ctx.translate(map_coords_dots[0], map_coords_dots[1])

        # Draw the rescaled Map
        ctx.save()
        rendered_map = self._map_canvas.get_rendered_map()
        ctx.scale(map_coords_dots[2]
                    / rendered_map.width,
                  map_coords_dots[3]
                    / rendered_map.height)
        mapnik.render(rendered_map, ctx)
        ctx.restore()

        # Draw a rectangle around the map
        ctx.rectangle(0, 0, map_coords_dots[2], map_coords_dots[3])
        ctx.stroke()

        # Place the vertical and horizontal square labels
        self._draw_labels(ctx, self.grid,
                          map_coords_dots[2],
                          map_coords_dots[3],
                          UTILS.convert_pt_to_dots(self._grid_legend_margin_pt,
                                                   dpi))
        ctx.restore()

        ##
        ## Draw the index, when applicable
        ##
        if self._index_renderer and self._index_area:
            ctx.save()
            self._index_renderer(ctx, self._index_area)
            ctx.restore()

        ##
        ## Draw the title
        ##
        ctx.save()
        ctx.translate(safe_margin_dots, safe_margin_dots)
        self._draw_title(ctx, usable_area_width_dots,
                         title_margin_dots, 'Georgia Bold')
        ctx.restore()

        ##
        ## Draw the copyright notice
        ##
        ctx.save()

        # Move to the right position
        ctx.translate(safe_margin_dots,
                      ( safe_margin_dots + title_margin_dots
                        + usable_area_height_dots
                        + copyright_margin_dots/4. ) )

        # Draw the copyright notice
        self._draw_copyright_notice(ctx, usable_area_width_dots,
                                    copyright_margin_dots)
        ctx.restore()

        # TODO: map scale
        # TODO: compass rose

        cairo_surface.flush()

    @staticmethod
    def _generic_get_compatible_paper_sizes(bounding_box, zoom_level,
                                            resolution_km_in_mm=Renderer.DEFAULT_KM_IN_MM, index_position = None):
        """Returns a list of the compatible paper sizes for the given bounding
        box. The list is sorted, smaller papers first, and a "custom" paper
        matching the dimensions of the bounding box is added at the end.

        Args:
            bounding_box (coords.BoundingBox): the map geographic bounding box.
            zoom_level (int): the Mapnik zoom level to use, generally 16.
            resolution_km_in_mm (int): size of a geographic kilometer in
                milimeters on the rendered map.
           index_position (str): None or 'side' (index on side),
              'bottom' (index at bottom).

        Returns a list of tuples (paper name, width in mm, height in mm). Paper
        sizes are represented in portrait mode.
        """
        geo_height_m, geo_width_m = bounding_box.spheric_sizes()
        paper_width_mm = int(geo_width_m/1000.0 * resolution_km_in_mm)
        paper_height_mm = int(geo_height_m/1000.0 * resolution_km_in_mm)

        LOG.debug('Map represents %dx%dm, needs at least %.1fx%.1fcm '
                  'on paper.' % (geo_width_m, geo_height_m,
                                 paper_width_mm/10., paper_height_mm/10.))

        # Take index into account, when applicable
        if index_position == 'side':
            paper_width_mm /= (1. -
                               SinglePageRenderer.MAX_INDEX_OCCUPATION_RATIO)
        elif index_position == 'bottom':
            paper_height_mm /= (1. -
                                SinglePageRenderer.MAX_INDEX_OCCUPATION_RATIO)

        # Test both portrait and landscape orientations when checking for paper
        # sizes.
        valid_sizes = []
        for name, w, h in Renderer.PAPER_SIZES:
            portrait_ok  = paper_width_mm <= w and paper_height_mm <= h
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


class SinglePageRendererNoIndex(SinglePageRenderer):

    name = 'plain'
    description = 'Full-page layout without index.'

    def __init__(self, rc, tmpdir, street_index):
        """
        Create the renderer.

        Args:
           rc (RenderingConfiguration): rendering parameters.
           tmpdir (os.path): Path to a temp dir that can hold temp files.
           street_index (StreetIndex): None or the street index object.
        """
        SinglePageRenderer.__init__(self, rc, tmpdir, None, None)


    @staticmethod
    def get_compatible_paper_sizes(bounding_box, zoom_level,
                                   resolution_km_in_mm=Renderer.DEFAULT_KM_IN_MM):
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
        return SinglePageRenderer._generic_get_compatible_paper_sizes(
            bounding_box, zoom_level, resolution_km_in_mm, None)


class SinglePageRendererIndexOnSide(SinglePageRenderer):

    name = 'single_page_index_side'
    description = 'Full-page layout with the index on the side.'

    def __init__(self, rc, tmpdir, street_index):
        """
        Create the renderer.

        Args:
           rc (RenderingConfiguration): rendering parameters.
           tmpdir (os.path): Path to a temp dir that can hold temp files.
           street_index (StreetIndex): None or the street index object.
        """
        SinglePageRenderer.__init__(self, rc, tmpdir, street_index, 'side')


    @staticmethod
    def get_compatible_paper_sizes(bounding_box, zoom_level,
                                   resolution_km_in_mm=Renderer.DEFAULT_KM_IN_MM):
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
        return SinglePageRenderer._generic_get_compatible_paper_sizes(
            bounding_box, zoom_level, resolution_km_in_mm, 'side')


class SinglePageRendererIndexBottom(SinglePageRenderer):

    name = 'single_page_index_bottom'
    description = 'Full-page layout with the index at the bottom.'

    def __init__(self, rc, tmpdir, street_index):
        """
        Create the renderer.

        Args:
           rc (RenderingConfiguration): rendering parameters.
           tmpdir (os.path): Path to a temp dir that can hold temp files.
           street_index (StreetIndex): None or the street index object.
        """
        SinglePageRenderer.__init__(self, rc, tmpdir, street_index, 'bottom')


    @staticmethod
    def get_compatible_paper_sizes(bounding_box, zoom_level,
                                   resolution_km_in_mm=Renderer.DEFAULT_KM_IN_MM):
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
        return SinglePageRenderer._generic_get_compatible_paper_sizes(
            bounding_box, zoom_level, resolution_km_in_mm, 'bottom')


# The renderers registry
_RENDERERS = [ SinglePageRendererNoIndex,
               SinglePageRendererIndexOnSide,
               SinglePageRendererIndexBottom ]

def get_renderer_class_by_name(name):
    """Retrieves a renderer class, by name."""
    for renderer in _RENDERERS:
        if renderer.name == name:
            return renderer
    raise LookupError, 'The requested renderer %s was not found!' % name

def get_renderers():
    """Returns the list of available renderers' names."""
    return _RENDERERS

def get_paper_sizes():
    """Returns a list of paper sizes specifications, 3-uples (name, width in
    millimeters, height in millimeters). The paper sizes are returned assuming
    portrait mode."""
    return Renderer.PAPER_SIZES

if __name__ == '__main__':
    import coords
    import i18n

    # Hack to fake gettext
    try:
        _(u"Test gettext")
    except NameError:
        _ = lambda x: x

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
            self.shade_color = 'black'
            self.shade_alpha = 0.7

    class RenderingConfigurationMock:
        def __init__(self):
            self.stylesheet = StylesheetMock()
            self.bounding_box = bbox
            self.paper_width_mm = papers[0][1]
            self.paper_height_mm = papers[0][2]
            self.i18n  = i18n.i18n()
            self.title = 'Au Kremlin-Bycêtre'
            self.polygon_wkt = bbox.as_wkt()

    config = RenderingConfigurationMock()

    plain = renderer_cls(config, '/tmp', None)
    surface = cairo.PDFSurface('/tmp/plain.pdf',
                   UTILS.convert_mm_to_pt(config.paper_width_mm),
                   UTILS.convert_mm_to_pt(config.paper_height_mm))

    plain.render(surface, UTILS.PT_PER_INCH)
    surface.finish()

    print "Generated /tmp/plain.pdf"

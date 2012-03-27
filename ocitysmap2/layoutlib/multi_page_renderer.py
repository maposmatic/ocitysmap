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

import os
import logging
import tempfile
import math
import sys
import cairo
import mapnik
import coords

from abstract_renderer import Renderer

from ocitysmap2.maplib.map_canvas import MapCanvas

import ocitysmap2
import commons

LOG = logging.getLogger('ocitysmap')
PAGE_STR = " - Page %(page_number)d"

_MAPNIK_PROJECTION = "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 " \
                     "+lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m   " \
                     "+nadgrids=@null +no_defs +over"

class MultiPageRenderer(Renderer):
    """
    This Renderer creates a multi-pages map, with all the classic overlayed
    features and no index page.
    """

    name = 'multi_page'
    description = 'A multi-page layout.'
    multipages = True

    def __init__(self, *args, **kwargs):
        Renderer.__init__(self, *args, **kwargs)

        print "One page width  (in mm) : %f" % self.rc.paper_width_mm
        print "One page height (in mm) : %f" % self.rc.paper_height_mm

        # Compute the usable area per page
        self._usable_area_width_pt = (self.paper_width_pt -
                                      (2 * Renderer.PRINT_SAFE_MARGIN_PT))
        self._usable_area_height_pt = (self.paper_height_pt -
                                       (2 * Renderer.PRINT_SAFE_MARGIN_PT))

        scale_denom = 10000
        OUTTER_MARGIN_MM = 20

        print 'BoundingBox(%f,%f,%f,%f,"original", {color: "#00ff00"})' % \
            (self.rc.bounding_box.get_top_left()[0],
             self.rc.bounding_box.get_top_left()[1],
             self.rc.bounding_box.get_bottom_right()[0],
             self.rc.bounding_box.get_bottom_right()[1])

        # Convert the original Bounding box into Mercator meters
        self._proj = mapnik.Projection(_MAPNIK_PROJECTION)
        orig_envelope = self._project_envelope(self.rc.bounding_box)

        # Extend the bounding box to take into account the lost outter
        # margin
        off_x  = orig_envelope.minx - (OUTTER_MARGIN_MM * scale_denom) / 1000
        off_y  = orig_envelope.miny - (OUTTER_MARGIN_MM * scale_denom) / 1000
        width  = orig_envelope.width() + (2 * OUTTER_MARGIN_MM * scale_denom) / 1000
        height = orig_envelope.height() + (2 * OUTTER_MARGIN_MM * scale_denom) / 1000

        # Calculate the total width and height of paper needed to
        # render the geographical area at the current scale.
        total_width_pt   = commons.convert_mm_to_pt(float(width) * 1000 / scale_denom)
        total_height_pt  = commons.convert_mm_to_pt(float(height) * 1000 / scale_denom)
        outter_margin_pt = commons.convert_mm_to_pt(OUTTER_MARGIN_MM)

        # Calculate the number of pages needed in both directions
        if total_width_pt < self._usable_area_width_pt:
            nb_pages_width = 1
        else:
            nb_pages_width = \
                (float(total_width_pt - self._usable_area_width_pt) / \
                     (self._usable_area_width_pt - outter_margin_pt)) + 1

        if total_height_pt < self._usable_area_height_pt:
            nb_pages_height = 1
        else:
            nb_pages_height = \
                (float(total_height_pt - self._usable_area_height_pt) / \
                     (self._usable_area_height_pt - outter_margin_pt)) + 1

        # Round up the number of pages needed so that we have integer
        # number of pages
        nb_pages_width = int(math.ceil(nb_pages_width))
        nb_pages_height = int(math.ceil(nb_pages_height))

        # Calculate the entire paper area available
        total_width_pt_after_extension = \
            self._usable_area_width_pt + (self._usable_area_width_pt - outter_margin_pt) * (nb_pages_width - 1)
        total_height_pt_after_extension = \
            self._usable_area_height_pt + (self._usable_area_height_pt - outter_margin_pt) * (nb_pages_height - 1)

        # Convert this paper area available in the number of Mercator
        # meters that can we rendered on the map
        total_width_merc = \
            commons.convert_pt_to_mm(total_width_pt_after_extension) * scale_denom / 1000
        total_height_merc = \
            commons.convert_pt_to_mm(total_height_pt_after_extension) * scale_denom / 1000

        # Extend the geographical boundaries so that we completely
        # fill the available paper size. We are careful to extend the
        # boundaries evenly on all directions (so the center of the
        # previous boundaries remain the same as the new one)
        off_x -= (total_width_merc - width) / 2
        width = total_width_merc
        off_y -= (total_height_merc - height) / 2
        height = total_height_merc

        # Calculate what is the final global bounding box that we will render
        envelope = mapnik.Box2d(off_x, off_y, off_x + width, off_y + height)
        self._geo_bbox = self._inverse_envelope(envelope)

        print 'BoundingBox(%f,%f,%f,%f,"extended", {color: "#0f0f0f"})' % \
            (self._geo_bbox.get_top_left()[0],
             self._geo_bbox.get_top_left()[1],
             self._geo_bbox.get_bottom_right()[0],
             self._geo_bbox.get_bottom_right()[1])

        # Convert the usable area on each sheet of paper into the
        # amount of Mercator meters we can render in this area.
        usable_area_merc_m_width  = commons.convert_pt_to_mm(self._usable_area_width_pt) * scale_denom / 1000
        usable_area_merc_m_height = commons.convert_pt_to_mm(self._usable_area_height_pt) * scale_denom / 1000
        outter_margin_merc_m      = (OUTTER_MARGIN_MM * scale_denom) / 1000

        # Calculate all the bounding boxes that correspond to the
        # geographical area that will be rendered on each sheet of
        # paper.
        bboxes = []
        for j in reversed(range(0, nb_pages_height)):
            for i in range(0, nb_pages_width):
                cur_x = off_x + i * (usable_area_merc_m_width - outter_margin_merc_m)
                cur_y = off_y + j * (usable_area_merc_m_height - outter_margin_merc_m)
                envelope = mapnik.Box2d(cur_x, cur_y,
                                        cur_x+usable_area_merc_m_width,
                                        cur_y+usable_area_merc_m_height)
                bboxes.append(self._inverse_envelope(envelope))

        for i, bb in enumerate(bboxes):
            print 'BoundingBox(%f,%f,%f,%f,"p%d")' % \
                (bb.get_top_left()[0],
                 bb.get_top_left()[1],
                 bb.get_bottom_right()[0],
                 bb.get_bottom_right()[1], i)

        # Create the map canvas for each page
        self.canvas = []
        print "List of all bboxes"
        for bb in bboxes:
            print bb
            # Create one canvas for each page
            map_canvas = MapCanvas(self.rc.stylesheet,
                                   bb, graphical_ratio=None)

            map_canvas.render()

            self.canvas.append(map_canvas)

        self.map_coords = (Renderer.PRINT_SAFE_MARGIN_PT,
                           Renderer.PRINT_SAFE_MARGIN_PT,
                           self._usable_area_width_pt,
                           self._usable_area_height_pt)

        print self.canvas

    def _project_envelope(self, bbox):
        """Project the given bounding box into the rendering projection."""
        envelope = mapnik.Box2d(bbox.get_top_left()[1],
                                bbox.get_top_left()[0],
                                bbox.get_bottom_right()[1],
                                bbox.get_bottom_right()[0])
        c0 = self._proj.forward(mapnik.Coord(envelope.minx, envelope.miny))
        c1 = self._proj.forward(mapnik.Coord(envelope.maxx, envelope.maxy))
        return mapnik.Box2d(c0.x, c0.y, c1.x, c1.y)

    def _inverse_envelope(self, envelope):
        """Inverse the given cartesian envelope (in 900913) back to a 4002
        bounding box."""
        c0 = self._proj.inverse(mapnik.Coord(envelope.minx, envelope.miny))
        c1 = self._proj.inverse(mapnik.Coord(envelope.maxx, envelope.maxy))
        return coords.BoundingBox(c0.y, c0.x, c1.y, c1.x)

    def render(self, cairo_surface, dpi, osm_date):
        ctx = cairo.Context(cairo_surface)
        for c in self.canvas:
            ctx.save()

            # Prepare to draw the map at the right location
            ctx.translate(commons.convert_pt_to_dots(Renderer.PRINT_SAFE_MARGIN_PT),
                          commons.convert_pt_to_dots(Renderer.PRINT_SAFE_MARGIN_PT))

            ctx.save()
            rendered_map = c.get_rendered_map()
            ctx.scale(commons.convert_pt_to_dots(self._usable_area_width_pt)
                      / rendered_map.width,
                      commons.convert_pt_to_dots(self._usable_area_height_pt)
                      / rendered_map.height)
            mapnik.render(rendered_map, ctx)
            ctx.restore()

            ctx.restore()

            cairo_surface.show_page()
        cairo_surface.flush()
        print "I'm rendering"
        pass

    # Convert a length in geometric meters (in the real life) into a
    # length in paper millimiters (as drawn on the map).
    def _geo_m_to_paper_mm(self, geo_m):
        return geo_m / 1000.0 * Renderer.DEFAULT_KM_IN_MM * 2

    def _paper_mm_to_geo_m(self, paper_mm):
        return paper_mm * 1000.0 / (Renderer.DEFAULT_KM_IN_MM * 2)

    def _paper_pt_to_geo_m(self, paper_pt):
        return self._paper_mm_to_geo_m(commons.convert_pt_to_mm(paper_pt))

    # In multi-page mode, we only accept A4, A5 and US letter as paper
    # sizes. The goal is to render booklets, not posters.
    @staticmethod
    def get_compatible_paper_sizes(bounding_box, zoom_level,
                                   resolution_km_in_mm=Renderer.DEFAULT_KM_IN_MM,
                                   index_position=None, hsplit=1, vsplit=1):
        valid_sizes = []
        acceptable_formats = [ 'A5', 'A4', 'US letter' ]
        for sz in ocitysmap2.layoutlib.PAPER_SIZES:
            # Skip unsupported paper formats
            if sz[0] not in acceptable_formats:
                continue
            valid_sizes.append((sz[0], sz[1], sz[2], True, True))
        return valid_sizes


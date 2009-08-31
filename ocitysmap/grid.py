# -*- coding: utf-8 -*-

# ocitysmap, city map and street index generator from OpenStreetMap data
# Copyright (C) 2009  David Decotigny
# Copyright (C) 2009  Frédéric Lehobey
# Copyright (C) 2009  David Mentré
# Copyright (C) 2009  Maxime Petazzoni
# Copyright (C) 2009  Thomas Petazzoni
# Copyright (C) 2009  Gaël Utard

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


import math, logging
import map_canvas, utils,  coords

l = logging.getLogger('ocitysmap')

class GridDescriptor:
    def __init__(self, bbox, db):
        self.bbox = bbox
        height, width = bbox.spheric_sizes()

        # Compute number of squares, assumming a size of 500 meters
        # per square
        self.width_square_count  = width / 500
        self.height_square_count = height / 500

        # Compute the size in angles of the squares
        self.width_square_angle  = (abs(bbox.get_top_left()[1] -
                                        bbox.get_bottom_right()[1]) /
                                    self.width_square_count)
        self.height_square_angle = (abs(bbox.get_top_left()[0] -
                                        bbox.get_bottom_right()[0]) /
                                    self.height_square_count)

        # Compute the lists of longitudes and latitudes of the
        # horizontal and vertical lines delimiting the square
        self.vertical_lines   = [bbox.get_top_left()[1] +
                                 x * self.width_square_angle
                                 for x in xrange(0, int(math.floor(self.width_square_count )) + 1)]
        self.horizontal_lines = [bbox.get_top_left()[0] -
                                 x * self.height_square_angle
                                 for x in xrange(0, int(math.floor(self.height_square_count)) + 1)]

        # Compute the lists of labels
        self.vertical_labels   = [utils.gen_vertical_square_label(x)
                                  for x in xrange(0, int(math.ceil(self.width_square_count)))]
        self.horizontal_labels = [utils.gen_horizontal_square_label(x)
                                  for x in xrange(0, int(math.ceil(self.height_square_count)))]
        l.debug("vertical lines: %s" % self.vertical_lines)
        l.debug("horizontal lines: %s" % self.horizontal_lines)
        l.debug("vertical labels: %s" % self.vertical_labels)
        l.debug("horizontal labels: %s" % self.horizontal_labels)

    def generate_shape_file(self, filename, bbox):
        g = map_canvas.GridFile(bbox, filename)
        for v in self.vertical_lines:
            g.add_vert_line(v)
        for h in self.horizontal_lines:
            g.add_horiz_line(h)
        g.flush()
        return g

    def generate_scale_shape_file(self, filename, base_lat):
        """
        Returns a tuple (gridfile, lat, long) of the scale widget, or
        None when not enough room for scale
        """
        if len(self.horizontal_lines) < 2 or len(self.vertical_lines) < 2:
            return None

        height_lat = (self.horizontal_lines[-2] - self.horizontal_lines[-1])/30

        # Make sure there is enough room between the last horiz line
        # and the bottom:
        if base_lat + (self.horizontal_lines[-1] - base_lat) / 3. \
                + 2*height_lat < self.horizontal_lines[-1]:
            line_lat = base_lat + (self.horizontal_lines[-1] - base_lat) / 3.
        else:
            # Nope...
            line_lat = self.horizontal_lines[-1] \
                + (self.horizontal_lines[-2] - self.horizontal_lines[-1]) \
                / 5.

        bbox = coords.BoundingBox(line_lat + height_lat,
                                  self.vertical_lines[0]-1.e-5,
                                  line_lat - height_lat,
                                  self.vertical_lines[1]+1.e-5)

        g = map_canvas.GridFile(bbox, filename) # bbox, filename)
        g.add_horiz_line(line_lat)
        g.add_vert_line(self.vertical_lines[0])
        g.add_vert_line(self.vertical_lines[1])
        g.flush()
        return (g, line_lat + height_lat,
                (self.vertical_lines[0] + self.vertical_lines[1]) / 2)

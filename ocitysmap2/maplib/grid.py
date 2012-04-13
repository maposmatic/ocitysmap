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
import math

import shapes

l = logging.getLogger('ocitysmap')

class Grid:
    """
    The Grid class defines the grid overlayed on a rendered map. It controls
    the grid size, number and size of squares, etc.
    """

    # Approximative paper size of the grid squares (+/- 33%).
    GRID_APPROX_PAPER_SIZE_MM = 40

    def __init__(self, bounding_box, scale, rtl=False):
        """Creates a new grid for the given bounding box.

        Args:
            bounding_box (coords.BoundingBox): the map bounding box.
            rtl (boolean): whether the map is rendered in right-to-left mode or
                not. Defaults to False.
        """

        self._bbox = bounding_box
        self.rtl   = rtl
        self._height_m, self._width_m = bounding_box.spheric_sizes()

        l.info('Laying out grid on %.1fx%.1fm area...' %
               (self._width_m, self._height_m))

        # compute the terrain grid size corresponding to the targeted paper size
        size = float(self.GRID_APPROX_PAPER_SIZE_MM) * scale / 1000
        # compute the scientific notation of this size :
        # size = significant * 10 ^ exponent with 1 <= significand < 10
        exponent = math.log10(size)
        significand = float(size) / 10 ** int(exponent)
        # "round" this size to be 1, 2, 2.5 or 5 multiplied by a power of 10
        if significand < 1.5:
            significand = 1
        elif significand < 2.25:
            significand = 2
        elif significand < 3.75:
            significand = 2.5
        elif significand < 7.5:
            significand = 5
        else:
            significand = 10
        size = significand * 10 ** int(exponent)
        # use it
        self.grid_size_m = size
        self.horiz_count = self._width_m / size
        self.vert_count = self._height_m / size

        self._horiz_angle_span = abs(self._bbox.get_top_left()[1] -
                                     self._bbox.get_bottom_right()[1])
        self._vert_angle_span  = abs(self._bbox.get_top_left()[0] -
                                     self._bbox.get_bottom_right()[0])

        self._horiz_unit_angle = (self._horiz_angle_span / self.horiz_count)
        self._vert_unit_angle  = (self._vert_angle_span / self.vert_count)

        self._horizontal_lines = [ ( self._bbox.get_top_left()[0] -
                                    (x+1) * self._vert_unit_angle)
                                  for x in xrange(int(math.floor(self.vert_count)))]
        self._vertical_lines   = [ (self._bbox.get_top_left()[1] +
                                    (x+1) * self._horiz_unit_angle)
                                   for x in xrange(int(math.floor(self.horiz_count)))]

        self.horizontal_labels = map(self._gen_horizontal_square_label,
                                      xrange(int(math.ceil(self.horiz_count))))
        self.vertical_labels = map(self._gen_vertical_square_label,
                                   xrange(int(math.ceil(self.vert_count))))

        l.info('Using %sx%sm grid (%sx%s squares).' %
               (self.grid_size_m, self.grid_size_m,
                self.horiz_count, self.vert_count))

    def generate_shape_file(self, filename):
        """Generates the grid shapefile with all the horizontal and
        vertical lines added.

        Args:
            filename (string): path to the temporary shape file that will be
                generated.
        Returns the ShapeFile object.
        """

        # Use a slightly larger bounding box for the shape file to accomodate
        # for the small imprecisions of re-projecting.
        g = shapes.LineShapeFile(self._bbox.create_expanded(0.001, 0.001),
                                 filename, 'grid')
        map(g.add_vert_line, self._vertical_lines)
        map(g.add_horiz_line, self._horizontal_lines)
        return g

    def _gen_horizontal_square_label(self, x):
        """Generates a human-readable label for the given horizontal square
        number. For example:
             1 -> A
             2 -> B
            26 -> Z
            27 -> AA
            28 -> AB
            ...
        """
        if self.rtl:
            x = len(self._vertical_lines) - x

        label = ''
        while x != -1:
            label = chr(ord('A') + x % 26) + label
            x = x/26 - 1
        return label

    def _gen_vertical_square_label(self, x):
        """Generate a human-readable label for the given vertical square
        number. Since we put numbers verticaly, this is simply x+1."""
        return str(x + 1)

    def get_location_str(self, lattitude, longitude):
        """
        Translate the given lattitude/longitude (EPSG:4326) into a
        string of the form "CA42"
        """
        hdelta = min(abs(longitude - self._bbox.get_top_left()[1]),
                     self._horiz_angle_span)
        hlabel = self.horizontal_labels[int(hdelta / self._horiz_unit_angle)]

        vdelta = min(abs(lattitude - self._bbox.get_top_left()[0]),
                     self._vert_angle_span)
        vlabel = self.vertical_labels[int(vdelta / self._vert_unit_angle)]

        return "%s%s" % (hlabel, vlabel)


if __name__ == "__main__":
    from ocitysmap2 import coords

    logging.basicConfig(level=logging.DEBUG)
    grid = Grid(coords.BoundingBox(44.4883, -1.0901, 44.4778, -1.0637))
    shape = grid.generate_shape_file('/tmp/mygrid.shp')

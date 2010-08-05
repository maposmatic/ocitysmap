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

import coords
import shapes

l = logging.getLogger('ocitysmap')

class Grid:
    """
    The Grid class defines the grid overlayed on a rendered map. It controls
    the grid size, nuber and size of squares, etc.
    """

    # Available and supported grid sizes, in meters.
    AVAILABLE_GRID_SIZES_METERS = [50, 100, 250, 500]

    # Number of squares under which a smaller grid size is used (until no
    # smaller size is available).
    GRID_COUNT_TRESHOLD = 4

    def __init__(self, bounding_box, rtl=False):
        """Creates a new grid for the given bounding box.

        Args:
            bounding_box (coords.BoundingBox): the map bounding box.
            rtl (boolean): whether the map is rendered in right-to-left mode or
                not. Defaults to False.
        """

        self._bbox = bounding_box
        self._height_m, self._width_m = bounding_box.spheric_sizes()

        for size in sorted(Grid.AVAILABLE_GRID_SIZES_METERS, reverse=True):
            self.grid_size_m = size
            self.horiz_count = self._width_m / size
            self.vert_count = self._height_m / size

            if (min(self.horiz_count, self.vert_count) >
                Grid.GRID_COUNT_TRESHOLD):
                break

        l.info('Using %dx%dm grid (%dx%d squares).' % (self.grid_size_m,
                                                       self.grid_size_m,
                                                       self.horiz_count,
                                                       self.vert_count))

        self._horiz_angle = (abs(self._bbox.get_top_left()[1] -
                                 self._bbox.get_bottom_right()[1]) /
                             self.horiz_count)
        self._vert_angle  = (abs(self._bbox.get_top_left()[0] -
                                 self._bbox.get_bottom_right()[0]) /
                             self.vert_count)

        self._horizontal_lines = [self._bbox.get_top_left()[0] -
                                  (x+1) * self._vert_angle for x in xrange(
                                      int(math.floor(self.vert_count)))]
        self._vertical_lines   = [self._bbox.get_top_left()[1] +
                                  (x+1) * self._horiz_angle for x in xrange(
                                      int(math.floor(self.horiz_count)))]

        self.horizontal_labels = map(self._gen_horizontal_square_label,
                                      xrange(int(math.ceil(self.horiz_count))))
        if rtl:
            self.horizontal_labels.reverse()
        self.vertical_labels = map(self._gen_vertical_square_label,
                                   xrange(int(math.ceil(self.vert_count))))

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
        label = ''
        while x != -1:
            label = chr(ord('A') + x % 26) + label
            x = x/26 - 1
        return label

    def _gen_vertical_square_label(self, x):
        return str(x + 1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    grid = Grid(coords.BoundingBox(44.4883, -1.0901, 44.4778, -1.0637))
    shape = grid.generate_shape_file('/tmp/mygrid.shp')

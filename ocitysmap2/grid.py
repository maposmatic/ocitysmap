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

    AVAILABLE_GRID_SIZES_METERS = [50, 100, 250, 750, 500]
    GRID_COUNT_TRESHOLD = 4

    def __init__(self, boundingbox):
        self._bbox = boundingbox
        self._height_m, self._width_m = boundingbox.spheric_sizes()

        for size in sorted(Grid.AVAILABLE_GRID_SIZES_METERS, reverse=True):
            self._grid_size = size
            self._horiz_count = self._width_m / size
            self._vert_count = self._height_m / size

            if (min(self._horiz_count, self._vert_count) >
                Grid.GRID_COUNT_TRESHOLD):
                break

        l.info('Using %dx%dm grid (%dx%d squares).' % (self._grid_size,
                                                       self._grid_size,
                                                       self._horiz_count,
                                                       self._vert_count))

        self._horiz_angle = (abs(self._bbox.get_top_left()[1] -
                                 self._bbox.get_bottom_right()[1]) /
                             self._horiz_count)
        self._vert_angle  = (abs(self._bbox.get_top_left()[0] -
                                 self._bbox.get_bottom_right()[0]) /
                             self._vert_count)

        self._horizontal_lines = [self._bbox.get_top_left()[0] -
                                  (x+1) * self._vert_angle for x in xrange(
                                      int(math.floor(self._vert_count)))]
        self._vertical_lines   = [self._bbox.get_top_left()[1] +
                                  (x+1) * self._horiz_angle for x in xrange(
                                      int(math.floor(self._horiz_count)))]

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
        g = shapes.LineShapeFile(self._bbox.create_expanded(0.05, 0.05),
                                 filename, 'grid')
        map(g.add_vert_line, self._vertical_lines)
        map(g.add_horiz_line, self._horizontal_lines)
        return g

if __name__ == "__main__":
    # Basic unit test
    import coords

    logging.basicConfig(level=logging.DEBUG)

    grid = Grid(coords.BoundingBox(44.4883, -1.0901, 44.4778, -1.0637))
    shape = grid.generate_shape_file('/tmp/mygrid.shp')

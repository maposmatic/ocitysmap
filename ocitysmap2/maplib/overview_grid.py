# -*- coding: utf-8 -*-

# ocitysmap, city map and street index generator from OpenStreetMap data

import logging
import math

import shapes

l = logging.getLogger('ocitysmap')

class OverviewGrid:
    """
    The OverviewGrid class draw the grid overlayed on the overview map of a
    multi-page render.
    """

    def __init__(self, bounding_box, pages_bounding_boxes, rtl=False):
        """Creates a new grid for the given bounding boxes.

        Args:
            bounding_box (coords.BoundingBox): the map bounding box.
            bounding_box (list of coords.BoundingBox): bounding boxes of the
                pages.
            rtl (boolean): whether the map is rendered in right-to-left mode or
                not. Defaults to False.
        """

        self._bbox = bounding_box
        self._pages_bbox = pages_bounding_boxes
        self.rtl   = rtl
        self._height_m, self._width_m = bounding_box.spheric_sizes()

        l.info('Laying out of overview grid on %.1fx%.1fm area...' %
               (self._width_m, self._height_m))

        self._pages_wkt = [bb.as_wkt() for bb in self._pages_bbox]

        self.horiz_count = 1
        self.vert_count = 1
        self.horizontal_labels = ['plouf']
        self.vertical_labels = ['plouf']

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
        g = shapes.BoxShapeFile(self._bbox.create_expanded(0.001, 0.001),
                                 filename, 'grid')
        map(g.add_box, self._pages_bbox)
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
    logging.basicConfig(level=logging.DEBUG)
    pass

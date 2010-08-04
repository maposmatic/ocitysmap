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

class StreetIndex:
    """
    The StreetIndex class encapsulate all the logic related to the querying and
    rendering of the street index.
    """

    def __init__(self, osmid, bounding_box, language, grid):
        self._osmid = osmid
        self._bbox = bounding_box
        self._language = language
        self._grid = grid

    def render(self, surface, x, y, w, h):
        """Render the street and amenities index at the given (x,y) coordinates
        into the provided Cairo surface. The index must not be larger than the
        provided width and height (in pixels).

        Args:
            x (int): horizontal origin position, in pixels.
            y (int): vertical origin position, in pixels.
            w (int): maximum usable width for the index, in pixels.
            h (int): maximum usable height for the index, in pixels.
        """
        ctx = cairo.Context(surface)
        ctx.move_to(x, y)

        # TODO: render index into ctx

        return surface

    def as_csv(self, fobj):
        """Saves the street index as CSV to the provided file object."""

        # TODO: write to CSV

        raise NotImplementedError

    def _get_streets(self):
        raise NotImplementedError

    def _get_amenities(self):
        raise NotImplementedError

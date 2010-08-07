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
import math
import pango
import pangocairo

from ocitysmap2 import coords, draw_utils, grid
from indexer import StreetIndex
from render import StreetIndexRenderer
from commons import IndexCategory, IndexItem

l = logging.getLogger('ocitysmap')


if __name__ == '__main__':
    import random
    import string

    import render

    random.seed(42)

    bbox = coords.BoundingBox(48.8162, 2.3417, 48.8063, 2.3699)
    grid = grid.Grid(bbox)

    surface = cairo.PDFSurface('/tmp/index.pdf', 1000, 1000)

    class i18nMock:
        def __init__(self, rtl):
            self.rtl = rtl
        def isrtl(self):
            return self.rtl

    margin = 50
    width = 800
    height = 500

    streets = []
    for i in ['A', 'B', 'C', 'D', 'E', 'Schools', 'Public buildings']:
         streets.append(IndexCategory(i, [IndexItem(l,s) for l,s in
                    [(''.join(random.choice(string.letters) for i in xrange(random.randint(1, 10))), 'A1')]*4]))

    index = render.StreetIndexRenderer(i18nMock(False), streets, [])
    index.render(surface, 50, 50, width, height, 'height', 'top')
    surface.show_page()
    index.render(surface, 50, 50, width, height, 'height', 'bottom')
    surface.show_page()
    index.render(surface, 50, 50, width, height, 'width', 'left')
    surface.show_page()
    index.render(surface, 50, 50, width, height, 'width', 'right')
    surface.show_page()

    index = render.StreetIndexRenderer(i18nMock(True), streets, [])
    index.render(surface, 50, 50, width, height, 'height', 'top')
    surface.show_page()
    index.render(surface, 50, 50, width, height, 'height', 'bottom')
    surface.show_page()
    index.render(surface, 50, 50, width, height, 'width', 'left')
    surface.show_page()
    index.render(surface, 50, 50, width, height, 'width', 'right')

    surface.finish()


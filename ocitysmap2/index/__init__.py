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

from indexer import StreetIndex
from render  import StreetIndexRenderer
from commons import IndexCategory, IndexItem

if __name__ == '__main__':
    import os
    import string
    import random
    import psycopg2
    import cairo

    from ocitysmap2 import i18n, coords
    from ocitysmap2.index import commons

    import render

    random.seed(42)

    bbox = coords.BoundingBox(48.8162, 2.3417, 48.8063, 2.3699)

    # Build the list of index items
    db = psycopg2.connect(user='maposmatic',
                          password='waeleephoo3Aew3u',
                          host='localhost',
                          database='maposmatic')

    i18n = i18n.install_translation("fr_FR.UTF-8",
                                    os.path.join(os.path.dirname(__file__),
                                                 "..", "..", "locale"))

    street_index = StreetIndex(db, None, None, i18n, None, bbox.as_wkt())
    print street_index.categories

    # Render the items
    class i18nMock:
        def __init__(self, rtl):
            self.rtl = rtl
        def isrtl(self):
            return self.rtl

    width = 5*(20 / 2.54) * 72
    height = 5*(29 / 2.54) * 72

    surface = cairo.PDFSurface('/tmp/index.pdf', width, height)

    index = render.StreetIndexRenderer(i18nMock(False),
                                       street_index.categories)
    index.render(surface, 0, 0, width, height, 'height', 'top')
    surface.show_page()
    index.render(surface, 0, 0, width, height, 'height', 'bottom')
    surface.show_page()
    index.render(surface, 0, 0, width, height, 'width', 'left')
    surface.show_page()
    index.render(surface, 0, 0, width, height, 'width', 'right')
    surface.show_page()

    index = render.StreetIndexRenderer(i18nMock(True),
                                       street_index.categories)
    index.render(surface, 0, 0, width, height, 'height', 'top')
    surface.show_page()
    index.render(surface, 0, 0, width, height, 'height', 'bottom')
    surface.show_page()
    index.render(surface, 0, 0, width, height, 'width', 'left')
    surface.show_page()
    index.render(surface, 0, 0, width, height, 'width', 'right')

    surface.finish()
    print "Generated /tmp/index.pdf."

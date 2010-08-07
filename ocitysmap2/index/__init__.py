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

import coords
import draw_utils
import grid

l = logging.getLogger('ocitysmap')

class IndexEmptyError(Exception):
    pass

class IndexDoesNotFitError(Exception):
    pass

class IndexCategory:
    name = None
    items = None

    def __init__(self, name, items):
        self.name, self.items = name, items

    def __str__(self):
        return '<%s (%s)>' % (self.name, map(str, self.items))

    def draw(self, rtl, ctx, pc, layout, fascent, fheight,
             baseline_x, baseline_y):
        """Draw this category header.

        Args:
            ...
        """

        ctx.save()
        ctx.set_source_rgb(0.9, 0.9, 0.9)
        ctx.rectangle(baseline_x, baseline_y - fascent,
                      layout.get_width() / pango.SCALE, fheight)
        ctx.fill()

        ctx.set_source_rgb(0.0, 0.0, 0.0)
        ctx.move_to(baseline_x,
                    baseline_y - fascent)
        layout.set_alignment(pango.ALIGN_CENTER)
        layout.set_text(self.name)
        pc.show_layout(layout)
        ctx.restore()

    def get_all_item_labels(self):
        return [x.label for x in self.items]

    def get_all_item_squares(self):
        return [x.squares for x in self.items]

class IndexItem:
    __slots__ = ['label', 'squares']
    label = None
    squares = None

    def __init__(self, label, squares):
        self.label, self.squares = label, squares

    def __str__(self):
        return '%s...%s' % (self.label, self.squares)

    def draw(self, rtl, ctx, pc, layout, fascent, fheight,
             baseline_x, baseline_y):
        """Draw this index item to the provided Cairo context. It prints the
        label, the squares definition and the dotted line, with respect to the
        RTL setting.

        Args:
            rtl (boolean): right-to-left localization.
            ctx (cairo.Context): the Cairo context to draw to.
            pc (pangocairo.PangoCairo): the PangoCairo context for text
                drawing.
            layout (pango.Layout): the Pango layout to use for text
                rendering, pre-configured with the appropriate font.
            fascent (int): font ascent.
            fheight (int): font height.
            baseline_x (int): X axis coordinate of the baseline.
            baseline_y (int): Y axis coordinate of the baseline.
        """

        width = layout.get_width() / pango.SCALE

        ctx.save()
        if not rtl:
            line_start, _ = _draw_text_left(ctx, pc, layout,
                    fascent, fheight, baseline_x, baseline_y, self.label)
            line_end, _ = _draw_text_right(ctx, pc, layout,
                    fascent, fheight, baseline_x, baseline_y,
                    self.squares)
        else:
            line_start, _ = _draw_text_left(ctx, pc, layout,
                    fascent, fheight, baseline_x, baseline_y,
                    self.squares)
            line_end, _ = _draw_text_right(ctx, pc, layout,
                    fascent, fheight, baseline_x, baseline_y,
                    self.label)

        _draw_dotted_line(ctx, max(fheight/12, 1),
                          line_start + fheight/4, baseline_y,
                          line_end - line_start - fheight/2)
        ctx.restore()


class StreetIndex:
    def __init__(self, db, osmid, bounding_box, i18n, grid, polygon):
        self._db = db
        self._osmid = osmid
        self._bounding_box = bounding_box
        self._i18n = i18n
        self._grid = grid
        self._polygon = polygon

    def _humanize_street_label(self, street):
        return (self._i18n.user_readable_street(street[0]),
                self._user_readable_label(street[1]))

    def _humanize_street_list(self, sl):
        """Given a list of street and their corresponding squares, do some
        cleanup and pass it through the internationalization layer to
        get proper sorting, filtering of common prefixes, etc.

        Args:
            sl (list): list of streets, each in the form [(name, squares)].

        Returns the humanized street list.
        """

        # We transform the string representing the squares list into a
        # Python list
        sl = [(street[0],
               [map(int, x.split(',')) for x in street[1].split(';')[:-1]])
              for street in sl]

        # Street prefixes are postfixed, a human readable label is
        # built to represent the list of squares, and the list is
        # alphabetically-sorted.
        prev_locale = locale.getlocale(locale.LC_COLLATE)
        locale.setlocale(locale.LC_COLLATE, self._i18n.language_code())
        try:
            sl = sorted(map(self._humanize_street_label, sl),
                        lambda x, y: locale.strcoll(x[0].lower(), y[0].lower()))
        finally:
            locale.setlocale(locale.LC_COLLATE, prev_locale)

        result = []
        first_letter = None
        current_category = None
        for street in sl:
            if not self._i18n.first_letter_equal(street[0][0], first_letter):
                current_category = IndexCategory(street[0])
                result.append(current_category)
            current_category.items.append(IndexItem(street[0], street[1]))

        return result

    def get_streets(self):
        """Get the list of streets in the administrative area if city is
        defined or in the bounding box otherwise, and for each
        street, the list of squares that it intersects.

        Returns a list of the form [(street_name, 'A-B1'),
                                    (street2_name, 'B3')]
        """

        cursor = self._db.cursor()
        l.info("Getting streets...")

        intersect = 'true'
        if self._polygon:
            intersect = """st_intersects(way, st_transform(
                                GeomFromText('%s', 4002), 900913))""" % self._polygon

        cursor.execute("""select name, textcat_all(x || ',' || y || ';')
                          from (select distinct name, x, y
                                from planet_osm_line
                                join %s
                                on st_intersects(way, st_transform(geom, 900913))
                                where trim(name) != '' and highway is not null
                                and %s)
                          as foo
                          group by name
                          order by name;""" % \
                           (self._map_areas_table_name,
                            intersect))

        sl = cursor.fetchall()
        l.debug("Got streets (%d)." % len(sl))
        return self.humanize_street_list(sl)


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


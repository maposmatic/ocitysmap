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

import pango

import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import draw_utils

class IndexEmptyError(Exception):
    """This exception is raised when no data is to be rendered in the index."""
    pass

class IndexDoesNotFitError(Exception):
    """This exception is raised when the index does not fit in the given
    graphical area, even after trying smaller font sizes."""
    pass

class IndexCategory:
    """
    The IndexCategory represents a set of index items that belong to the same
    category (their first letter is the same or they are of the same amenity
    type).
    """
    name = None
    items = None
    is_street = False

    def __init__(self, name, items=None, is_street=True):
        assert name is not None
        self.name = name
        self.items = items or list()
        self.is_street = is_street

    def __str__(self):
        return '<%s (%s)>' % (self.name, map(str, self.items))

    def __repr__(self):
        return 'IndexCategory(%s, %s)' % (repr(self.name),
                                          repr(self.items))

    def draw(self, rtl, ctx, pc, layout, fascent, fheight,
             baseline_x, baseline_y):
        """Draw this category header.

        Args:
            rtl (boolean): whether to draw right-to-left or not.
            ctx (cairo.Context): the Cairo context to draw to.
            pc (pangocairo.CairoContext): the PangoCairo context.
            layout (pango.layout): the Pango layout to draw text into.
            fascent (int): font ascent.
            fheight (int): font height.
            baseline_x (int): base X axis position.
            baseline_y (int): base Y axis position.
        """

        ctx.save()
        ctx.set_source_rgb(0.9, 0.9, 0.9)
        ctx.rectangle(baseline_x, baseline_y - fascent,
                      layout.get_width() / pango.SCALE, fheight)
        ctx.fill()

        ctx.set_source_rgb(0.0, 0.0, 0.0)
        draw_utils.draw_text_center(ctx, pc, layout, fascent, fheight,
                                    baseline_x, baseline_y, self.name)
        ctx.restore()

    def get_all_item_labels(self):
        return [x.label for x in self.items]

    def get_all_item_squares(self):
        return [x.squares for x in self.items]


class IndexItem:
    """
    An IndexItem represents one item in the index (a street or a POI). It
    contains the item label (street name, POI name or description) and the
    humanized squares description.
    """
    __slots__    = ['label', 'endpoint1', 'endpoint2', 'location_str']
    label        = None # str
    endpoint1    = None # coords.Point
    endpoint2    = None # coords.Point
    location_str = None # str or None
    page_number  = None # integer or None. Only used by multi-page renderer.

    def __init__(self, label, endpoint1, endpoint2, page_number=None):
        assert label is not None
        self.label        = label
        self.endpoint1    = endpoint1
        self.endpoint2    = endpoint2
        self.location_str = None
        self.page_number  = page_number

    def __str__(self):
        return '%s...%s' % (self.label, self.location_str)

    def __repr__(self):
        return ('IndexItem(%s, %s, %s, %s, %s)'
                % (repr(self.label), self.endpoint1, self.endpoint2,
                   repr(self.location_str), repr(self.page_number)))

    def label_drawing_width(self, layout):
        layout.set_text(self.label)
        return float(layout.get_size()[0]) / pango.SCALE

    def label_drawing_height(self, layout):
        layout.set_text(self.label)
        return float(layout.get_size()[1]) / pango.SCALE

    def location_drawing_width(self, layout):
        layout.set_text(self.location_str)
        return float(layout.get_size()[0]) / pango.SCALE

    def draw(self, rtl, ctx, pc, column_layout, fascent, fheight,
             baseline_x, baseline_y,
             label_layout=None, label_height=0, location_width=0):
        """Draw this index item to the provided Cairo context. It prints the
        label, the squares definition and the dotted line, with respect to the
        RTL setting.

        Args:
            rtl (boolean): right-to-left localization.
            ctx (cairo.Context): the Cairo context to draw to.
            pc (pangocairo.PangoCairo): the PangoCairo context for text
                drawing.
            column_layout (pango.Layout): the Pango layout to use for text
                rendering, pre-configured with the appropriate font.
            fascent (int): font ascent.
            fheight (int): font height.
            baseline_x (int): X axis coordinate of the baseline.
            baseline_y (int): Y axis coordinate of the baseline.
        Optional args (in case of label wrapping):
            label_layout (pango.Layout): the Pango layout to use for text
                rendering, in case the label should be wrapped
            label_height (int): height of the big label
            location_width (int): width of the 'location' part
        """

        # Fallbacks in case we dont't have a wrapping label
        if label_layout == None:
            label_layout = column_layout
        if label_height == 0:
            label_height = fheight

        if not self.location_str:
            location_str = '???'
        else:
            location_str = self.location_str

        ctx.save()
        if not rtl:
            _, _, line_start = draw_utils.draw_text_left(ctx, pc, label_layout,
                                                         fascent, fheight,
                                                         baseline_x, baseline_y,
                                                         self.label)
            line_end, _, _ = draw_utils.draw_text_right(ctx, pc, column_layout,
                                                        fascent, fheight,
                                                        baseline_x, baseline_y,
                                                        location_str)
        else:
            _, _, line_start = draw_utils.draw_text_left(ctx, pc, column_layout,
                                                         fascent, fheight,
                                                         baseline_x, baseline_y,
                                                         location_str)
            line_end, _, _ = draw_utils.draw_text_right(ctx, pc, label_layout,
                                                        fascent, fheight,
                                                        (baseline_x
                                                         + location_width),
                                                        baseline_y,
                                                        self.label)

        # In case of empty label, we don't draw the dots
        if self.label != '':
            draw_utils.draw_dotted_line(ctx, max(fheight/12, 1),
                                        line_start + fheight/4, baseline_y,
                                        line_end - line_start - fheight/2)
        ctx.restore()

    def update_location_str(self, grid):
        """
        Update the location_str field from the given Grid object.

        Args:
           grid (ocitysmap2.Grid): the Grid object from which we
           compute the location strings

        Returns:
           Nothing, but the location_str field will have been altered
        """
        if self.endpoint1 is not None:
            ep1_label = grid.get_location_str( * self.endpoint1.get_latlong())
        else:
            ep1_label = None
        if self.endpoint2 is not None:
            ep2_label = grid.get_location_str( * self.endpoint2.get_latlong())
        else:
            ep2_label = None
        if ep1_label is None:
            ep1_label = ep2_label
        if ep2_label is None:
            ep2_label = ep1_label

        if ep1_label == ep2_label:
            if ep1_label is None:
                self.location_str = "???"
            self.location_str = ep1_label
        elif grid.rtl:
            self.location_str = "%s-%s" % (max(ep1_label, ep2_label),
                                           min(ep1_label, ep2_label))
        else:
            self.location_str = "%s-%s" % (min(ep1_label, ep2_label),
                                           max(ep1_label, ep2_label))

        if self.page_number is not None:
            if grid.rtl:
                self.location_str = "%s, %d" % (self.location_str,
                                                self.page_number)
            else:
                self.location_str = "%d, %s" % (self.page_number,
                                                self.location_str)

if __name__ == "__main__":
    import cairo
    import pangocairo

    surface = cairo.PDFSurface('/tmp/idx_commons.pdf', 1000, 1000)

    ctx = cairo.Context(surface)
    pc = pangocairo.CairoContext(ctx)

    font_desc = pango.FontDescription('DejaVu')
    font_desc.set_size(12 * pango.SCALE)

    layout = pc.create_layout()
    layout.set_font_description(font_desc)
    layout.set_width(200 * pango.SCALE)

    font = layout.get_context().load_font(font_desc)
    font_metric = font.get_metrics()

    fascent = font_metric.get_ascent() / pango.SCALE
    fheight = ((font_metric.get_ascent() + font_metric.get_descent())
               / pango.SCALE)

    first_item  = IndexItem('First Item', None, None)
    second_item = IndexItem('Second Item', None, None)
    category    = IndexCategory('Hello world !', [first_item, second_item])

    category.draw(False, ctx, pc, layout, fascent, fheight,
                  72, 80)
    first_item.draw(False, ctx, pc, layout, fascent, fheight,
                    72, 100)
    second_item.draw(False, ctx, pc, layout, fascent, fheight,
                     72, 120)

    surface.finish()
    print "Generated /tmp/idx_commons.pdf"

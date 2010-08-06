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
import math
import pango
import pangocairo
import random # TODO: remove
import string

import coords
import grid

class IndexDoesNotFitError(Exception):
    pass

def _draw_text_left(ctx, pc, layout, fascent, fheight,
                    baseline_x, baseline_y, text):
    """Draws the given text left aligned into the provided Cairo context
    through the Pango layout.

    Args:
        pc (pangocairo.CairoContext): ...
    """

    layout.set_alignment(pango.ALIGN_LEFT)
    layout.set_text(text)
    width, height = [x/pango.SCALE for x in layout.get_size()]

    ctx.move_to(baseline_x, baseline_y - fascent)
    pc.show_layout(layout)
    return baseline_x + width, baseline_y

def _draw_text_right(ctx, pc, layout, fascent, fheight,
                     baseline_x, baseline_y, text):
    """Draws the given text right aligned into the provided Cairo context
    through the Pango layout.

    Args:
        pc (pangocairo.CairoContext): ...
    """

    layout.set_alignment(pango.ALIGN_RIGHT)
    layout.set_text(text)
    width, height = [x/pango.SCALE for x in layout.get_size()]

    ctx.move_to(baseline_x, baseline_y - fascent)
    pc.show_layout(layout)
    return baseline_x + layout.get_width() / pango.SCALE - width, baseline_y

def _draw_dotted_line(ctx, line_width, baseline_x, baseline_y, length):
    ctx.set_line_width(line_width)
    ctx.set_dash([line_width, line_width*2])
    ctx.move_to(baseline_x, baseline_y)
    ctx.rel_line_to(length, 0)
    ctx.stroke()

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
    """
    The StreetIndex class encapsulate all the logic related to the querying and
    rendering of the street index.
    """

    def __init__(self, osmid, bounding_box, i18n, grid):
        self._osmid = osmid
        self._bbox = bounding_box
        self._i18n = i18n
        self._grid = grid

        self._data = self._get_streets() + self._get_amenities()

        self._label_fd = pango.FontDescription('DejaVu')
        self._header_fd = pango.FontDescription('Georgia Bold')

    def render(self, surface, x, y, w, h, freedom_direction, alignment):
        """Render the street and amenities index at the given (x,y) coordinates
        into the provided Cairo surface. The index must not be larger than the
        provided width and height (in pixels).

        Args:
            surface (cairo.Surface): the cairo surface to render into.
            x (int): horizontal origin position, in pixels.
            y (int): vertical origin position, in pixels.
            w (int): maximum usable width for the index, in dots (Cairo unit).
            h (int): maximum usable height for the index, in dots (Cairo unit).
            freedom_direction (string): freedom direction, can be 'width' or
                'height'. See _compute_columns_split for more details.
            alignment (string): 'top' or 'bottom' for a freedom_direction
                of 'height', 'left' or 'right' for 'width'. Tells which side to
                stick the index to.

        Returns the new actual graphical bounding box (new_x, new_y, new_w,
        new_h) used by the index.
        """

        if ((freedom_direction == 'height' and
             alignment not in ('top', 'bottom')) or
            (freedom_direction == 'width' and
             alignment not in ('left', 'right'))):
            raise ValueError, 'Incompatible freedom direction and alignment!'


        ctx = cairo.Context(surface)
        ctx.move_to(x, y)

        # Create a PangoCairo context for drawing to Cairo
        pc = pangocairo.CairoContext(ctx)

        n_cols, min_dimension = self._compute_columns_split(pc,
                w, h, 12, 16, freedom_direction)

        self._label_fd.set_size(12 * pango.SCALE)
        self._header_fd.set_size(16 * pango.SCALE)

        label_layout, label_fascent, label_fheight, label_em = \
                self._create_layout_with_font(pc, self._label_fd)
        header_layout, header_fascent, header_fheight, header_em = \
                self._create_layout_with_font(pc, self._header_fd)

        if freedom_direction == 'height':
            index_width = w
            index_height = min_dimension
        elif freedom_direction == 'width':
            index_width = min_dimension
            index_height = h

        cairo_colspace = label_em
        column_width = int(math.floor((index_width + cairo_colspace) / n_cols))

        label_layout.set_width((column_width - label_em) * pango.SCALE)
        header_layout.set_width((column_width - label_em) * pango.SCALE)

        print "columns#", n_cols
        print "min_dim:", min_dimension
        print "col width:", column_width
        print "index: (%d x %d)" % (index_width, index_height)
        print

        if alignment == 'top':
            base_offset_x = 0
            base_offset_y = 0
        elif alignment == 'bottom':
            base_offset_x = 0
            base_offset_y = h - index_height
        elif alignment == 'left':
            base_offset_x = 0
            base_offset_y = 0
        elif alignment == 'right':
            base_offset_x = w - index_width
            base_offset_y = 0

        if not self._i18n.isrtl():
            delta_x = column_width
            offset_x = 0
        else:
            delta_x = - column_width
            offset_x = w + delta_x

        offset_y = 0
        for category in self._data:
            if offset_y + header_fheight + label_fheight > index_height:
                offset_y = 0
                offset_x += delta_x

            category.draw(self._i18n.isrtl(), ctx, pc, header_layout,
                    header_fascent, header_fheight,
                    x + base_offset_x + offset_x,
                    y + base_offset_y + offset_y + header_fascent)

            offset_y += header_fheight

            for street in category.items:
                if offset_y + label_fheight > index_height:
                    offset_y = 0
                    offset_x += delta_x

                street.draw(self._i18n.isrtl(), ctx, pc, label_layout,
                        label_fascent, label_fheight,
                        x + base_offset_x + offset_x,
                        y + base_offset_y + offset_y + label_fascent)

                offset_y += label_fheight


        ctx.save()
        ctx.rectangle(x, y, w, h)
        ctx.stroke()
        ctx.restore()

        ctx.save()
        ctx.set_source_rgba(1.0, 0.0, 0.0, 0.3)
        ctx.rectangle(x + base_offset_x, y + base_offset_y,
                      index_width, index_height)
        ctx.fill()
        ctx.restore()


#        return new_x, new_y, new_w, new_h

    def as_csv(self, fobj):
        """Saves the street index as CSV to the provided file object."""
        # TODO: write to CSV
        raise NotImplementedError

    def _get_streets(self):
        streets = []
        for i in ['A', 'B', 'C', 'D', 'E', 'Schools', 'Public buildings']:
            streets.append(IndexCategory(i,
                [IndexItem(l,s) for l,s in
                    [(''.join(random.choice(string.letters) for i in xrange(random.randint(1, 10))), 'A1')]*4]))
        return streets

    def _get_amenities(self):
        return []

    def _create_layout_with_font(self, pc, font_desc):
        layout = pc.create_layout()
        layout.set_font_description(font_desc)
        font = layout.get_context().load_font(font_desc)
        font_metric = font.get_metrics()

        fascent = font_metric.get_ascent() / pango.SCALE
        fheight = ((font_metric.get_ascent() + font_metric.get_descent())
                   / pango.SCALE)
        em = font_metric.get_approximate_char_width() / pango.SCALE

        return layout, fascent, fheight, em

    def _compute_lines_occupation(self, pc, font_desc, n_em_padding,
                                  text_lines):
        """Compute the visual dimension parameters of the initial long column
        for the given text lines with the given font.

        Args:
            pc (pangocairo.CairoContext): the PangoCairo context.
            font_desc (pango.FontDescription): Pango font description,
                representing the used font at a given size.
            n_em_padding (int): number of extra em space to account for.
            text_lines (list): the list of text labels.

        Returns a dictionnary with the following key,value pairs:
            column_width: the computed column width (pixel size of the longest
                label).
            column_height: the total height of the column.
            fascent: scaled font ascent.
            fheight: scaled font height.
        """

        layout, fascent, fheight, em = self._create_layout_with_font(pc, font_desc)
        width = max(map(lambda x: self._label_width(layout, x), text_lines))
        # Save some extra space horizontally
        width += n_em_padding * em

        height = fheight * len(text_lines)

        return {'column_width': width, 'column_height': height,
                'fascent': fascent, 'fheight': fheight}

    def _label_width(self, layout, label):
        layout.set_text(label)
        return layout.get_size()[0] / pango.SCALE

    def _compute_column_occupation(self, pc, label_font_size,
                                   header_font_size):
        """Returns the size of the tall column with all headers, labels and
        squares for the given font sizes.

        Args:
            pc (pangocairo.CairoContext): the PangoCairo context.
            label_font_size (int): font size for street labels and squares.
            header_font_size (int): font size for headers.
        """

        self._label_fd.set_size(label_font_size * pango.SCALE)
        self._header_fd.set_size(header_font_size * pango.SCALE)

        label_block = self._compute_lines_occupation(pc, self._label_fd, 3,
                reduce(lambda x,y: x+y.get_all_item_labels(), self._data, []))
        squares_block = self._compute_lines_occupation(pc, self._label_fd, 3,
                reduce(lambda x,y: x+y.get_all_item_squares(), self._data, []))
        headers_block = self._compute_lines_occupation(pc, self._header_fd, 2,
                [x.name for x in self._data])

        column_width = max(label_block['column_width'] +
                           squares_block['column_width'],
                           headers_block['column_width'])
        column_height = max(label_block['column_height'],
                            squares_block['column_height']) + \
                        headers_block['column_height']

        return column_width, column_height, \
                max(label_block['fheight'], headers_block['fheight'])

    def _compute_columns_split(self, pc, zone_width_dots, zone_height_dots,
                               label_font_size, header_font_size,
                               freedom_direction):
        """Computes the columns split for this index. From the one tall column
        width and height it finds the number of columns fitting on the zone
        dedicated to the index on the Cairo surface.

        If the columns split does not fit on the index zone,
        IndexDoesNotFitError is raised.

        Args:
            pc (pangocairo.CairoContext): the PangoCairo context.
            zone_width_dots (float): maximum width of the Cairo zone dedicated
                to the index.
            zone_height_dots (float): maximum height of the Cairo zone
                dedicated to the index.
            label_font_size (int): font size for street labels and squares.
            header_font_size (int): font size for headers.
            freedom_direction (string): the zone dimension that is flexible for
                rendering this index, can be 'width' or 'height'. If the
                streets don't fill the zone dedicated to the index, we need to
                try with a zone smaller in the freedom_direction.

        Returns the number of columns that will be in the index and the new
        value for the flexible dimension.
        """

        tall_width, tall_height, vertical_extra = \
                self._compute_column_occupation(pc, label_font_size,
                                                header_font_size)

        if freedom_direction == 'height':
            n_cols = math.floor(zone_width_dots / float(tall_width))
            min_required_height = (math.ceil(tall_height / n_cols) +
                                   vertical_extra)

            if (n_cols <= 0 or n_cols * tall_width > zone_width_dots or
                min_required_height > zone_height_dots):
                raise IndexDoesNotFitError

            return int(n_cols), min_required_height
        elif freedom_direction == 'width':
            n_cols = math.ceil(float(tall_height) / zone_height_dots)
            extra = n_cols * vertical_extra
            min_required_width = n_cols * tall_width

            if (min_required_width > zone_width_dots or
                tall_height + extra > n_cols * zone_height_dots):
                raise IndexDoesNotFitError

            return int(n_cols), min_required_width

        raise ValueError, 'Invalid freedom direction!'

if __name__ == '__main__':
    bbox = coords.BoundingBox(48.8162, 2.3417, 48.8063, 2.3699)
    grid = grid.Grid(bbox)

    surface = cairo.PDFSurface('/tmp/index.pdf', 1000, 1000)

    class i18nMock:
        def isrtl(self):
            return False

    index = StreetIndex(None, bbox, i18nMock(), grid)
    index.render(surface, 50, 50, 800, 520, 'height', 'top')
    surface.show_page()
    index.render(surface, 50, 50, 800, 520, 'height', 'bottom')
    surface.show_page()
    index.render(surface, 50, 50, 800, 520, 'width', 'left')
    surface.show_page()
    index.render(surface, 50, 50, 800, 520, 'width', 'right')

    surface.finish()


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

import commons

l = logging.getLogger('ocitysmap')

class StreetIndexRenderer:
    """
    The StreetIndex class encapsulate all the logic related to the querying and
    rendering of the street index.
    """

    def __init__(self, i18n, index_categories,
                 header_font_spec = 'Georgia Bold',
                 label_font_spec = 'DejaVu'):
        self._i18n = i18n
        self._index_categories = index_categories

        self._header_fd = pango.FontDescription(header_font_spec)
        self._label_fd = pango.FontDescription(label_font_spec)

    def precompute_occupation_area(self, surface, x, y, w, h,
                                   freedom_direction, alignment):
        """Prepare to render the street and amenities index at the
        given (x,y) coordinates into the provided Cairo surface. The
        index must not be larger than the provided width and height
        (in pixels). Nothing will be drawn on surface.

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

        Returns the recommended actual graphical bounding box (new_x,
        new_y, new_w, new_h, n_cols) where the index should be
        rendered. Raise IndexDoesNotFitError when the provided area's
        surface is not enough to hold the index.
        """
        if ((freedom_direction == 'height' and
             alignment not in ('top', 'bottom')) or
            (freedom_direction == 'width' and
             alignment not in ('left', 'right'))):
            raise ValueError, 'Incompatible freedom direction and alignment!'

        if not self._index_categories:
            raise commons.IndexEmptyError

        ctx = cairo.Context(surface)

        # Create a PangoCairo context for drawing to Cairo
        pc = pangocairo.CairoContext(ctx)

        n_cols, min_dimension = self._compute_columns_split(pc,
                                                            w, h, 12, 16,
                                                            freedom_direction)

        self._label_fd.set_size(12 * pango.SCALE)
        self._header_fd.set_size(16 * pango.SCALE)

        label_layout, label_fascent, label_fheight, label_em = \
                self._create_layout_with_font(pc, self._label_fd)
        header_layout, header_fascent, header_fheight, header_em = \
                self._create_layout_with_font(pc, self._header_fd)

        if freedom_direction == 'height':
            index_width  = w
            index_height = min_dimension
        elif freedom_direction == 'width':
            index_width  = min_dimension
            index_height = h

        base_offset_x = 0
        base_offset_y = 0
        if alignment == 'bottom':
            base_offset_y = h - index_height
        if alignment == 'right':
            base_offset_x = w - index_width

        return (x+base_offset_x, y+base_offset_y,
                index_width, index_height, n_cols)


    def render(self, surface, x, y, w, h, n_cols):
        """Render the street and amenities index at the given (x,y) coordinates
        into the provided Cairo surface. The index must not be larger than the
        provided surface (use precompute_occupation_area() to adjust it).

        Args:
            surface (cairo.Surface): the cairo surface to render into.
            x (int): horizontal origin position, in pixels.
            y (int): vertical origin position, in pixels.
            w (int): maximum usable width for the index, in dots (Cairo unit).
            h (int): maximum usable height for the index, in dots (Cairo unit).
        """

        if not self._index_categories:
            raise commons.IndexEmptyError

        ctx = cairo.Context(surface)
        ctx.move_to(x, y)

        # Create a PangoCairo context for drawing to Cairo
        pc = pangocairo.CairoContext(ctx)

        self._label_fd.set_size(12 * pango.SCALE)
        self._header_fd.set_size(16 * pango.SCALE)

        label_layout, label_fascent, label_fheight, label_em = \
                self._create_layout_with_font(pc, self._label_fd)
        header_layout, header_fascent, header_fheight, header_em = \
                self._create_layout_with_font(pc, self._header_fd)

        cairo_colspace = label_em
        column_width = int(math.floor((w + cairo_colspace) / n_cols))

        label_layout.set_width((column_width - label_em) * pango.SCALE)
        header_layout.set_width((column_width - label_em) * pango.SCALE)

        if not self._i18n.isrtl():
            delta_x  = column_width
            offset_x = 0
        else:
            delta_x  = - column_width
            offset_x = w - column_width + cairo_colspace

        offset_y = 0
        for category in self._index_categories:
            if offset_y + header_fheight + label_fheight > h:
                offset_y = 0
                offset_x += delta_x

            category.draw(self._i18n.isrtl(), ctx, pc, header_layout,
                    header_fascent, header_fheight,
                    x + offset_x,
                    y + offset_y + header_fascent)

            offset_y += header_fheight

            for street in category.items:
                if offset_y + label_fheight > h:
                    offset_y = 0
                    offset_x += delta_x

                street.draw(self._i18n.isrtl(), ctx, pc, label_layout,
                        label_fascent, label_fheight,
                        x + offset_x,
                        y + offset_y + label_fascent)

                offset_y += label_fheight


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

        # Account for maximum square width (at worst "Z99-Z99")
        label_block = self._compute_lines_occupation(pc, self._label_fd, 1+7,
                reduce(lambda x,y: x+y.get_all_item_labels(),
                       self._index_categories, []))

        # Reserve a small margin around the category headers
        headers_block = self._compute_lines_occupation(pc, self._header_fd, 2,
                [x.name for x in self._index_categories])

        column_width = max(label_block['column_width'],
                           headers_block['column_width'])
        column_height = label_block['column_height'] + \
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
        commons.IndexDoesNotFitError is raised.

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

        if zone_width_dots < tall_width:
            raise commons.IndexDoesNotFitError

        if freedom_direction == 'height':
            n_cols = math.floor(zone_width_dots / float(tall_width))
            min_required_height = (math.ceil(tall_height / n_cols) +
                                   vertical_extra)

            if (n_cols <= 0 or n_cols * tall_width > zone_width_dots or
                min_required_height > zone_height_dots):
                raise commons.IndexDoesNotFitError

            return int(n_cols), min_required_height
        elif freedom_direction == 'width':
            n_cols = math.ceil(float(tall_height) / zone_height_dots)
            extra = n_cols * vertical_extra
            min_required_width = n_cols * tall_width

            if (min_required_width > zone_width_dots or
                tall_height + extra > n_cols * zone_height_dots):
                raise commons.IndexDoesNotFitError

            return int(n_cols), min_required_width

        raise ValueError, 'Invalid freedom direction!'


if __name__ == '__main__':
    import random
    import string
    from ocitysmap2 import coords
    from ocitysmap2.index import commons

    import render

    width = 72*21./2.54
    height = .75 * 72*29.7/2.54

    random.seed(42)

    bbox = coords.BoundingBox(48.8162, 2.3417, 48.8063, 2.3699)

    surface = cairo.PDFSurface('/tmp/myindex_render.pdf', width, height)

    def rnd_str(max_len, letters = string.letters):
        return ''.join(random.choice(letters)
                       for i in xrange(random.randint(1, max_len)))

    class i18nMock:
        def __init__(self, rtl):
            self.rtl = rtl
        def isrtl(self):
            return self.rtl

    streets = []
    for i in ['A', 'B', 'C', 'D', 'E', 'Schools', 'Public buildings']:
        items = []
        for label, location_str in [(rnd_str(10).capitalize(),
                                     '%s%d-%s%d' \
                                         % (rnd_str(2,
                                                    string.ascii_uppercase),
                                            random.randint(1,19),
                                            rnd_str(2,
                                                    string.ascii_uppercase),
                                            random.randint(1,19),
                                            ))]*4:
            item              = commons.IndexItem(label, None, None)
            item.location_str = location_str
            items.append(item)
        streets.append(commons.IndexCategory(i, items))

    index = render.StreetIndexRenderer(i18nMock(False), streets)

    def _render(freedom_dimension, alignment):
        x,y,w,h = 50, 50, width-100, height-100

        # Draw constraining rectangle
        ctx = cairo.Context(surface)
        ctx.set_source_rgb(.2,0,0)
        ctx.rectangle(x,y,w,h)
        ctx.stroke()

        # Precompute index area
        x,y,w,h,ncols = index.precompute_occupation_area(surface, x,y,w,h,
                                                         freedom_dimension,
                                                         alignment)

        # Draw a green background for the precomputed area
        ctx.set_source_rgba(0,1,0,.5)
        ctx.rectangle(x,y,w,h)
        ctx.fill()

        # Render the index
        index.render(surface,x,y,w,h,ncols)


    _render('height', 'top')
    surface.show_page()
    _render('height', 'bottom')
    surface.show_page()
    _render('width', 'left')
    surface.show_page()
    _render('width', 'right')
    surface.show_page()

    index = render.StreetIndexRenderer(i18nMock(True), streets)
    _render('height', 'top')
    surface.show_page()
    _render('height', 'bottom')
    surface.show_page()
    _render('width', 'left')
    surface.show_page()
    _render('width', 'right')

    surface.finish()
    print "Generated /tmp/myindex_render.pdf"

# -*- coding: utf-8 -*-

# ocitysmap, city map and street index generator from OpenStreetMap data
# Copyright (C) 2012  David Decotigny
# Copyright (C) 2012  Frédéric Lehobey
# Copyright (C) 2012  Pierre Mauduit
# Copyright (C) 2012  David Mentré
# Copyright (C) 2012  Maxime Petazzoni
# Copyright (C) 2012  Thomas Petazzoni
# Copyright (C) 2012  Gaël Utard
# Copyright (C) 2012  Étienne Loks

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
import pango
import pangocairo

import ocitysmap.layoutlib.commons as commons

def draw_text(ctx, pc, layout, fascent, fheight,
              baseline_x, baseline_y, text, pango_alignment):
    """Draws the given text into the provided Cairo
    context through the Pango layout (get_width() expected to be
    correct in order to position the text correctly) with the
    specified pango.ALIGN_x alignment.

    Args:
        ctx (cairo.Context): cairo context to use
        pc (pangocairo.CairoContext): pango context
        layout (pango.Layout): pango layout to draw into (get_with() important)
        fascent, fheight (int): current font ascent/height metrics
        baseline_x/baseline_y (int): coordinate of the left baseline cairo point
        pango_alignment (enum): pango.ALIGN_ constant value

    Results:
        A 3-uple text_width, text_height (cairo units)
    """
    layout.set_auto_dir(False) # Make sure ALIGN_RIGHT is independent on RTL...
    layout.set_alignment(pango_alignment)
    layout.set_text(text)
    width, height = [x/pango.SCALE for x in layout.get_size()]

    ctx.move_to(baseline_x, baseline_y - fascent)
    pc.show_layout(layout)
    return width, height

def draw_text_left(ctx, pc, layout, fascent, fheight,
                    baseline_x, baseline_y, text):
    """Draws the given text left aligned into the provided Cairo
    context through the Pango layout (get_width() expected to be
    correct in order to position the text correctly).

    Args:
        ctx (cairo.Context): cairo context to use
        pc (pangocairo.CairoContext): pango context
        layout (pango.Layout): pango layout to draw into (get_with() important)
        fascent, fheight (int): current font ascent/height metrics
        baseline_x/baseline_y (int): coordinate of the left baseline cairo point
        pango_alignment (enum): pango.ALIGN_ constant value

    Results:
        A 3-uple left_x, baseline_y, right_x of the text rendered (cairo units)
    """
    w,h = draw_text(ctx, pc, layout, fascent, fheight,
                    baseline_x, baseline_y, text, pango.ALIGN_LEFT)
    return baseline_x, baseline_y, baseline_x + w

def draw_text_center(ctx, pc, layout, fascent, fheight,
                     baseline_x, baseline_y, text):
    """Draws the given text centered inside the provided Cairo
    context through the Pango layout (get_width() expected to be
    correct in order to position the text correctly).

    Args:
        ctx (cairo.Context): cairo context to use
        pc (pangocairo.CairoContext): pango context
        layout (pango.Layout): pango layout to draw into (get_with() important)
        fascent, fheight (int): current font ascent/height metrics
        baseline_x/baseline_y (int): coordinate of the left baseline cairo point
        pango_alignment (enum): pango.ALIGN_ constant value

    Results:
        A 3-uple left_x, baseline_y, right_x of the text rendered (cairo units)
    """
    txt_width, txt_height = draw_text(ctx, pc, layout, fascent, fheight,
                                      baseline_x, baseline_y, text,
                                      pango.ALIGN_CENTER)
    layout_width = layout.get_width() / pango.SCALE
    return ( baseline_x + (layout_width - txt_width) / 2.,
             baseline_y,
             baseline_x + (layout_width + txt_width) / 2. )

def draw_text_right(ctx, pc, layout, fascent, fheight,
                    baseline_x, baseline_y, text):
    """Draws the given text right aligned into the provided Cairo
    context through the Pango layout (get_width() expected to be
    correct in order to position the text correctly).

    Args:
        ctx (cairo.Context): cairo context to use
        pc (pangocairo.CairoContext): pango context
        layout (pango.Layout): pango layout to draw into (get_with() important)
        fascent, fheight (int): current font ascent/height metrics
        baseline_x/baseline_y (int): coordinate of the left baseline cairo point
        pango_alignment (enum): pango.ALIGN_ constant value

    Results:
        A 3-uple left_x, baseline_y, right_x of the text rendered (cairo units)
    """
    txt_width, txt_height = draw_text(ctx, pc, layout, fascent, fheight,
                                      baseline_x, baseline_y,
                                      text, pango.ALIGN_RIGHT)
    layout_width = layout.get_width() / pango.SCALE
    return (baseline_x + layout_width - txt_width,
            baseline_y,
            baseline_x + layout_width)

def draw_simpletext_center(ctx, text, x, y):
    """
    Draw the given text centered at x,y.

    Args:
       ctx (cairo.Context): The cairo context to use to draw.
       text (str): the text to draw.
       x,y (numbers): Location of the center (cairo units).
    """
    ctx.save()
    xb, yb, tw, th, xa, ya = ctx.text_extents(text)
    ctx.move_to(x - tw/2.0 - xb, y - yb/2.0)
    ctx.show_text(text)
    ctx.stroke()
    ctx.restore()

def draw_dotted_line(ctx, line_width, baseline_x, baseline_y, length):
    ctx.set_line_width(line_width)
    ctx.set_dash([line_width, line_width*2])
    ctx.move_to(baseline_x, baseline_y)
    ctx.rel_line_to(length, 0)
    ctx.stroke()

def adjust_font_size(layout, fd, constraint_x, constraint_y):
    """
    Grow the given font description (20% by 20%) until it fits in
    designated area and then draw it.

    Args:
       layout (pango.Layout): The text block parameters.
       fd (pango.FontDescriptor): The font object.
       constraint_x/constraint_y (numbers): The area we want to
           write into (cairo units).
    """
    while (layout.get_size()[0] / pango.SCALE < constraint_x and
           layout.get_size()[1] / pango.SCALE < constraint_y):
        fd.set_size(int(fd.get_size()*1.2))
        layout.set_font_description(fd)
    fd.set_size(int(fd.get_size()/1.2))
    layout.set_font_description(fd)

def draw_text_adjusted(ctx, text, x, y, width, height, max_char_number=None,
                       text_color=(0, 0, 0, 1), align=pango.ALIGN_CENTER,
                       width_adjust=0.7, height_adjust=0.8):
    """
    Draw a text adjusted to a maximum character number

    Args:
       ctx (cairo.Context): The cairo context to use to draw.
       text (str): the text to draw.
       x/y (numbers): The position on the canvas.
       width/height (numbers): The area we want to
           write into (cairo units).
       max_char_number (number): If set a maximum character number.
    """
    pc = pangocairo.CairoContext(ctx)
    layout = pc.create_layout()
    layout.set_width(int(width_adjust * width * pango.SCALE))
    layout.set_alignment(align)
    fd = pango.FontDescription("Georgia Bold")
    fd.set_size(pango.SCALE)
    layout.set_font_description(fd)

    if max_char_number:
        # adjust size with the max character number
        layout.set_text('0'*max_char_number)
        adjust_font_size(layout, fd, width_adjust*width, height_adjust*height)

    # set the real text
    layout.set_text(text)
    if not max_char_number:
        adjust_font_size(layout, fd, width_adjust*width, height_adjust*height)

    # draw
    text_x, text_y, text_w, text_h = layout.get_extents()[1]
    ctx.save()
    ctx.set_source_rgba(*text_color)
    if align == pango.ALIGN_CENTER:
        x = x - (text_w/2.0)/pango.SCALE - int(float(text_x)/pango.SCALE)
        y = y - (text_h/2.0)/pango.SCALE - int(float(text_y)/pango.SCALE)
    else:
        y = y - (text_h/2.0)/pango.SCALE - text_y/pango.SCALE
    ctx.translate(x, y)

    if align == pango.ALIGN_LEFT:
        # Hack to workaround what appears to be a Cairo bug: without
        # drawing a rectangle here, the translation above is not taken
        # into account for rendering the text.
        ctx.rectangle(0, 0, 0, 0)
    pc.show_layout(layout)
    ctx.restore()

def render_page_number(ctx, page_number,
                       usable_area_width_pt, usable_area_height_pt, margin_pt,
                       transparent_background = True):
    """
    Render page number
    """
    ctx.save()
    x_offset = 0
    if page_number % 2:
        x_offset += commons.convert_pt_to_dots(usable_area_width_pt)\
                  - commons.convert_pt_to_dots(margin_pt)
    y_offset = commons.convert_pt_to_dots(usable_area_height_pt)\
             - commons.convert_pt_to_dots(margin_pt)
    ctx.translate(x_offset, y_offset)

    if transparent_background:
        ctx.set_source_rgba(1, 1, 1, 0.6)
    else:
        ctx.set_source_rgba(0.8, 0.8, 0.8, 0.6)
    ctx.rectangle(0, 0, commons.convert_pt_to_dots(margin_pt),
                  commons.convert_pt_to_dots(margin_pt))
    ctx.fill()

    ctx.set_source_rgba(0, 0, 0, 1)
    x_offset = commons.convert_pt_to_dots(margin_pt)/2
    y_offset = commons.convert_pt_to_dots(margin_pt)/2
    ctx.translate(x_offset, y_offset)
    draw_simpletext_center(ctx, unicode(page_number), 0, 0)
    ctx.restore()


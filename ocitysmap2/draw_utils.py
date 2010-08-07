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
import pango

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

def draw_dotted_line(ctx, line_width, baseline_x, baseline_y, length):
    ctx.set_line_width(line_width)
    ctx.set_dash([line_width, line_width*2])
    ctx.move_to(baseline_x, baseline_y)
    ctx.rel_line_to(length, 0)
    ctx.stroke()

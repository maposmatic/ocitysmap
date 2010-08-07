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

def draw_text_left(ctx, pc, layout, fascent, fheight,
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

def draw_text_right(ctx, pc, layout, fascent, fheight,
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

def draw_dotted_line(ctx, line_width, baseline_x, baseline_y, length):
    ctx.set_line_width(line_width)
    ctx.set_dash([line_width, line_width*2])
    ctx.move_to(baseline_x, baseline_y)
    ctx.rel_line_to(length, 0)
    ctx.stroke()

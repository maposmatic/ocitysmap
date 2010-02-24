# -*- coding: utf-8; mode: Python -*-

# ocitysmap, city map and street index generator from OpenStreetMap data
# Copyright (C) 2009  David Decotigny
# Copyright (C) 2009  Frédéric Lehobey
# Copyright (C) 2009  David Mentré
# Copyright (C) 2009  Maxime Petazzoni
# Copyright (C) 2009  Thomas Petazzoni
# Copyright (C) 2009  Gaël Utard

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


import cairo, logging, pango, pangocairo
import datetime

l = logging.getLogger('ocitysmap')


def enclose_in_frame(renderer, insurf_w, insurf_h,
                     title,
                     outsurf, outsurf_w, outsurf_h, out_margin):
    """
    Fill the given surface with the contents of another one and a
    frame around it
    @param renderer (function : cairo_context -> None) Function
    drawing inside the frame
    @param insurf_w/h (int) width/height of the inside rendering
    @param title (string) title to write on the frame
    @param outsurf (cairo surface) surface to draw the whole thing into
    @param outsurf_w/h (int) width/height of the resulting framed image
    @param out_margin (int) size of the margin around the inner image
    """

    ctx = cairo.Context(outsurf)

    ctx.save()

    # Reset background
    ctx.set_source_rgb (1, 1, 1)
    ctx.set_operator (cairo.OPERATOR_OVER)
    ctx.paint()

    # Default pen color
    ctx.set_source_rgb (0, 0, 0)

    # Draw the surface with a margin around it
    ctx.save()
    ctx.translate(out_margin, out_margin)
    indest_w = outsurf_w - 2.*out_margin
    indest_h = outsurf_h - 2.*out_margin
    ctx.scale(indest_w / insurf_w, indest_h / insurf_h)
    renderer(ctx)
    ctx.restore()

    # Draw the title
    ctx.save()

    pc = pangocairo.CairoContext(ctx)
    layout = pc.create_layout()
    fd = pango.FontDescription("DejaVu")

    # Do a first test with a font size of out_margin
    fd.set_size(out_margin * pango.SCALE)
    layout.set_font_description(fd)
    layout.set_text(title)
    width = layout.get_size()[0] / pango.SCALE
    height = layout.get_size()[1] / pango.SCALE

    # Compute the ratio to be applied on the font size to make the
    # text fit in the available space
    if height > out_margin:
        hratio = float(out_margin) / height
    else:
        hratio = 1.

    max_width = indest_w * .8
    if width > max_width:
        wratio = max_width / width
    else:
        wratio = 1.

    ratio = min(wratio, hratio)

    # Render the text at the appropriate size and location
    fd.set_size(int(out_margin * ratio * pango.SCALE))
    layout.set_font_description(fd)
    width = layout.get_size()[0] / pango.SCALE
    f = layout.get_context().load_font(fd)
    fm = f.get_metrics()
    ascent = fm.get_ascent() / pango.SCALE
    ctx.move_to(out_margin * 2., out_margin * (.5 + .35 * ratio) - ascent)
    pc.show_layout(layout)

    ctx.restore()

    # Draw the rounded rectangle
    ctx.save()
    ctx.set_line_width(max(out_margin/9., 2.))
    ctx.move_to (out_margin * 2 + width + out_margin/2., out_margin / 2.)
    ctx.line_to (outsurf_w - out_margin, out_margin / 2.)
    ctx.rel_curve_to(0,0, out_margin/2., 0, out_margin/2., out_margin/2.)
    ctx.rel_line_to (0, outsurf_h - 2*out_margin)
    ctx.rel_curve_to(0,0, 0, out_margin/2., -out_margin/2., out_margin/2.)
    ctx.rel_line_to(-(outsurf_w - 2*out_margin), 0)
    ctx.rel_curve_to(0,0, -out_margin/2.,0, -out_margin/2., -out_margin/2.)
    ctx.rel_line_to(0, -(outsurf_h - 2*out_margin))
    ctx.rel_curve_to(0,0, 0,-out_margin/2., out_margin/2.,-out_margin/2.)
    ctx.line_to(out_margin*1.5, out_margin/2.)
    ctx.stroke()
    ctx.restore()

    ctx.restore()
    return outsurf


def add_logo(ctx, paperwidth, paperheight, logo_path,
             copyright_notice = u'© 2009 MapOSMatic/ocitysmap authors. '
             u'Map data © 2009 OpenStreetMap.org '
             u'and contributors (CC-BY-SA)'):

    # Open logo file
    png =  None
    if logo_path:
        try:
            f = open(logo_path, 'rb')
            png = cairo.ImageSurface.create_from_png(f)
            l.debug('Using copyright logo: %s' % logo_path)
            f.close()
        except Exception, ex:
            l.warning('Cannot open logo file: %s' % ex)
        except:
            l.warning('Cannot open logo file.')

    # Create a virtual buffer containing the png and the copyright notice
    ctx.push_group()
    ctx.move_to(0,0)
    xlat1, ylat1 = ctx.get_current_point()

    ctx.select_font_face("DejaVu", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(14)

    fontheight = ctx.font_extents()[2]

    # Draw the png in the buffer
    if png:
        ctx.set_source_surface(png)
        ctx.paint()
        ctx.rel_move_to(png.get_width(), fontheight)
    else:
        ctx.rel_move_to(0, font_size*1.5)

    # Write the notice in the buffer
    textwidth = ctx.text_extents(copyright_notice)[2]
    ctx.set_source_rgb (0, 0, 0)
    ctx.show_text(copyright_notice)

    ctx.move_to(png.get_width(), png.get_height() * 0.33 + fontheight)
    today = datetime.date.today()
    gendatetext = _("This map has been rendered on %s and may be incomplete or inaccurate.") % today.strftime("%d %b %Y")
    textwidth = max(textwidth, ctx.text_extents(gendatetext)[2])
    ctx.show_text(gendatetext)

    ctx.move_to(png.get_width(), png.get_height() * 0.66 + fontheight)
    contribute_text = _("You can contribute to improve this map. See http://wiki.openstreetmap.org")
    textwidth = max(textwidth, ctx.text_extents(contribute_text)[2])
    ctx.show_text(contribute_text)

    # Determine the size of the virtual buffer
    if png:
        vbufheight = png.get_height()
    else:
        vbufheight = font_size * 2.5

    vbufwidth = png.get_width() + max(ctx.text_extents(copyright_notice)[2],
                                      ctx.text_extents(gendatetext)[2])

    grp = ctx.pop_group()
    # Virtual buffer done.

    # Display the buffer inside the surface, taking its size into account
    ctx.translate(paperwidth - vbufwidth - 10,
                  paperheight - vbufheight - 10)
    ctx.set_source(grp)

    # Make it transparent
    ctx.paint_with_alpha(.5)


if __name__ == "__main__":
    inner_W, inner_H, margin = 1024, 768, 50

    inside_area = cairo.ImageSurface(cairo.FORMAT_RGB24, inner_W,  inner_H)
    ctx = cairo.Context(inside_area)

    # Fill the inside with something
    ctx.set_source_rgb (1, .1, .1)
    ctx.set_operator (cairo.OPERATOR_OVER)
    ctx.paint()

    # Add the logo and save the result as inside.png
    add_logo(ctx, inner_W, inner_H, "../Openstreetmap_logo.png")
    f = open("inside.png", 'wb')
    inside_area.write_to_png(f)
    f.close()

    # Add a frame and save the result as outside.png
    def my_render(x):
        x.set_source_surface(inside_area)
        x.paint()

    outside_area = cairo.ImageSurface(cairo.FORMAT_RGB24,
                                      inner_W+2*margin,
                                      inner_H+2*margin)
    enclose_in_frame(my_render, inner_W,  inner_H, "badidonc",
                     outside_area, inner_W+2*margin,
                     inner_H+2*margin, margin)

    f = open("outside.png", 'wb')
    outside_area.write_to_png(f)
    f.close()

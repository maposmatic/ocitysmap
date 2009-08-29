
import cairo

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
    ctx.move_to(out_margin * 2., out_margin * .85)
    xlat1, _ = ctx.get_current_point()
    ctx.select_font_face("DejaVu", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(out_margin)
    fascent, fdescent, fheight, fxadvance, fyadvance = ctx.font_extents()
    ctx.show_text(title)
    xlat2, _ = ctx.get_current_point()
    xlat = xlat2 - xlat1
    ctx.restore()

    # Draw the rounded rectangle
    ctx.save()
    ctx.set_line_width(max(out_margin/9., 2.))
    ctx.move_to (out_margin * 2 + xlat + out_margin/2., out_margin / 2.)
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


def add_logo(ctx, paperwidth, paperheight, logo_path):
    f = open(logo_path, 'r')
    png = cairo.ImageSurface.create_from_png(f)
    f.close()

    # Create a virtual buffer containing the png and the copyright notice
    ctx.push_group()
    ctx.move_to(0,0)
    xlat1, ylat1 = ctx.get_current_point()

    # Draw the png in the buffer
    ctx.set_source_surface(png)
    ctx.paint()

    # Write the notice in the buffer
    ctx.rel_move_to(png.get_width(), png.get_height()*.85)
    ctx.set_source_rgb (0, 0, 0)
    ctx.select_font_face("DejaVu", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(png.get_height() * .75)
    ctx.show_text('Copyright the MapOSMatic team. '
                  'Map data: copyright OpenStreetMap '
                  'and contributors (CC-BY-SA)')

    # Determine the size of the virtual buffer
    xlat2, ylat2 = ctx.get_current_point()
    grp = ctx.pop_group()
    # Virtual buffer done.

    # Display the buffer inside the surface, taking its size into account
    ctx.translate(paperwidth - (xlat2-xlat1) - 10,
                  paperheight - (ylat2-ylat1) - 10)
    ctx.set_source(grp)

    # Make it transparent
    ctx.paint_with_alpha(.5)


if __name__ == "__main__":
    inside_area = cairo.ImageSurface(cairo.FORMAT_RGB24, 800,  600)
    ctx = cairo.Context(inside_area)

    # Fill the inside with something
    ctx.set_source_rgb (1, .1, .1)
    ctx.set_operator (cairo.OPERATOR_OVER)
    ctx.paint()

    # Add the logo and save the result as inside.png
    add_logo(ctx, 800, 600, "../Openstreetmap_logo.png")
    f = open("inside.png", 'wb')
    inside_area.write_to_png(f)
    f.close()

    # Add a frame and save the result as outside.png
    def my_render(x):
        x.set_source_surface(inside_area)
        x.paint()

    outside_area = cairo.ImageSurface(cairo.FORMAT_RGB24, 900,  700)
    enclose_in_frame(my_render, 800,  600, "badidonc",
                     outside_area, 900, 700, 50)

    f = open("outside.png", 'wb')
    outside_area.write_to_png(f)
    f.close()

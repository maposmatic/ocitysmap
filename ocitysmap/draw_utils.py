
import cairo

def borderize(renderer, insurf_w, insurf_h,
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

    # ctx.set_source_rgb (.1, 1, .1)
    # ctx.set_operator (cairo.OPERATOR_OVER)
    # ctx.paint()

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
    ctx.set_line_width(out_margin/5.)
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

    return outsurf

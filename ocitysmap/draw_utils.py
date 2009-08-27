
import cairo

def borderize(insurf, insurf_w, insurf_h, renderer,
              title,
              outsurf, outsurf_w, outsurf_h, out_margin):

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
    ctx.translate(out_margin * 2., out_margin * .85)
    ctx.select_font_face("DejaVu", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(out_margin)
    fascent, fdescent, fheight, fxadvance, fyadvance = ctx.font_extents()
    ctx.show_text(title)
    xlat, _ = ctx.get_current_point()
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

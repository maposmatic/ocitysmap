#! /usr/bin/env python


import os, mapnik, logging, locale
from osgeo import ogr
from coords import BoundingBox
from draw_utils import enclose_in_frame

try:
    import cairo
except ImportError:
    cairo = None

l = logging.getLogger('ocitysmap')

class GLOBALS:
    MAIN_PROJECTION = "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +no_defs +over"


class GridFile:
    """
    Class to generate a shape_file containing vertical/horizontal lines.
    Call flush() to commit the final rendering to disk. Afterwards,
    any attempt to add grid lines will fail (exception).
    The coordinates are not related to any projection
    """
    def __init__(self, envelope, out_filename, layer_name = "Grid"):
        """
        @param envelope (BoundingBox) envelope of the grid lines
        @param out_filename (string) path to the output shape file we generate
        @param layer_name (string) layer name in the shape file
        """
        self._envelope = envelope
        self._filepath = out_filename
        driver = ogr.GetDriverByName('ESRI Shapefile')
        if os.path.exists(out_filename):
            # Delete the detination file first
            driver.DeleteDataSource(out_filename)
        self._ds = driver.CreateDataSource(out_filename)
        self._layer = self._ds.CreateLayer(layer_name,
                                           geom_type=ogr.wkbLineString)

    def add_horiz_line(self, y):
        """
        Add a new latitude line at the given latitude
        """
        line = ogr.Geometry(type = ogr.wkbLineString)
        line.AddPoint_2D(self._envelope.get_top_left()[1], y)
        line.AddPoint_2D(self._envelope.get_bottom_right()[1], y)
        f = ogr.Feature(feature_def = self._layer.GetLayerDefn())
        f.SetGeometryDirectly(line)
        self._layer.CreateFeature(f)
        f.Destroy()

    def add_vert_line(self, x):
        """
        Add a new longitude line at the given longitude
        """
        line = ogr.Geometry(type = ogr.wkbLineString)
        line.AddPoint_2D(x, self._envelope.get_top_left()[0])
        line.AddPoint_2D(x, self._envelope.get_bottom_right()[0])
        f = ogr.Feature(feature_def = self._layer.GetLayerDefn())
        f.SetGeometryDirectly(line)
        self._layer.CreateFeature(f)
        f.Destroy()

    def flush(self):
        """
        Commit the file to disk and prevent any further addition of
        new longitude/latitude lines
        """
        self._ds.Destroy()
        self._ds = None

    def get_filepath(self):
        """
        Return the path to the destination shape file
        """
        return self._filepath

    def __str__(self):
        return "GridFile(%s)" % self._filepath


def create_shapefile_polygon_from_wkt(out_fname, wkt):
    driver = ogr.GetDriverByName('ESRI Shapefile')
    if os.path.exists(out_fname):
        driver.DeleteDataSource(out_fname)
    ds = driver.CreateDataSource(out_fname)
    layer = ds.CreateLayer('poly', geom_type=ogr.wkbPolygon)

    prev_locale = locale.getlocale(locale.LC_ALL)
    locale.setlocale(locale.LC_ALL, "C")
    try:
        poly = ogr.CreateGeometryFromWkt(wkt)
    finally:
        locale.setlocale(locale.LC_ALL, prev_locale)

    f = ogr.Feature(feature_def = layer.GetLayerDefn())
    f.SetGeometryDirectly(poly)
    layer.CreateFeature(f)
    f.Destroy()
    ds.Destroy()


def _project_envelope(proj, envelope):
    """
    Returns a new envelop, projected along the given projection object.
    @param proj mapnik.Projection object
    @param envelope mapnik.Envelope object
    """
    c0 = proj.forward(mapnik.Coord(envelope.minx, envelope.miny))
    c1 = proj.forward(mapnik.Coord(envelope.maxx, envelope.maxy))
    return mapnik.Envelope(c0.x, c0.y, c1.x, c1.y)


class MapCanvas:
    """
    OSM in the background of a canvas used to draw grids and text.
    """
    def __init__(self, mapfile_path, geographic_bbox, graph_bbox = None):
        """
        @param mapfile_path (string) path the the osm.xml map file
        @param geographic_bbox (BoundingBox) bounding box to render, in
        latlong (4326) coordinates
        @param graph_bbox (int) graphical width/height of the
        rendered area for raster output (None = auto)
        """
        self._projname    = GLOBALS.MAIN_PROJECTION
        self._proj        = mapnik.Projection(self._projname)
        if graph_bbox is None:
            graph_bbox = geographic_bbox.get_pixel_size_for_zoom_factor()
        elif str(graph_bbox).startswith('zoom:'):
            graph_bbox = geographic_bbox.get_pixel_size_for_zoom_factor(int(graph_bbox[5:]))
        self._envelope    = mapnik.Envelope(geographic_bbox.get_top_left()[1],
                                            geographic_bbox.get_top_left()[0],
                                            geographic_bbox.get_bottom_right()[1],
                                            geographic_bbox.get_bottom_right()[0])
        # Determine the size of a meter in pixels (float)
        ymeters, xmeters = geographic_bbox.spheric_sizes()
        xpixels = graph_bbox[0] / xmeters
        ypixels = graph_bbox[1] / ymeters
        self.one_meter_in_pixels = min(xpixels, ypixels)
        l.debug('Geo size: %sx%s, pixels=%sx%s, 1m=%s|%s' \
                    % (xmeters, ymeters,
                       graph_bbox[0], graph_bbox[1],
                       xpixels, ypixels))

        self._map         = mapnik.Map(graph_bbox[0],
                                       graph_bbox[1],
                                       self._projname)
        mapnik.load_map(self._map, mapfile_path)

        # Keep geographic bounding box, ignoring one dimension of the
        # specified grwidth/grheight constraints
        self._map.aspect_fix_mode = mapnik.aspect_fix_mode.SHRINK_CANVAS

        # The data to render in the resulting scene
        self._labels      = mapnik.PointDatasource()
        self._labelstyles = set() # Set of label styles, used to
                                  # define the sets of layers
        self._shapes      = []    # Data from the shape files
        self._dirty       = True  # Rendering needed because data have
                                  # been added

    def add_label(self, x, y, str_label,
                  str_color = "red", alpha = 0.5,
                  font_size = 11,
                  font_family = "DejaVu Sans Book"):
        """
        Add a label on top of the map.
        @param x,y Coordinates of the label, in latlong coordinates (4326)
        @param str_label (string) Text to display
        @param str_color (string) Color definition (html)
        @param alpha (float 0..1) Color opacity
        @param font_size (int) Font size of the label
        @param font_family (string) Name of the font
        """
        pt = self._proj.forward(mapnik.Coord(x,  y))
        labelstyle = (str_color, alpha, font_size, font_family)
        self._labels.add_point(pt.x, pt.y,
                               'style_%x' % hash(labelstyle),
                               str_label)
        self._labelstyles.add(labelstyle)
        self._dirty = True

    def _render_label_style(self, str_color, alpha, font_size, font_family):
        labelstyle = (str_color, alpha, font_size, font_family)
        H = hash(labelstyle)

        s = mapnik.Style()
        r = mapnik.Rule()
        c = mapnik.Color(str_color)
        c.a = int(255 * alpha)
        symb = mapnik.TextSymbolizer('style_%x' % H,
                                     font_family,
                                     int(font_size),
                                     c)
        symb.allow_overlap       = True
        symb.set_label_placement = mapnik.label_placement.POINT_PLACEMENT
        r.symbols.append(symb)
        s.rules.append(r)

        lyr = mapnik.Layer('Labels_%x' % H, self._projname)
        lyr.datasource = self._labels
        self._map.append_style('labels_%x' % H, s)
        lyr.styles.append('labels_%x' % H)
        self._map.layers.append(lyr)

    def add_shapefile(self, path_shpfile, str_color = 'grey', alpha = 0.5,
                      line_width = 1.):
        """
        Add a shape file to display on top of the map
        @param path_shpfile (string) path to the shape file to render
        @param str_color (string) Color definition (html)
        @param alpha (float 0..1) Color opacity
        @param line_width (float) line width in raster pixels
        """
        col = mapnik.Color(str_color)
        col.a = int(255 * alpha)
        self._shapes.append(['SHPFILE', (path_shpfile, col, line_width)])
        self._dirty = True

    def _render_shp(self, path_shpfile, obj_color, line_width):
        shpid = os.path.basename(path_shpfile)
        s,r = mapnik.Style(), mapnik.Rule()
        r.symbols.append(mapnik.PolygonSymbolizer(obj_color))
        r.symbols.append(mapnik.LineSymbolizer(obj_color, line_width))
        s.rules.append(r)
        self._map.append_style('style_' + shpid, s)
        lyr = mapnik.Layer(shpid)
        lyr.datasource = mapnik.Shapefile(file=path_shpfile)
        lyr.styles.append("style_" + shpid)
        self._map.layers.append(lyr)

    def render_map(self):
        """
        Render map in memory. Automatically called by save_map(), only
        when needed.
        @return the mapnik map object
        """
        for lyrtype, lyrparms in self._shapes:
            self._render_shp(*lyrparms)

        for labelstyle in self._labelstyles:
            self._render_label_style(*labelstyle)

        l.debug("rendering to bbox %s as %sx%s..."
                % (self._envelope, self._map.height, self._map.width))
        bbox = _project_envelope(self._proj, self._envelope)
        self._map.zoom_to_box(bbox)
        l.debug("rendered to bbox %s as %sx%s." \
                    % (bbox, self._map.height, self._map.width))
        self._dirty = False
        return self._map

    def save_map(self, output_filename,
                 title = "City's map",
                 file_type = None,
                 force = False):
        """
        Save the map as an image. By default, the format is inferred
        from the filename (its extension). It can be forced with the
        'file_type' parameter.
        @param output_filename (string) file to generate
        @param file_type (string) None, or 'xml', 'png', 'ps',
        'pdf', 'svg'
        @param force (bool) fore render_map() to be called, even if it
        does not appear to have changed since last render_map()
        """
        if self._dirty or force:
            self.render_map()

        if file_type is None:
            file_type = output_filename.split('.')[-1]
        
        file_type = file_type.lower()
        cairo_factory = None

        if file_type == 'xml':
            mapnik.save_map(self._map, output_filename)
            return

        elif file_type in ('png', 'png24'): # 24-bits, the default
            if (title is None) or (cairo is None):
                mapnik.render_to_file(self._map, output_filename, 'png')
                return
            else:
                cairo_factory = \
                    lambda w,h: cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)

        elif file_type == 'svg' and cairo is not None:
            cairo_factory = lambda w,h: cairo.SVGSurface(output_filename, w, h)

        elif file_type == 'pdf' and cairo is not None:
            cairo_factory = lambda w,h: cairo.PDFSurface(output_filename, w, h)

        elif file_type == 'ps' and cairo is not None:
            cairo_factory = lambda w,h: cairo.PSSurface(output_filename, w, h)

        else:
            raise ValueError('Unsupported output format: %s' % file_type)

        # Cairo reendering
        if title is not None:
            frame_width = max(self._map.height / 20., 30)

            surface = cairo_factory(self._map.width + frame_width*2,
                                    self._map.height + frame_width*2)
            enclose_in_frame(lambda ctx: mapnik.render(self._map, ctx),
                             self._map.width, self._map.height,
                             title,
                             surface, self._map.width + frame_width*2,
                             self._map.height + frame_width*2, frame_width)
        else:
            surface = cairo_factory(self._map.width, self._map.height)
            ctx = cairo.Context(surface)
            mapnik.render(self._map, ctx)

        surface.flush()

        # png rendering with cairo...
        if file_type in ('png', 'png24', 'png8'):
            out_file = open(output_filename, 'wb')
            try:
                surface.write_to_png(out_file)
            finally:
                out_file.close()

        surface.finish()


if __name__ == "__main__":
    # A few tests

    # Create the grid shape file
    g = GridFile("mygrid.shp")
    g.add_horiz_line(44.48)
    g.add_vert_line(-1.08)
    g.flush()
    
    # Declare a map with a grid and some text
    sanguinet = MapCanvas("/home/decot/downloads/svn/mapnik-osm/osm.xml",
                          BoundingBox(44.4883, -1.0901,
                                      44.4778, -1.0637))
    sanguinet.add_label(-1.075, 44.483, "Toto")
    sanguinet.add_label(-1.075, 44.479, "Titi", '#ff00ff', 30)
    sanguinet.add_shapefile(g.get_filepath())

    # Save the rendered map into different file formats
    for fname in ('sanguinet.xml', 'sanguinet.png',
                  'sanguinet.svg', 'sanguinet.pdf',
                  'sanguinet.ps', 'sanguinet.jpg'):
        sanguinet.save_map(fname)

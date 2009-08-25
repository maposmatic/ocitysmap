#! /usr/bin/env python


import os, mapnik
from osgeo import ogr


class GLOBALS:
    MAIN_PROJECTION = "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +no_defs +over"


class GridFile:
    """
    Class to generate a shape_file containing vertical/horizontal lines.
    Call flush() to commit the final rendering to disk. Afterwards,
    any attempt to add grid lines will fail (exception).
    The coordinates are not related to any projection
    """
    def __init__(self, out_filename, layer_name = "Grid"):
        """
        @param out_filename (string) path to the output shape file we generate
        @param layer_name (string) layer name in the shape file
        """
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
        line.AddPoint_2D(-180, y)
        line.AddPoint_2D(180, y)
        f = ogr.Feature(feature_def = self._layer.GetLayerDefn())
        f.SetGeometryDirectly(line)
        self._layer.CreateFeature(f)
        f.Destroy()

    def add_vert_line(self, x):
        """
        Add a new longitude line at the given longitude
        """
        line = ogr.Geometry(type = ogr.wkbLineString)
        line.AddPoint_2D(x, -80)
        line.AddPoint_2D(x, 80)
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
        Get the path to the destination shape file
        """
        return self._filepath

    def __str__(self):
        return "GridFile(%s)" % self._filepath


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
    def __init__(self, mapfile_path, envelope, grwidth = 800, grheight = 600):
        """
        @param mapfile_path (string) path the the osm.xml map file
        @param envelope (mapnik.Envelope) bounding box to render, in
        latlong (4326) coordinates
        @param grwidth/grwidth (int) graphical width/height of the
        rendered area for raster output
        """
        self._projname    = GLOBALS.MAIN_PROJECTION
        self._proj        = mapnik.Projection(self._projname)
        self._envelope    = envelope
        self._map         = mapnik.Map(grwidth, grheight, self._projname)
        mapnik.load_map(self._map, mapfile_path)
        self._labels      = mapnik.PointDatasource()
        self._labelstyles = set()
        self._shapes      = []

    def add_label(self, x, y, str_label, str_color = "red", font_size = 11):
        """
        Add a label on top of the map.
        @param x,y Coordinates of the label, in latlong coordinates (4326)
        @param str_label (string) Text to display
        @param str_color (string) Color definition (html)
        @param font_size (int) Font size of the label
        """
        labelstyle = "%s:%s" % (str_color, font_size)
        pt = self._proj.forward(mapnik.Coord(x,  y))
        self._labels.add_point(pt.x, pt.y, 'style_' + labelstyle,
                               str_label)
        self._labelstyles.add(labelstyle)

    def _render_label_style(self, labelstyle):
        str_color, font_size = labelstyle.split(':')

        s = mapnik.Style()
        r = mapnik.Rule()
        symb = mapnik.TextSymbolizer('style_' + labelstyle,
                                     "DejaVu Sans Book",
                                     int(font_size),
                                     mapnik.Color(str_color))
        symb.allow_overlap       = True
        symb.set_label_placement = mapnik.label_placement.POINT_PLACEMENT
        r.symbols.append(symb)
        s.rules.append(r)

        lyr = mapnik.Layer('Labels_' + labelstyle, self._projname)
        lyr.datasource = self._labels
        self._map.append_style('labels_' + labelstyle, s)
        lyr.styles.append('labels_' + labelstyle)
        self._map.layers.append(lyr)

    def add_shp(self, path_shpfile, str_color = mapnik.Color('black')):
        """
        Add a shape file to display on top of the map
        @param path_shpfile (string) path to the shape file to render
        @param str_color (string) Color definition (html)
        """
        self._shapes.append(['SHPFILE', (path_shpfile, str_color)])

    def _render_shp(self, path_shpfile, str_color):
        shpid = os.path.basename(path_shpfile)
        s,r = mapnik.Style(), mapnik.Rule()
        r.symbols.append(mapnik.PolygonSymbolizer(str_color))
        r.symbols.append(mapnik.LineSymbolizer(str_color, 1))
        s.rules.append(r)
        self._map.append_style('style_' + shpid, s)
        lyr = mapnik.Layer(shpid)
        lyr.datasource = mapnik.Shapefile(file=path_shpfile)
        lyr.styles.append("style_" + shpid)
        self._map.layers.append(lyr)

    def render_map(self):
        for labelstyle in self._labelstyles:
            self._render_label_style(labelstyle)

        for lyrtype, lyrparms in self._shapes:
            self._render_shp(*lyrparms)

        bbox = _project_envelope(self._proj, self._envelope)
        self._map.zoom_to_box(bbox)
        return self._map

if __name__ == "__main__":
    # A few tests

    # Create the grid shape file
    g = GridFile("toto.shp")
    g.add_horiz_line(44.48)
    g.add_vert_line(-1.08)
    g.flush()
    
    # Declare a map with a grid and some text
    sanguinet = MapCanvas("/home/decot/downloads/svn/mapnik-osm/osm.xml",
                          mapnik.Envelope(-1.0901, 44.4883, -1.0637, 44.4778),
                          800, 600)
    sanguinet.add_label(-1.075, 44.483, "Toto")
    sanguinet.add_label(-1.075, 44.479, "Titi", '#ff00ff', 30)
    sanguinet.add_shp(g.get_filepath())
    m = sanguinet.render_map()
    
    # Render the whole thing as png, svg, etc.
    mapnik.save_map(m,"map.xml")
    mapnik.render_to_file(m, 'map.png')

    try:
        import cairo
        surface = cairo.SVGSurface('map.svg', m.width,m.height)
        mapnik.render(m, surface)
        surface = cairo.PDFSurface('map.pdf', m.width,m.height)
        mapnik.render(m, surface)
        surface = cairo.PSSurface('map.ps', m.width,m.height)
        mapnik.render(m, surface)
    except Exception, ex:
        print '\n\nSkipping cairo examples as Pycairo not available:', ex


import mapnik
from osgeo import ogr


class GridFile:
    def __init__(self, out_filename, envelope, layer_name = "Grid"):
        self._filepath = out_filename
        self._envelope = envelope
        driver = ogr.GetDriverByName('ESRI Shapefile')
        driver.DeleteDataSource(out_filename)
        self._ds = driver.CreateDataSource(out_filename)
        self._layer = self._ds.CreateLayer(layer_name,
                                           geom_type=ogr.wkbLineString)

    def add_horiz_line(self, y):
        line = ogr.Geometry(type = ogr.wkbLineString)
        line.AddPoint_2D(self._envelope.minx, y)
        line.AddPoint_2D(self._envelope.maxx, y)
        f = ogr.Feature(feature_def = self._layer.GetLayerDefn())
        f.SetGeometryDirectly(line)
        self._layer.CreateFeature(f)
        f.Destroy()

    def add_vert_line(self, x):
        pass

    def flush(self):
        self._ds.Destroy()
        self._ds = None

    def get_filepath(self):
        return self._filepath

    def __str__(self):
        return "GridFile(%s)" % self._filepath

g = GridFile("toto.shp", mapnik.Envelope(-1.0901,44.4883,-1.0637,44.4778))
g.add_horiz_line(44.48)
g.flush()


def shpfile(mmm):
    s,r = mapnik.Style(),mapnik.Rule()
    r.symbols.append(mapnik.PolygonSymbolizer(mapnik.Color('black')))
    r.symbols.append(mapnik.LineSymbolizer(mapnik.Color('black'), 1))
    s.rules.append(r)
    mmm.append_style('yostyle', s)
    lyr = mapnik.Layer('thegrid')
    ### lyr.srs = "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +no_defs +over" # "+proj=latlong"
    lyr.datasource = mapnik.Shapefile(file='toto')
    lyr.styles.append('yostyle')
    mmm.layers.append(lyr)

class BasicMap:
    def __init__(self, mapfile_path, ul_x, ul_y, lr_x, lr_y):
        """
        TODO: mettre 800,600 en parametre
        """
        self._projname = "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +no_defs +over"
        self._proj = mapnik.Projection(self._projname)
        self._ul   = (ul_x, ul_y)
        self._lr   = (lr_x, lr_y)
        self._map  = mapnik.Map(800,600, self._projname)
        mapnik.load_map(self._map, mapfile_path)
        self._labels = mapnik.PointDatasource()
        self._shapes = []

    def add_label(self, x, y, str_label):
        pt = self._proj.forward(mapnik.Coord(x,  y))
        self._labels.add_point(pt.x, pt.y, 'LABELS',
                               str_label)

    def add_horiz_line(self, y):
        pass

    def add_vert_line(self, x):
        pass

    def add_shp(self, path_shpfile):
        pass

    def render_map(self):
        s = mapnik.Style()
        r = mapnik.Rule()
        symb = mapnik.TextSymbolizer("LABELS", "DejaVu Sans Book",
                                     10, mapnik.Color('red'))
        symb.allow_overlap       = True
        symb.set_label_placement = mapnik.label_placement.POINT_PLACEMENT
        r.symbols.append(symb)
        s.rules.append(r)
        
        lyr = mapnik.Layer('Labels', self._projname)
        lyr.datasource = self._labels
        self._map.append_style('places_labels', s)
        lyr.styles.append('places_labels')
        self._map.layers.append(lyr)

        shpfile(self._map)

        c0 = self._proj.forward(mapnik.Coord(self._ul[0], self._ul[1]))
        c1 = self._proj.forward(mapnik.Coord(self._lr[0], self._lr[1]))
        bbox = mapnik.Envelope(c0.x,c0.y,c1.x,c1.y)
        print bbox
        self._map.zoom_to_box(bbox)
        ### self._map.zoom_all()

        return self._map



sanguinet = BasicMap("/home/decot/downloads/svn/mapnik-osm/osm.xml",
                     -1.0901,44.4883,
                     -1.0637,44.4778)
sanguinet.add_label(-1.075, 44.483, "Toto")
them = sanguinet.render_map()

## shpfile(them)
mapnik.save_map(them,"map.xml")
mapnik.render_to_file(them, 'map.png')

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

import logging
import mapnik
import os

import coords
import shapes

l = logging.getLogger('ocitysmap')

# TODO: use 4002 instead?
_MAIN_PROJECTION = "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +no_defs +over"

class MapCanvas:
    """
    The MapCanvas renders a geographic bounding box into a Cairo surface of a
    given width and height (in pixels). Shape files can be overlayed on the
    map; the order they are added to the map being important with regard to
    their respective alpha levels.
    """

    def __init__(self, stylesheet, bounding_box, width_px, height_px):
        """Initialize the map canvas for rendering.

        Args:
            stylesheet (Stylesheet): map stylesheet.
            bounding_box (coords.BoundingBox): geographic bounding box.
            width_px (int): width in pixels of the rendering surface.
            height_px (int): height in pixels of the rendering surface.
        """

        self._geo_bbox = bounding_box
        self._proj = mapnik.Projection(_MAIN_PROJECTION)

        # TODO: if (width_px, height_px) is large enough compared to
        # bounding_box.get_pixel_size_for_zoom_factor(), try higher zooms.

        self._map = mapnik.Map(width_px, height_px, _MAIN_PROJECTION)
        mapnik.load_map(self._map, stylesheet.path)

        # Keep geographic bounding box, ignoring one dimension of the
        # specified grwidth/grheight constraints
        self._map.aspect_fix_mode = mapnik.aspect_fix_mode.GROW_BBOX

        # Added shapes to render
        self._shapes = []

        l.debug('MapCanvas %dx%d pixels for %s.' % (width_px, height_px,
                                                    bounding_box))

    def add_shape_file(self, shape_file, str_color='grey', alpha=0.5,
                       line_width=1.0):
        """
        Args:
            shape_file (shapes.ShapeFile): ...
        """
        col = mapnik.Color(str_color)
        col.a = int(255 * alpha)
        self._shapes.append({'shape_file': shape_file,
                             'color': col,
                             'line_width': line_width})
        l.debug('Added shape file %s to map canvas as layer %s.' %
                (shape_file.get_filepath(), shape_file.get_layer_name()))
        return shape_file

    def render(self):
        """Render the map in memory with all the added shapes. Returns the
        corresponding mapnik.Map object."""
        envelope = self._project_envelope(
                mapnik.Envelope(self._geo_bbox.get_top_left()[1],
                                self._geo_bbox.get_top_left()[0],
                                self._geo_bbox.get_bottom_right()[1],
                                self._geo_bbox.get_bottom_right()[0]))

        # Add all shapes to the map
        for shape in self._shapes:
            self._render_shape_file(**shape)

        self._map.zoom_to_box(envelope)

        return self._map

    def _render_shape_file(self, shape_file, color, line_width):
        shape_file.flush()

        shpid = os.path.basename(shape_file.get_filepath())
        s,r = mapnik.Style(), mapnik.Rule()
        r.symbols.append(mapnik.PolygonSymbolizer(color))
        r.symbols.append(mapnik.LineSymbolizer(color, line_width))
        s.rules.append(r)

        self._map.append_style('style_%s' % shpid, s)
        layer = mapnik.Layer(shpid)
        layer.datasource = mapnik.Shapefile(file=shape_file.get_filepath())
        layer.styles.append('style_%s' % shpid)

        self._map.layers.append(layer)

    def _project_envelope(self, envelope):
        """Project the given bounding box into the rendering projection."""
        c0 = self._proj.forward(mapnik.Coord(envelope.minx, envelope.miny))
        c1 = self._proj.forward(mapnik.Coord(envelope.maxx, envelope.maxy))
        return mapnik.Envelope(c0.x, c0.y, c1.x, c1.y)


if __name__ == '__main__':
    class StylesheetMock:
        def __init__(self):
            self.path = '/home/sam/src/python/maposmatic/mapnik-osm/osm.xml'

    logging.basicConfig(level=logging.DEBUG)

    # Basic unit test
    bbox = coords.BoundingBox(48.7148, 2.0155, 48.6950, 2.0670)

    px, py = bbox.get_pixel_size_for_zoom_factor(16)
    canvas = MapCanvas(StylesheetMock(), bbox, px, py)

    canvas.add_shape_file(
        shapes.ShapeFile(bbox, '/tmp/mygrid.shp', 'grid')
            .add_vert_line(2.04)
            .add_horiz_line(48.7),
        'red', 0.3, 10.0)

    canvas.add_shape_file(
        shapes.ShapeFile(bbox, '/tmp/mypoly.shp', 'shade')
            .add_shade_from_wkt('POLYGON((2.04537559754772 48.702794853359,2.0456929723376 48.7033682610593,2.0457757970068 48.7037022715908,2.04577876144723 48.7043963708738,2.04589724923321 48.7043963708738,2.04589428479277 48.704519562418,2.04746445007788 48.7044706533954,2.04723043894637 48.7024665875529,2.04674876229103 48.7024238422904,2.04615641319268 48.702500973452,2.04537559754772 48.702794853359))'),
        'blue', 0.3)

    my_map = canvas.render()
    mapnik.render_to_file(my_map, '/tmp/mymap.png', 'png')

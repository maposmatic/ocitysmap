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
import locale

from ocitysmap2.index import commons


l = logging.getLogger('ocitysmap')


class StreetIndex:
    def __init__(self, db, osmid, bounding_box, i18n, grid, polygon):
        self._db = db
        self._osmid = osmid
        self._bounding_box = bounding_box
        self._i18n = i18n
        self._grid = grid
        self._polygon = polygon

    def _humanize_street_label(self, street):
        return (self._i18n.user_readable_street(street[0]),
                self._i18n.user_readable_label(street[1]))

    def _humanize_street_list(self, sl):
        """Given a list of street and their corresponding squares, do some
        cleanup and pass it through the internationalization layer to
        get proper sorting, filtering of common prefixes, etc.

        Args:
            sl (list): list of streets, each in the form [(name, squares)].

        Returns the humanized street list.
        """

        # We transform the string representing the squares list into a
        # Python list
        sl = [(street[0],
               [map(int, x.split(',')) for x in street[1].split(';')[:-1]])
              for street in sl]

        # Street prefixes are postfixed, a human readable label is
        # built to represent the list of squares, and the list is
        # alphabetically-sorted.
        prev_locale = locale.getlocale(locale.LC_COLLATE)
        locale.setlocale(locale.LC_COLLATE, self._i18n.language_code())
        try:
            sl = sorted(map(self._humanize_street_label, sl),
                        lambda x, y: locale.strcoll(x[0].lower(), y[0].lower()))
        finally:
            locale.setlocale(locale.LC_COLLATE, prev_locale)

        result = []
        first_letter = None
        current_category = None
        for street in sl:
            if not self._i18n.first_letter_equal(street[0][0], first_letter):
                current_category = commons.IndexCategory(street[0])
                result.append(current_category)
            current_category.items.append(commons.IndexItem(street[0],
                                                            street[1]))

        return result

    def get_streets_nogrid(self):
        """Get the list of streets in the administrative area if city
        is defined or in the bounding box otherwise. Don't try to map
        these streets onto the grid of squares.

        Returns a list of commons.IndexCategory objects, with their IndexItems
        having no specific grid location
        """

        cursor = self._db.cursor()
        l.info("Getting streets...")

        intersect = 'true'
        if self._polygon:
            # Limit to the polygon
            intersect = """st_intersects(way, st_transform(
                                GeomFromText('%s', 4002), 900913))""" \
                % self._polygon
        elif self._bounding_box:
            # Limit to the bounding box
            intersect = """st_intersects(way, st_transform(
                                GeomFromText('%s', 4002), 900913))""" \
                % self._bounding_box.as_wkt()
        else:
            raise ValueError("No suitable bounding box provided")

        query = """select distinct name
                          from planet_osm_line
                          where trim(name) != ''
                                and highway is not null
                                and %s
                          group by name
                          order by name;""" % intersect
        cursor.execute(query)
        sl = cursor.fetchall()

        l.debug("Got streets (%d)." % len(sl))

        return sl


    def get_streets(self):
        """Get the list of streets in the administrative area if city is
        defined or in the bounding box otherwise, and for each
        street, the list of squares that it intersects.

        Returns a list of the form [(street_name, 'A-B1'),
                                    (street2_name, 'B3')]
        """

        cursor = self._db.cursor()
        l.info("Getting streets...")

        intersect = 'true'
        if self._polygon:
            intersect = """st_intersects(way, st_transform(
                                GeomFromText('%s', 4002), 900913))""" % self._polygon

        cursor.execute("""select name, textcat_all(x || ',' || y || ';')
                          from (select distinct name, x, y
                                from planet_osm_line
                                join %s
                                on st_intersects(way, st_transform(geom, 900913))
                                where trim(name) != '' and highway is not null
                                and %s)
                          as foo
                          group by name
                          order by name;""" % \
                           (self._map_areas_table_name,
                            intersect))

        sl = cursor.fetchall()
        l.debug("Got streets (%d)." % len(sl))
        return self._humanize_street_list(sl)


if __name__ == "__main__":
    import os
    import psycopg2
    from ocitysmap2 import i18n, coords

    db = psycopg2.connect(user='maposmatic',
                          password='waeleephoo3Aew3u',
                          host='localhost',
                          database='maposmatic')

    i18n = i18n.install_translation("fr_FR",
                                    os.path.join(os.path.dirname(__file__),
                                                 "..", "..", "locale"))

    idx_polygon = coords.BoundingBox(48.7097, 2.0333, 48.7048, 2.0462)
    street_index = StreetIndex(db, None, None, i18n, None,
                               idx_polygon.as_wkt())
    sl = street_index.get_streets_nogrid()
    ### print sl

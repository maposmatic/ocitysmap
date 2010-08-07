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
import psycopg2

from ocitysmap2.index import commons

import psycopg2.extensions
# compatibility with django: see http://code.djangoproject.com/ticket/5996
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
# SQL string escaping routine
_sql_escape_unicode = lambda s: psycopg2.extensions.adapt(s.encode('utf-8'))


l = logging.getLogger('ocitysmap')


class StreetIndex:

    def __init__(self, db, osmid, bounding_box, i18n, grid, polygon_wkt):
        self._db = db
        self._osmid = osmid
        self._bounding_box = bounding_box
        self._i18n = i18n
        self._grid = grid
        self._polygon_wkt = polygon_wkt

        # Build the contents of the index
        self._categories = \
            (self._build_street_index_nogrid()
             + self._build_amenities_index_nogrid())

        if not self._categories:
            raise IndexEmptyError("Nothing to index")

    @property
    def categories(self):
        return self._categories

    def _get_selected_amenities(self):
        # Amenities to retrieve from DB, a list of string tuples:
        #  1. Category, displayed headers in the final index
        #  2. db_amenity, description string stored in the DB
        #  3. Label, text to display in the index for this amenity
        selected_amenities = [
            (_(u"Places of worship"), "place_of_worship", _(u"Place of worship")),
            (_(u"Education"), "kindergarten", _(u"Kindergarten")),
            (_(u"Education"), "school", _(u"School")),
            (_(u"Education"), "college", _(u"College")),
            (_(u"Education"), "university", _(u"University")),
            (_(u"Education"), "library", _(u"Library")),
            (_(u"Public buildings"), "townhall", _(u"Town hall")),
            (_(u"Public buildings"), "post_office", _(u"Post office")),
            (_(u"Public buildings"), "public_building", _(u"Public building")),
            (_(u"Public buildings"), "police", _(u"Police"))]

        return selected_amenities

    def _convert_street_index(self, sl):
        """Given a list of street names, do some cleanup and pass it
        through the internationalization layer to get proper sorting,
        filtering of common prefixes, etc.

        Args:
            sl (list of strings): list of street names

        Returns the list of IndexCategory objects. Each IndexItem will
        have its square location still undefined at that point
        """

        # Street prefixes are postfixed, a human readable label is
        # built to represent the list of squares, and the list is
        # alphabetically-sorted.
        prev_locale = locale.getlocale(locale.LC_COLLATE)
        locale.setlocale(locale.LC_COLLATE, self._i18n.language_code())
        try:
            sorted_sl = sorted(map(self._i18n.user_readable_street, sl),
                               lambda x,y: locale.strcoll(x.lower(), y.lower()))
        finally:
            locale.setlocale(locale.LC_COLLATE, prev_locale)

        result = []
        current_category = None
        for street in sorted_sl:
            if (not current_category
                or not self._i18n.first_letter_equal(street[0],
                                                     current_category.name)):
                current_category = commons.IndexCategory(street[0])
                result.append(current_category)
            current_category.items.append(commons.IndexItem(street))

        return result

    def _build_street_index_nogrid(self):
        """Get the list of streets in the administrative area if city
        is defined or in the bounding box otherwise. Don't try to map
        these streets onto the grid of squares.

        Returns a list of commons.IndexCategory objects, with their IndexItems
        having no specific grid square location
        """

        cursor = self._db.cursor()
        l.info("Getting streets (no grid)...")

        query = """select distinct name
                          from planet_osm_line
                          where trim(name) != ''
                                and highway is not null
                                and st_intersects(way, st_transform(
                                         GeomFromText('%s', 4002), 900913))
                          group by name
                          order by name;""" \
            % (self._polygon_wkt or self._bounding_box.as_wkt())

        cursor.execute(query)
        sl = cursor.fetchall()

        l.debug("Got %d streets (no grid)." % len(sl))

        return self._convert_street_index([name for (name,) in sl])

    def _build_amenities_index_nogrid(self):
        cursor = self._db.cursor()

        intersect = ("""st_intersects(way, st_transform(
                                     GeomFromText('%s', 4002), 900913))"""
                     % (self._polygon_wkt or self._bounding_box.as_wkt()))


        result = []
        for catname, db_amenity, label in self._get_selected_amenities():
            l.info("Getting amenities for %s/%s..." % (catname, db_amenity))

            # Get the current IndexCategory object, or create one if
            # different than previous
            if (not result or result[-1].name != catname):
                current_category = commons.IndexCategory(catname)
                result.append(current_category)
            else:
                current_category = result[-1]

            query = """select name, db_table, osm_id
                       from (select distinct amenity, name,
                                             'point' as db_table,
                                             osm_id
                                    from planet_osm_point
                                    where amenity = %(amenity)s
                                          and %(intersect)s
                             union
                             select distinct amenity, name,
                                             'polygon' as db_table,
                                             osm_id
                                    from planet_osm_polygon
                                    where amenity = %(amenity)s
                                          and %(intersect)s)
                        as foo
                        group by amenity, osm_id, db_table, name
                        order by amenity, name""" \
                % dict(amenity   = _sql_escape_unicode(db_amenity),
                       intersect = intersect)

            cursor.execute(query)
            items = [commons.IndexItem(name or label, db_table = db_table,
                                       osm_id = osm_id) \
                         for name,db_table,osm_id in cursor.fetchall()]

            l.debug("Got %d amenities for %s/%s."
                    % (len(items), catname, db_amenity))
            current_category.items.extend(items)

        return [category for category in result if category.items]

    def build_data_nogrid(self):
        return self._categories

if __name__ == "__main__":
    import os
    import psycopg2
    from ocitysmap2 import i18n, coords

    logging.basicConfig(level=logging.DEBUG)

    db = psycopg2.connect(user='maposmatic',
                          password='waeleephoo3Aew3u',
                          host='localhost',
                          database='maposmatic')

    i18n = i18n.install_translation("fr_FR.UTF-8",
                                    os.path.join(os.path.dirname(__file__),
                                                 "..", "..", "locale"))

    idx_polygon = coords.BoundingBox(48.7097, 2.0333, 48.7048, 2.0462)

    street_index = StreetIndex(db, None, None, i18n, None,
                               idx_polygon.as_wkt())
    print street_index.categories

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
import csv
import datetime
from itertools import groupby

import commons
from ocitysmap2 import coords

import psycopg2.extensions
# compatibility with django: see http://code.djangoproject.com/ticket/5996
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
# SQL string escaping routine
_sql_escape_unicode = lambda s: psycopg2.extensions.adapt(s.encode('utf-8'))


l = logging.getLogger('ocitysmap')


class StreetIndex:

    def __init__(self, db, polygon_wkt, i18n, page_number=None):
        """
        Prepare the index of the streets inside the given WKT. This
        constructor will perform all the SQL queries.

        Args:
           db (psycopg2 DB): The GIS database
           polygon_wkt (str): The WKT of the surrounding polygon of interest
           i18n (i18n.i18n): Internationalization configuration

        Note: All the arguments have to be provided !
        """
        self._i18n = i18n
        self._page_number = page_number

        # Build the contents of the index
        self._categories = \
            (self._list_streets(db, polygon_wkt)
             + self._list_amenities(db, polygon_wkt)
             + self._list_villages(db, polygon_wkt))

    @property
    def categories(self):
        return self._categories

    def apply_grid(self, grid):
        """
        Update the location_str field of the streets and amenities by
        mapping them onto the given grid.

        Args:
           grid (ocitysmap2.Grid): the Grid object from which we
           compute the location strings

        Returns:
           Nothing, but self._categories has been modified!
        """
        for category in self._categories:
            for item in category.items:
                item.update_location_str(grid)
        self.group_identical_grid_locations()

    def group_identical_grid_locations(self):
        """
        Group locations whith the same name and the same position on the grid.

        Returns:
           Nothing, but self._categories has been modified!
        """
        categories = []
        for category in self._categories:
            if category.is_street:
                categories.append(category)
                continue
            grouped_items = []
            sort_key = lambda item:(item.label, item.location_str)
            items = sorted(category.items, key=sort_key)
            for label, same_items in groupby(items, key=sort_key):
                grouped_items.append(same_items.next())
            category.items = grouped_items

    def write_to_csv(self, title, output_filename):
        # TODO: implement writing the index to CSV
        try:
            fd = open(output_filename, 'w')
        except Exception,ex:
            l.warning('error while opening destination file %s: %s'
                      % (output_filename, ex))
            return

        l.debug("Creating CSV file %s..." % output_filename)
        writer = csv.writer(fd)

        # Try to treat indifferently unicode and str in CSV rows
        def csv_writerow(row):
            _r = []
            for e in row:
                if type(e) is unicode:
                    _r.append(e.encode('UTF-8'))
                else:
                    _r.append(e)
            return writer.writerow(_r)

        copyright_notice = (u'© %(year)d MapOSMatic/ocitysmap authors. '
                            u'Map data © %(year)d OpenStreetMap.org '
                            u'and contributors (CC-BY-SA)' %
                            {'year': datetime.date.today().year})
        if title is not None:
            csv_writerow(['# (UTF-8)', title, copyright_notice])
        else:
            csv_writerow(['# (UTF-8)', '', copyright_notice])

        for category in self._categories:
            csv_writerow(['%s' % category.name])
            for item in category.items:
                csv_writerow(['', item.label, item.location_str or '???'])

        fd.close()

    def _get_selected_amenities(self):
        """
        Return the kinds of amenities to retrieve from DB as a list of
        string tuples:
          1. Category, displayed headers in the final index
          2. db_amenity, description string stored in the DB
          3. Label, text to display in the index for this amenity

        Note: This has to be a function because gettext() has to be
        called, which takes i18n into account... It cannot be
        statically defined as a class attribute for example.
        """

        # Make sure gettext is available...
        try:
            selected_amenities = [
                (_(u"Places of worship"), "place_of_worship",
                 _(u"Place of worship")),
                (_(u"Education"), "kindergarten", _(u"Kindergarten")),
                (_(u"Education"), "school", _(u"School")),
                (_(u"Education"), "college", _(u"College")),
                (_(u"Education"), "university", _(u"University")),
                (_(u"Education"), "library", _(u"Library")),
                (_(u"Public buildings"), "townhall", _(u"Town hall")),
                (_(u"Public buildings"), "post_office", _(u"Post office")),
                (_(u"Public buildings"), "public_building",
                 _(u"Public building")),
                (_(u"Public buildings"), "police", _(u"Police"))]
        except NameError:
            l.exception("i18n has to be initialized beforehand")
            return []

        return selected_amenities

    def _convert_street_index(self, sl):
        """Given a list of street names, do some cleanup and pass it
        through the internationalization layer to get proper sorting,
        filtering of common prefixes, etc.

        Args:
            sl (list of tuple): list tuples of the form (street_name,
                                linestring_wkt) where linestring_wkt
                                is a WKT for the linestring between
                                the 2 most distant point of the
                                street, in 4326 SRID

        Returns the list of IndexCategory objects. Each IndexItem will
        have its square location still undefined at that point
        """

        # Street prefixes are postfixed, a human readable label is
        # built to represent the list of squares, and the list is
        # alphabetically-sorted.
        prev_locale = locale.getlocale(locale.LC_COLLATE)
        locale.setlocale(locale.LC_COLLATE, self._i18n.language_code())
        try:
            sorted_sl = sorted([(self._i18n.user_readable_street(name),
                                 linestring) for name,linestring in sl],
                               lambda x,y: locale.strcoll(x[0].lower(),
                                                          y[0].lower()))
        finally:
            locale.setlocale(locale.LC_COLLATE, prev_locale)

        result = []
        current_category = None
        for street_name, linestring in sorted_sl:

            # Create new category if needed
            if (not current_category
                or not self._i18n.first_letter_equal(street_name[0],
                                                     current_category.name)):
                current_category = commons.IndexCategory(
                    self._i18n.upper_unaccent_string(street_name[0]))
                result.append(current_category)

            # Parse the WKT from the largest linestring in shape
            try:
                s_endpoint1, s_endpoint2 = map(lambda s: s.split(),
                                               linestring[11:-1].split(','))
            except (ValueError, TypeError):
                l.exception("Error parsing %s for %s" % (repr(linestring),
                                                         repr(street_name)))
                raise
            endpoint1 = coords.Point(s_endpoint1[1], s_endpoint1[0])
            endpoint2 = coords.Point(s_endpoint2[1], s_endpoint2[0])
            current_category.items.append(commons.IndexItem(street_name,
                                                            endpoint1,
                                                            endpoint2,
                                                            self._page_number))

        return result

    def _list_streets(self, db, polygon_wkt):
        """Get the list of streets inside the given polygon. Don't
        try to map them onto the grid of squares (there location_str
        field remains undefined).

        Args:
           db (psycopg2 DB): The GIS database
           polygon_wkt (str): The WKT of the surrounding polygon of interest

        Returns a list of commons.IndexCategory objects, with their IndexItems
        having no specific grid square location
        """

        cursor = db.cursor()
        l.info("Getting streets...")

        # PostGIS >= 1.5.0 for this to work:
        query = """
select name,
       --- street_kind, -- only when group by is: group by name, street_kind
       st_astext(st_transform(ST_LongestLine(street_path, street_path),
                              4002)) as longest_linestring
from
  (select name,
          -- highway as street_kind, -- only when group by name, street_kind
          st_intersection(%(wkb_limits)s,
                          st_linemerge(st_collect(way))) as street_path
   from planet_osm_line
          where trim(name) != '' and highway is not null
                and st_intersects(way, %(wkb_limits)s)
   group by name ---, street_kind -- (optional)
   order by name) as foo;
""" % dict(wkb_limits = ("st_transform(GeomFromText('%s', 4002), 900913)"
                         % (polygon_wkt,)))

        # l.debug("Street query (nogrid): %s" % query)

        cursor.execute(query)
        sl = cursor.fetchall()

        l.debug("Got %d streets." % len(sl))

        return self._convert_street_index(sl)


    def _list_amenities(self, db, polygon_wkt):
        """Get the list of amenities inside the given polygon. Don't
        try to map them onto the grid of squares (there location_str
        field remains undefined).

        Args:
           db (psycopg2 DB): The GIS database
           polygon_wkt (str): The WKT of the surrounding polygon of interest

        Returns a list of commons.IndexCategory objects, with their IndexItems
        having no specific grid square location
        """

        cursor = db.cursor()

        result = []
        for catname, db_amenity, label in self._get_selected_amenities():
            l.info("Getting amenities for %s/%s..." % (catname, db_amenity))

            # Get the current IndexCategory object, or create one if
            # different than previous
            if (not result or result[-1].name != catname):
                current_category = commons.IndexCategory(catname,
                                                         is_street=False)
                result.append(current_category)
            else:
                current_category = result[-1]

            query = """
select amenity_name,
       st_astext(st_transform(ST_LongestLine(amenity_contour, amenity_contour),
                              4002)) as longest_linestring
from (
       select name as amenity_name,
              st_intersection(%(wkb_limits)s, way) as amenity_contour
       from planet_osm_point
       where trim(name) != ''
             and amenity = %(amenity)s and ST_intersects(way, %(wkb_limits)s)
      union
       select name as amenity_name,
              st_intersection(%(wkb_limits)s, way) as amenity_contour
       from planet_osm_polygon
       where trim(name) != '' and amenity = %(amenity)s
             and ST_intersects(way, %(wkb_limits)s)
     ) as foo
order by amenity_name""" \
                % {'amenity': _sql_escape_unicode(db_amenity),
                   'wkb_limits': ("st_transform(GeomFromText('%s', 4002), 900913)"
                                  % (polygon_wkt,))}


            # l.debug("Amenity query for for %s/%s (nogrid): %s" \
            #             % (catname, db_amenity, query))

            cursor.execute(query)

            for amenity_name, linestring in cursor.fetchall():
                # Parse the WKT from the largest linestring in shape
                try:
                    s_endpoint1, s_endpoint2 = map(lambda s: s.split(),
                                                   linestring[11:-1].split(','))
                except (ValueError, TypeError):
                    l.exception("Error parsing %s for %s/%s/%s"
                                % (repr(linestring), catname, db_amenity,
                                   repr(amenity_name)))
                    continue
                    ## raise
                endpoint1 = coords.Point(s_endpoint1[1], s_endpoint1[0])
                endpoint2 = coords.Point(s_endpoint2[1], s_endpoint2[0])
                current_category.items.append(commons.IndexItem(amenity_name,
                                                                endpoint1,
                                                                endpoint2,
                                                                self._page_number))

            l.debug("Got %d amenities for %s/%s."
                    % (len(current_category.items), catname, db_amenity))

        return [category for category in result if category.items]

    def _list_villages(self, db, polygon_wkt):
        """Get the list of villages inside the given polygon. Don't
        try to map them onto the grid of squares (there location_str
        field remains undefined).

        Args:
           db (psycopg2 DB): The GIS database
           polygon_wkt (str): The WKT of the surrounding polygon of interest

        Returns a list of commons.IndexCategory objects, with their IndexItems
        having no specific grid square location
        """

        cursor = db.cursor()

        result = []
        current_category = commons.IndexCategory(_(u"Villages"),
                                                 is_street=False)
        result.append(current_category)

        query = """
select village_name,
       st_astext(st_transform(ST_LongestLine(village_contour, village_contour),
                              4002)) as longest_linestring
from (
       select name as village_name,
              st_intersection(%(wkb_limits)s, way) as village_contour
       from planet_osm_point
       where trim(name) != ''
             and (place = 'locality'
                  or place = 'hamlet'
                  or place = 'isolated_dwelling')
             and ST_intersects(way, %(wkb_limits)s)
     ) as foo
order by village_name""" \
            % {'wkb_limits': ("st_transform(GeomFromText('%s', 4002), 900913)"
                              % (polygon_wkt,))}


        # l.debug("Villages query for %s (nogrid): %s" \
        #             % ('Villages', query))

        cursor.execute(query)

        for village_name, linestring in cursor.fetchall():
            # Parse the WKT from the largest linestring in shape
            try:
                s_endpoint1, s_endpoint2 = map(lambda s: s.split(),
                                               linestring[11:-1].split(','))
            except (ValueError, TypeError):
                l.exception("Error parsing %s for %s/%s"
                            % (repr(linestring), 'Villages',
                               repr(village_name)))
                continue
                ## raise
            endpoint1 = coords.Point(s_endpoint1[1], s_endpoint1[0])
            endpoint2 = coords.Point(s_endpoint2[1], s_endpoint2[0])
            current_category.items.append(commons.IndexItem(village_name,
                                                            endpoint1,
                                                            endpoint2,
                                                            self._page_number))

        l.debug("Got %d villages for %s."
                % (len(current_category.items), 'Villages'))

        return [category for category in result if category.items]

if __name__ == "__main__":
    import os
    import psycopg2
    from ocitysmap2 import i18n

    logging.basicConfig(level=logging.DEBUG)

    db = psycopg2.connect(user='maposmatic',
                          password='waeleephoo3Aew3u',
                          host='localhost',
                          database='maposmatic')

    i18n = i18n.install_translation("fr_FR.UTF-8",
                                    os.path.join(os.path.dirname(__file__),
                                                 "..", "..", "locale"))

    # Chevreuse
    chevreuse_bbox = coords.BoundingBox(48.7097, 2.0333, 48.7048, 2.0462)
    limits_wkt = chevreuse_bbox.as_wkt()

    # Paris envelope:
    # limits_wkt = """POLYGON((2.22405967037499 48.8543531620913,2.22407682819692 48.8550025657752,2.22423996225251 48.8557367772146,2.22466908746374 48.8572219531993,2.22506398686264 48.8582666566114,2.22559363355415 48.8594446700813,2.2256475324712 48.8595315483635,2.22678057753906 48.861620896078,2.22753588102995 48.8635801454558,2.22787059330481 48.8647094580464,2.22819677158448 48.8653982612096,2.2290979614775 48.8666404585278,2.22973316021491 48.8672502886549,2.23105485149243 48.8683285824972,2.23214657405722 48.8695317674313,2.23752344019032 48.8710122798192,2.23998374609047 48.8716393690211,2.2406936846595 48.8720829886714,2.24189536101507 48.872839461003,2.24319136047547 48.8738725534154,2.24437587900911 48.8749394788509,2.24560396583403 48.876357855343,2.2475739712521 48.8757695828576,2.25479813293547 48.8740773968287,2.25538769725643 48.8742418854232,2.25841672656296 48.8800895643967,2.25883381434937 48.8802801449622,2.27745184777039 48.8779547879509,2.27972135150419 48.8786284619886,2.2799882409751 48.8789087875894,2.28068147087986 48.8818378450628,2.2818318534327 48.8837294922328,2.28231793183294 48.8838550796657,2.28449203448356 48.8855611708289,2.28577384056247 48.8864085830218,2.28619479110461 48.8867093618694,2.28716685807356 48.8872081947562,2.28783807925385 48.8875526789321,2.28864323924301 48.8879659741163,2.28891794405689 48.888090074233,2.28971618701836 48.8884625499349,2.29060021908946 48.8888914901301,2.2910407529048 48.889100761049,2.29231914538563 48.8897813727734,2.29280746957407 48.889718645603,2.29453124677277 48.8896871638578,2.29575008095026 48.8900483462911,2.29616537210611 48.8902642866599,2.29733794304647 48.8910359587209,2.29849335616491 48.8916923874085,2.30047153625207 48.8926164760274,2.30323852699021 48.8938978632484,2.30376898216549 48.8941694805188,2.30599186333604 48.8952257558751,2.30716075118374 48.895782794086,2.30753112657538 48.8959580779389,2.3095294289249 48.8967071614408,2.31232139282795 48.8977543476603,2.31338886088006 48.8980659834922,2.31527002291654 48.8986490922026,2.3161877418108 48.8989256442189,2.31850782069509 48.8996320466728,2.3186937719589 48.8997429489435,2.31986508525787 48.9004574890899,2.32026717117904 48.9006974778028,2.32035754169662 48.9007570614361,2.32190785421396 48.9008073738244,2.32408474164196 48.9008856768068,2.32755547257369 48.9008753427098,2.3277815785307 48.9009897853332,2.33018241595904 48.9010280509197,2.33437611103142 48.9011239509646,2.34387471718264 48.9013669480994,2.34414043884369 48.9013294504412,2.34815474035383 48.9014532811833,2.35198506689379 48.9014935541578,2.35509512423894 48.9015322917683,2.35784441816599 48.901608644928,2.36560774868288 48.9017625909672,2.37010498448976 48.9018541788921,2.37028114411698 48.9018568952303,2.3715506432765 48.9018857710774,2.37597825964886 48.9019807837163,2.37900028209617 48.9020473928421,2.38442916068422 48.9021559867851,2.38618599588537 48.901825184925,2.38870406345829 48.9013527757594,2.38942343433781 48.9012220947855,2.38942612928366 48.901219496516,2.39066068397863 48.9009871870515,2.39373992910953 48.8992668587557,2.39552739686187 48.8982616923999,2.39644098350582 48.8967792698801,2.3969293975258 48.8959819963415,2.39776222562571 48.8945922886365,2.39802974391732 48.893447763192,2.39801492171513 48.8935286763732,2.39826231774438 48.8926270480788,2.39881388332883 48.890253950367,2.39895932057332 48.8895456434227,2.39910251202961 48.8886453608921,2.3991283835098 48.8875843982919,2.39955014253569 48.8875104454888,2.39916467544727 48.8865343409336,2.39919692496597 48.8858403943193,2.3992251320659 48.8853650577775,2.39924848826328 48.8848527974081,2.40007305186258 48.8838178642316,2.4014665185313 48.8826086429161,2.40379216697036 48.8814466523376,2.40460945421585 48.8812171456678,2.40718249868415 48.8805096559317,2.40837555121299 48.8803798656879,2.40929021583528 48.8802754779329,2.41081034495907 48.8784304903174,2.41084259447777 48.8784022507851,2.41185625344437 48.8771519560988,2.4124848944802 48.8763725664976,2.41283757306074 48.8751571978536,2.41313805952328 48.8741215913749,2.41342911367534 48.873149893187,2.41356727456603 48.8726744951149,2.41362404809199 48.8724535746873,2.41370256084782 48.8716509499783,2.41378511602243 48.8708747835672,2.41382086897074 48.8705644554421,2.41395444845349 48.8692854838219,2.41400888635971 48.8676265832271,2.41392121078798 48.865438090478,2.41427317071629 48.8635013703719,2.41435258178741 48.8633375556219,2.41429544893534 48.86108297997,2.41449361728702 48.8598641666786,2.4146241424978 48.8590365765406,2.41474819983854 48.8587550757552,2.41485078744398 48.8577987414008,2.41516681476094 48.8558674588656,2.41526688708359 48.8552628686639,2.41528063130744 48.8551795884365,2.41534045910536 48.8548472936301,2.41542642787805 48.8543619690239,2.41549595748104 48.8539192562004,2.41559863491801 48.8534670821859,2.41571029550783 48.8527875722221,2.41588232288474 48.8518013915656,2.41603791109195 48.8508464612523,2.41619754171794 48.8498895620232,2.41633264833667 48.8492345945092,2.41641933576159 48.8487604470666,2.41590693672352 48.8466070719205,2.4158173746897 48.8459314888008,2.41570274965944 48.8452938500999,2.41508273245034 48.8438678534372,2.41483057535009 48.842407466859,2.41397762498782 48.8397444662905,2.41343683918678 48.8382643887995,2.41308496908999 48.8372079747027,2.41286182757341 48.8365921613894,2.41272447516647 48.8361966532922,2.41248094189295 48.8351168985142,2.41227567685053 48.8345595985272,2.41120937660828 48.8338612648054,2.41185337883546 48.8337666549157,2.41276912143609 48.8336280511047,2.41377514472278 48.8335691561952,2.41456503335211 48.8335829929573,2.4152836855794 48.8336421835075,2.41609872703668 48.8337632844351,2.41802022342941 48.8342701548677,2.41971058329954 48.8348930923147,2.42037623492507 48.8350979770248,2.42216028907934 48.835786478119,2.42174365045056 48.836467342233,2.42157791128064 48.8368203945709,2.42146292692427 48.8373379951919,2.42136842415638 48.8378079936814,2.42127904178561 48.8382237692705,2.42101987782615 48.8390223774626,2.42081524160442 48.8396772420515,2.42053451807814 48.8402191720905,2.42030571717527 48.8406060755701,2.4200338869703 48.8408907527957,2.41983958137434 48.8410638641368,2.41957143426203 48.841498295291,2.4194850163317 48.841891574028,2.41949453847371 48.8421841662022,2.41943623781177 48.8425948801975,2.41960179731864 48.8427473525507,2.4198688664526 48.8430295936735,2.41994342662119 48.8433190458415,2.41981406922027 48.8434354529104,2.42209974262919 48.8444911444825,2.42232683673301 48.8443736757305,2.4224450550244 48.8442929786174,2.42254979858653 48.8442016990887,2.42274715845445 48.8439993937374,2.42290418396612 48.8437964963748,2.42304917205297 48.8435854987992,2.4236784419095 48.8426801914628,2.42453121260871 48.8419447834817,2.42477411706154 48.841896067273,2.42472228426964 48.8417684826086,2.4250133384217 48.8417235500266,2.42756428433401 48.8415158545549,2.42824206321588 48.8414465634173,2.43078968536165 48.8413390791936,2.43159969625334 48.8412721527067,2.43229364481032 48.8412155725592,2.43289785167042 48.8411423789194,2.43343522387338 48.8410234833686,2.43353817080494 48.8411703438687,2.43713304890893 48.840876563315,2.43794862935538 48.8445595446304,2.43937416587975 48.844428596988,2.44051242117626 48.8443530432941,2.4406181528852 48.8448934447891,2.44079565998534 48.8448677875258,2.44085872171828 48.8452092526994,2.44068292141718 48.8452065924015,2.440762961309 48.8459171825144,2.44667486402532 48.8457350430313,2.4465157723885 48.8449324627219,2.44773784050101 48.8448136944047,2.4508502334659 48.8444805622559,2.45368262155673 48.8440907918728,2.45684127775875 48.8436784939176,2.45827462962609 48.8434694467977,2.4598624917223 48.8431756797296,2.46110701771692 48.842915846081,2.46205977090726 48.8426616866754,2.46269487981313 48.8424582518045,2.4632613574313 48.8421589805216,2.46424842626549 48.8417239638795,2.46530412638739 48.8410234833686,2.46573325159861 48.8406450968431,2.46645423944564 48.8400349425497,2.46722634143235 48.8390912580791,2.46853994787231 48.8378656419534,2.46941544594822 48.8370634676784,2.4696986847573 48.8366792567132,2.46979758927008 48.8364964923528,2.46975833289216 48.8357040524303,2.46962951448042 48.8352841759955,2.469376818391 48.8346450417393,2.46897805623638 48.8341124531957,2.46894293210877 48.8340655624265,2.46873425346827 48.8338930773407,2.4684829946833 48.833685349399,2.4681630147791 48.83350044538,2.46768493138489 48.833309154447,2.46675804967473 48.8328283516622,2.46638156573916 48.8325708887733,2.46606769437889 48.8323229449658,2.46572795153843 48.8319670816639,2.46544597037075 48.8315933574293,2.46527798541262 48.8312954995835,2.46511368354715 48.8309088789962,2.46499097367934 48.8304478634571,2.46468033625409 48.829476440867,2.46453741429239 48.8286916960156,2.46455591958724 48.8276476765417,2.46476693384748 48.827591554113,2.46508278150138 48.8275423508361,2.46522525430544 48.8276692620745,2.46540869028646 48.8275586730823,2.46616695821778 48.827329451485,2.46581778306685 48.8265121461304,2.46574735514857 48.8262822692052,2.46538704088811 48.8251054862733,2.46518545893835 48.8250846684754,2.46527987187471 48.8246208788162,2.46514233980472 48.8243022796837,2.46474366748162 48.8233780527712,2.46468662446108 48.8233752730267,2.46292781296631 48.8203007812736,2.46264268769513 48.8194471626414,2.4625531256613 48.8193715712664,2.46253803396453 48.8192435743433,2.46101026916082 48.8184906690057,2.45957682746195 48.8177797489504,2.45883877162452 48.8174406994093,2.45808337830211 48.8173220433582,2.45637532162088 48.8174689733421,2.45465019694926 48.8172375761677,2.45322654688698 48.8173483653878,2.45083927401944 48.817916148904,2.44960858208019 48.8180567481208,2.44732452563879 48.818110751838,2.44506122028045 48.8180814727215,2.44269299169693 48.8180604745566,2.44198386161164 48.8180874468456,2.43986159175291 48.8184555934794,2.43736292779013 48.818326647826,2.43750971250756 48.8192294970277,2.43688735967872 48.8195204471285,2.43617912790872 48.8196933957274,2.43516259433321 48.8197602918961,2.43490801178169 48.81967677518,2.43452964138402 48.8194661491895,2.43436533951855 48.8194927658336,2.43419852237029 48.8193901438057,2.4343578835017 48.8202087482566,2.43249298097186 48.8215368818771,2.43293315546108 48.8217982459121,2.43277855540069 48.821881463367,2.43264317928737 48.8219974470946,2.43221531171754 48.8217339548627,2.43039254017454 48.8229863438568,2.4305666336766 48.8231762547516,2.43030064252097 48.8232780410172,2.42970838325415 48.8234758760205,2.42917622127984 48.8236283474274,2.42852395455204 48.8237809957994,2.427802966705 48.8239278477077,2.42714207615048 48.8240239547446,2.42645531411577 48.8241030876619,2.42554235629252 48.8241716930794,2.42465293432971 48.8241878981385,2.4234599716324 48.8241482726199,2.42285055454365 48.8241143839052,2.42180338841696 48.8240634620762,2.42091073251913 48.8240352510058,2.41995806916032 48.8240860545781,2.41934865207157 48.824153950308,2.41861904039781 48.8242838863918,2.41781226344114 48.8244929544404,2.4172629436449 48.8246059750222,2.41659342926365 48.8247020807587,2.41596685435297 48.8247641797519,2.41512576175245 48.8247641797519,2.41461938142679 48.8247415875556,2.41388114592631 48.8247076992422,2.41260239411936 48.8247020807587,2.41152082251728 48.8248094823974,2.41040502510288 48.8250241667014,2.40984717131144 48.8252106988182,2.4095934870752 48.8253025452268,2.40872427720629 48.8256969565131,2.40802907100791 48.826103843296,2.40753122467745 48.8264315976597,2.40699043887641 48.8268045915822,2.40610649663684 48.827482561693,2.40505924067861 48.8283357477846,2.40415679314418 48.8288372916559,2.40312867130151 48.8292981446041,2.40238181197429 48.8295467538789,2.40146121847113 48.82936159804,2.40029439674858 48.828848586832,2.39983086606198 48.8286903949966,2.39569089024358 48.8277253844162,2.39434153085531 48.8274719758729,2.39341455931363 48.8270650410594,2.39270219529332 48.8267656778066,2.39101857278782 48.8260457675067,2.39024997423073 48.8257170643678,2.38881231045002 48.8250059510992,2.38717072909982 48.8244232849018,2.38514421965038 48.8237067712519,2.38151349876655 48.8224128807427,2.38074516970405 48.8216876439636,2.37905867258964 48.8211390665207,2.37788565249164 48.8208040616663,2.37602497204364 48.8201182529016,2.37415387113835 48.8195135859543,2.37390485814159 48.8195361805072,2.37086046764371 48.8185493450421,2.36695261649473 48.8172924680276,2.36696115048993 48.8171455966772,2.36538191222045 48.8164108785601,2.36485657744229 48.8163676977867,2.36431408484222 48.8162124833021,2.36334076023187 48.8160458519734,2.36025819133442 48.8157374908686,2.35668163886222 48.8160636567673,2.35617166527543 48.8159785959341,2.35590899788635 48.8159722666451,2.35584261238685 48.8159954543165,2.35561435047316 48.8161225722528,2.35535788145954 48.8162946452976,2.35511291088156 48.8164794945072,2.35462368837783 48.8169598626578,2.35419456316661 48.8172876768224,2.3538119706871 48.8174337787999,2.35343063584899 48.8175532626916,2.35333622291263 48.8175815957113,2.35282121876025 48.817688953459,2.35222904932496 48.8177341441997,2.35174836081642 48.8177284657843,2.35119904102018 48.8176380842518,2.35048667699988 48.8174571432466,2.34984294426728 48.8172593436366,2.34927646664911 48.8170559830563,2.34859832844113 48.8167620610855,2.34742243373422 48.8161799497174,2.34697615070107 48.816010360671,2.34665868607966 48.8159651683763,2.34602348734226 48.8160273964993,2.34526818385137 48.8161007451382,2.34459372873605 48.8160886781114,2.34447047987907 48.8155624582755,2.34444541688264 48.8155255469646,2.34366963180328 48.815818293137,2.34304512301776 48.8160522995573,2.34162892897234 48.8163212636258,2.34029852403656 48.8164059689672,2.33958903462517 48.8164496820727,2.33873931819792 48.8164892545265,2.33811445008628 48.8165226751843,2.33675377192543 48.8165755566752,2.33618729430726 48.8165981525526,2.33513671458248 48.8166802547645,2.33494276831264 48.8166885951114,2.33370246439986 48.8167583937045,2.33211541078741 48.8169823992109,2.33203123864528 48.8169932830019,2.33219437270088 48.8176466610404,2.33234672697307 48.8182133764852,2.3292783514571 48.8188955440884,2.32736916198376 48.8193461966713,2.32566811216175 48.8197292984568,2.32132996799168 48.8206846446699,2.31988844145525 48.8210021430204,2.31418755299918 48.8222493455562,2.31400735095318 48.8223115658781,2.30921708470061 48.8234334701976,2.30687382928199 48.8239227614225,2.30459606104757 48.8243880952424,2.30415274245486 48.8244955566963,2.30400101700337 48.8245166704496,2.30126582662629 48.8251162500177,2.29764687367268 48.8259108681886,2.29422959250036 48.8266900974691,2.29222069003049 48.8271378412956,2.29090331066633 48.8276893691378,2.28938767311896 48.8283238611162,2.28546904218657 48.829978742085,2.28336285217143 48.8308616895553,2.27902309103384 48.8324594827402,2.27632769602384 48.830228648962,2.27575996076428 48.8297178937999,2.27339568476801 48.8283193666538,2.27272688903898 48.8279749477035,2.27230836394811 48.8279610502545,2.26783708945293 48.8278866544835,2.26760478512046 48.8279671414773,2.26729971724997 48.8315588824109,2.26967162892616 48.8328133911768,2.27002951773535 48.8330080545344,2.26997543915525 48.8330472591227,2.26779953987406 48.8345744993608,2.26692476045038 48.8345170838228,2.26617763162858 48.8344520995247,2.26489681369648 48.8342849966568,2.26296911892829 48.8339027748382,2.26278244901225 48.8339252446421,2.25745831398633 48.8345391985692,2.25702927860663 48.8345165516496,2.25675457379275 48.8344826699466,2.25520965116712 48.8347538411894,2.25511523823076 48.8348385745105,2.25205108479663 48.8384259797004,2.25170774869504 48.8385728478167,2.25113264725014 48.8425497709943,2.25252988684306 48.8455598787296,2.25068663371158 48.8456377952918,2.24249372882582 48.8477268953035,2.24156136739244 48.8484739820425,2.24035744524866 48.8495405623492,2.23967867821998 48.8500017568624,2.2380956670263 48.8503630485457,2.2312561639476 48.8518493888202,2.22409811826915 48.853457152044,2.22405967037499 48.8543531620913))"""

    # Paris bbox
    # limits_wkt = """POLYGON((2.22405964791711 48.8155243047565,2.22405964791711 48.9021584078545,2.46979772401737 48.9021584078545,2.46979772401737 48.8155243047565,2.22405964791711 48.8155243047565))"""

    street_index = StreetIndex(db, limits_wkt, i18n)

    print "=> Got %d categories, total %d items" \
        % (len(street_index.categories),
           reduce(lambda r,cat: r+len(cat.items), street_index.categories, 0))

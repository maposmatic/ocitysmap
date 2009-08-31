-- ocitysmap, city map and street index generator from OpenStreetMap data
-- Copyright (C) 2009  David Decotigny
-- Copyright (C) 2009  Frédéric Lehobey
-- Copyright (C) 2009  David Mentré
-- Copyright (C) 2009  Maxime Petazzoni
-- Copyright (C) 2009  Thomas Petazzoni
-- Copyright (C) 2009  Gaël Utard

-- This program is free software: you can redistribute it and/or modify
-- it under the terms of the GNU Affero General Public License as
-- published by the Free Software Foundation, either version 3 of the
-- License, or any later version.

-- This program is distributed in the hope that it will be useful,
-- but WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
-- GNU Affero General Public License for more details.

-- You should have received a copy of the GNU Affero General Public License
-- along with this program.  If not, see <http://www.gnu.org/licenses/>.



-- Create a view that associates each city with an area representing
--  its territory, based on the administrative boundaries available in
--  OSM database. For french cities, these boundaries are admin_level 8,
--  and are for the moment only available for part of the country.

create or replace view cities_area
   as select name as city, st_buildarea(way) as area
   from planet_osm_line where boundary='administrative' and admin_level='8';

-- Create an aggregate used to build the list of squares that each
-- street intersects

CREATE AGGREGATE textcat_all(
  basetype    = text,
  sfunc       = textcat,
  stype       = text,
  initcond    = ''
);



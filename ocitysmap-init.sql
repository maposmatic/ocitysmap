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



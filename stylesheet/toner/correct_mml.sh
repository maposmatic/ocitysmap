#!/bin/sh

sed -i 's|<Parameter name="password"></Parameter>|<Parameter name="password">\&nev_pass;</Parameter>|' style-toner-standard.mml
sed -i 's/land_110m/ne_110m_land/' style-toner-standard.mml
sed -i 's/land_50m/ne_50m_land/' style-toner-standard.mml
sed -i "s/admin_0_countries_110m</ne_110m_admin_0_countries</" style-toner-standard.mml
sed -i "s/admin_0_countries_50m</ne_50m_admin_0_countries</" style-toner-standard.mml
sed -i "s/admin_0_countries_10m</ne_10m_admin_0_countries</" style-toner-standard.mml
sed -i 's/admin_1_states_provinces_lines_110m/ne_110m_admin_1_states_provinces_lines_shp/' style-toner-standard.mml
sed -i 's/admin_1_states_provinces_lines_50m/ne_50m_admin_1_states_provinces_lines_shp/' style-toner-standard.mml
sed -i 's/admin_1_states_provinces_lines_10m/ne_10m_admin_1_states_provinces_lines_shp/' style-toner-standard.mml
sed -i 's/admin_1_states_provinces_110m/ne_110m_admin_1_states_provinces_shp/' style-toner-standard.mml
sed -i 's/admin_1_states_provinces_50m/ne_50m_admin_1_states_provinces_shp/' style-toner-standard.mml
sed -i 's/admin_1_states_provinces_10m/ne_10m_admin_1_states_provinces_shp/' style-toner-standard.mml

sed -i 's/lakes_110m/ne_110m_lakes/' style-toner-standard.mml
sed -i 's/lakes_50m/ne_50m_lakes/' style-toner-standard.mml
sed -i 's/lakes_10m/ne_10m_lakes/' style-toner-standard.mml

sed -i 's/geography_marine_polys_110m/ne_110m_geography_marine_polys/' style-toner-standard.mml
sed -i 's/geography_marine_polys_50m/ne_50m_geography_marine_polys/' style-toner-standard.mml
sed -i 's/geography_marine_polys_10m/ne_10m_geography_marine_polys/' style-toner-standard.mml

sed -i 's/coastline_10m/ne_10m_coastline/' style-toner-standard.mml

sed -i 's|<Parameter name="estimate_extent">false</Parameter>|<Parameter name="estimate_extent">false</Parameter>\n            <Parameter name="extent">\&epsg900913_extent;</Parameter>|' style-toner-standard.mml

-- This file is used to create the maposmatic_admin table, which
-- contains a single table, with a single column and a single value,
-- used only to store the timestamp of the last update of the OSM
-- database. This is used by the website to show the current
-- replication lag with the official database, and to display on the
-- generated maps the age of the data used for the rendering.

CREATE TABLE maposmatic_admin (last_update timestamp);

-- Insert dummy value so that the planet-update script only needs to
-- do an UPDATE query.
INSERT INTO maposmatic_admin VALUES ('1970-01-01 00:00:00');

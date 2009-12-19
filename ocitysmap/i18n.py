# -*- coding: utf-8; mode: Python -*-

# ocitysmap, city map and street index generator from OpenStreetMap data
# Copyright (C) 2009  David Decotigny
# Copyright (C) 2009  Frédéric Lehobey
# Copyright (C) 2009  David Mentré
# Copyright (C) 2009  Maxime Petazzoni
# Copyright (C) 2009  Thomas Petazzoni
# Copyright (C) 2009  Gaël Utard

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

import re

APPELLATIONS = [ u"Allée", u"Avenue", u"Boulevard", u"Carrefour", u"Chaussée",
                 u"Chemin", u"Cité", u"Clos", u"Côte", u"Cour", u"Cours", 
                 u"Degré",
                 u"Esplanade", u"Impasse", u"Liaison", u"Mail", u"Montée",
                 u"Passage", u"Place", u"Placette", u"Pont", u"Promenade", 
                 u"Quai",
                 u"Résidence", u"Rond-Point", u"Rang", u"Route", u"Rue", 
                 u"Ruelle",
                 u"Square", u"Traboule", u"Traverse", u"Venelle", u"Villa",
                 u"Voie", u"Rond-point" ]
DETERMINANTS = [ u" des", u" du", u" de la", u" de l'", u" de", u" d'", u"" ]

SPACE_REDUCE = re.compile(r"\s+")
PREFIX_REGEXP = re.compile(r"^(?P<prefix>(%s)(%s)?)\s?\b(?P<name>.*)" %
                           ("|".join(APPELLATIONS),
                            "|".join(DETERMINANTS)), re.IGNORECASE | re.UNICODE)

# for IndexPageGenerator._upper_unaccent_string
E_ACCENT = re.compile(ur"[éèêëẽ]", re.IGNORECASE | re.UNICODE)
I_ACCENT = re.compile(ur"[íìîïĩ]", re.IGNORECASE | re.UNICODE)
A_ACCENT = re.compile(ur"[áàâäã]", re.IGNORECASE | re.UNICODE)
O_ACCENT = re.compile(ur"[óòôöõ]", re.IGNORECASE | re.UNICODE)
U_ACCENT = re.compile(ur"[úùûüũ]", re.IGNORECASE | re.UNICODE)

def user_readable_street(name):
    name = name.strip()
    name = SPACE_REDUCE.sub(" ", name)
    name = PREFIX_REGEXP.sub(r"\g<name> (\g<prefix>)", name)
    return name

def _upper_unaccent_string(s):
    s = E_ACCENT.sub("e", s)
    s = I_ACCENT.sub("i", s)
    s = A_ACCENT.sub("a", s)
    s = O_ACCENT.sub("o", s)
    s = U_ACCENT.sub("u", s)
    return s.upper()

def first_letter_equal(a, b):
    return _upper_unaccent_string(a) == _upper_unaccent_string(b)

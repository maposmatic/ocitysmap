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
import gettext

def _install_language(language, locale_path):
    t = gettext.translation(domain='ocitysmap', 
                            localedir=locale_path,
                            languages=[language],
                            fallback=True)
    t.install(unicode=True)

class i18n:
    """Functions needed to be implemented for a new language.
       See i18n_fr_FR_UTF8 below for an example. """
    def language_code(self):
        pass

    def user_readable_street(self, name):
        pass

    def first_letter_equal(self, a, b):
        pass

class i18n_template_code_CODE(i18n):
    def __init__(self, language, language_path):
        """Install the _() function for the chosen locale other
           object initialisation"""
        self.language = str(language) # FIXME: why do we have unicode here?
        _install_language(language, locale_path)
        
    def language_code(self):
        """returns the language code of the specific language
           supported, e.g. fr_FR.UTF-8"""
        return self.language

    def user_readable_street(self, name):
        """ transforms a street name into a suitable form for
            the map index, e.g. Paris (Rue de) for French"""
        return name

    def first_letter_equal(self, a, b):
        """returns True if the letters a and b are equal in the map index,
           e.g. É and E are equals in French map index"""
        return a == b


class i18n_fr_generic(i18n):
    APPELLATIONS = [ u"Allée", u"Allées", u"Avenue", u"Boulevard", u"Carrefour",
                     u"Chaussée", u"Chemin", u"Cheminement",
                     u"Cité", u"Clos", u"Côte", u"Cour", u"Cours",
                     u"Degré", u"Esplanade", u"Giratoire", u"Hameau",
                     u"Impasse", u"Liaison", u"Mail", u"Montée",
                     u"Passage", u"Place", u"Placette", u"Pont", u"Promenade",
                     u"Petite Avenue", u"Petite Rue", u"Quai",
                     u"Résidence", u"Rond-Point", u"Rang", u"Route forestière",
                     u"Route", u"Rue", u"Ruelle",
                     u"Square", u"Sentier", u"Sentiers",
                     u"Traboule", u"Traverse", u"Venelle", u"Villa",
                     u"Voie", u"Rond-point" ]
    DETERMINANTS = [ u" des", u" du", u" de la", u" de l'",
                          u" de", u" d'", u"" ]

    SPACE_REDUCE = re.compile(r"\s+")
    PREFIX_REGEXP = re.compile(r"^(?P<prefix>(%s)(%s)?)\s?\b(?P<name>.+)" %
                                    ("|".join(APPELLATIONS),
                                     "|".join(DETERMINANTS)), re.IGNORECASE
                                                                 | re.UNICODE)

    # for IndexPageGenerator._upper_unaccent_string
    E_ACCENT = re.compile(ur"[éèêëẽ]", re.IGNORECASE | re.UNICODE)
    I_ACCENT = re.compile(ur"[íìîïĩ]", re.IGNORECASE | re.UNICODE)
    A_ACCENT = re.compile(ur"[áàâäã]", re.IGNORECASE | re.UNICODE)
    O_ACCENT = re.compile(ur"[óòôöõ]", re.IGNORECASE | re.UNICODE)
    U_ACCENT = re.compile(ur"[úùûüũ]", re.IGNORECASE | re.UNICODE)

    def __init__(self, language, locale_path):
        self.language = str(language)
        _install_language(language, locale_path)

    def _upper_unaccent_string(self, s):
        s = self.E_ACCENT.sub("e", s)
        s = self.I_ACCENT.sub("i", s)
        s = self.A_ACCENT.sub("a", s)
        s = self.O_ACCENT.sub("o", s)
        s = self.U_ACCENT.sub("u", s)
        return s.upper()

    def language_code(self):
        return self.language

    def user_readable_street(self, name):
        name = name.strip()
        name = self.SPACE_REDUCE.sub(" ", name)
        name = self.PREFIX_REGEXP.sub(r"\g<name> (\g<prefix>)", name)
        return name

    def first_letter_equal(self, a, b):
        return self._upper_unaccent_string(a) == self._upper_unaccent_string(b)

class i18n_it_generic(i18n):
    APPELLATIONS = [ u"Via", u"Viale", u"Piazza", u"Scali", u"Strada", u"Largo",
                     u"Corso", u"Viale", u"Calle", u"Sottoportico",
		     u"Sottoportego", u"Vicolo", u"Piazzetta" ]
    DETERMINANTS = [ u" delle", u" dell'", u" dei", u" degli",
                     u" della", u" del", u" di", u"" ]

    SPACE_REDUCE = re.compile(r"\s+")
    PREFIX_REGEXP = re.compile(r"^(?P<prefix>(%s)(%s)?)\s?\b(?P<name>.+)" %
                                    ("|".join(APPELLATIONS),
                                     "|".join(DETERMINANTS)), re.IGNORECASE
                                                                 | re.UNICODE)

    # for IndexPageGenerator._upper_unaccent_string
    E_ACCENT = re.compile(ur"[éèêëẽ]", re.IGNORECASE | re.UNICODE)
    I_ACCENT = re.compile(ur"[íìîïĩ]", re.IGNORECASE | re.UNICODE)
    A_ACCENT = re.compile(ur"[áàâäã]", re.IGNORECASE | re.UNICODE)
    O_ACCENT = re.compile(ur"[óòôöõ]", re.IGNORECASE | re.UNICODE)
    U_ACCENT = re.compile(ur"[úùûüũ]", re.IGNORECASE | re.UNICODE)

    def __init__(self, language, locale_path):
        self.language = str(language)
        _install_language(language, locale_path)

    def _upper_unaccent_string(self, s):
        s = self.E_ACCENT.sub("e", s)
        s = self.I_ACCENT.sub("i", s)
        s = self.A_ACCENT.sub("a", s)
        s = self.O_ACCENT.sub("o", s)
        s = self.U_ACCENT.sub("u", s)
        return s.upper()

    def language_code(self):
        return self.language

    def user_readable_street(self, name):
        name = name.strip()
        name = self.SPACE_REDUCE.sub(" ", name)
        name = self.PREFIX_REGEXP.sub(r"\g<name> (\g<prefix>)", name)
        return name

    def first_letter_equal(self, a, b):
        return self._upper_unaccent_string(a) == self._upper_unaccent_string(b)

class i18n_es_generic(i18n):
    APPELLATIONS = [ u"Avenida", u"Avinguda", u"Calle", u"Camino", u"Camí", u"Carrer",
		     u"Carretera", u"Plaza", u"Plaça", u"Ronda" ]
    DETERMINANTS = [ u" de", u" de la", u" del", u" de las",
                     u" dels", u" de los", u" d'", u" de l'", u"" ]

    SPACE_REDUCE = re.compile(r"\s+")
    PREFIX_REGEXP = re.compile(r"^(?P<prefix>(%s)(%s)?)\s?\b(?P<name>.+)" %
                                    ("|".join(APPELLATIONS),
                                     "|".join(DETERMINANTS)), re.IGNORECASE
                                                                 | re.UNICODE)

    # for IndexPageGenerator._upper_unaccent_string
    E_ACCENT = re.compile(ur"[éèêëẽ]", re.IGNORECASE | re.UNICODE)
    I_ACCENT = re.compile(ur"[íìîïĩ]", re.IGNORECASE | re.UNICODE)
    A_ACCENT = re.compile(ur"[áàâäã]", re.IGNORECASE | re.UNICODE)
    O_ACCENT = re.compile(ur"[óòôöõ]", re.IGNORECASE | re.UNICODE)
    U_ACCENT = re.compile(ur"[úùûüũ]", re.IGNORECASE | re.UNICODE)
    N_ACCENT = re.compile(ur"[ñ]", re.IGNORECASE | re.UNICODE)

    def __init__(self, language, locale_path):
        self.language = str(language)
        _install_language(language, locale_path)

    def _upper_unaccent_string(self, s):
        s = self.E_ACCENT.sub("e", s)
        s = self.I_ACCENT.sub("i", s)
        s = self.A_ACCENT.sub("a", s)
        s = self.O_ACCENT.sub("o", s)
        s = self.U_ACCENT.sub("u", s)
        s = self.N_ACCENT.sub("n", s)
        return s.upper()

    def language_code(self):
        return self.language

    def user_readable_street(self, name):
        name = name.strip()
        name = self.SPACE_REDUCE.sub(" ", name)
        name = self.PREFIX_REGEXP.sub(r"\g<name> (\g<prefix>)", name)
        return name

    def first_letter_equal(self, a, b):
        return self._upper_unaccent_string(a) == self._upper_unaccent_string(b)

class i18n_generic(i18n):
    def __init__(self, language, locale_path):
        self.language = str(language)
        _install_language(language, locale_path)

    def language_code(self):
        return self.language

    def user_readable_street(self, name):
        return name

    def first_letter_equal(self, a, b):
        return a == b

# When not listed in the following map, default language class will be
# i18n_generic
language_class_map = {
    'fr_BE.UTF-8': i18n_fr_generic,
    'fr_FR.UTF-8': i18n_fr_generic,
    'fr_CA.UTF-8': i18n_fr_generic,
    'fr_CH.UTF-8': i18n_fr_generic,
    'fr_LU.UTF-8': i18n_fr_generic,
    'en_AG': i18n_generic,
    'en_AU.UTF-8': i18n_generic,
    'en_BW.UTF-8': i18n_generic,
    'en_CA.UTF-8': i18n_generic,
    'en_DK.UTF-8': i18n_generic,
    'en_GB.UTF-8': i18n_generic,
    'en_HK.UTF-8': i18n_generic,
    'en_IE.UTF-8': i18n_generic,
    'en_IN': i18n_generic,
    'en_NG': i18n_generic,
    'en_NZ.UTF-8': i18n_generic,
    'en_PH.UTF-8': i18n_generic,
    'en_SG.UTF-8': i18n_generic,
    'en_US.UTF-8': i18n_generic,
    'en_ZA.UTF-8': i18n_generic,
    'en_ZW.UTF-8': i18n_generic,
    'de_BE.UTF-8': i18n_generic,
    'nl_BE.UTF-8': i18n_generic,
    'it_IT.UTF-8': i18n_it_generic,
    'it_CH.UTF-8': i18n_it_generic,
    'de_AT.UTF-8': i18n_generic,
    'de_DE.UTF-8': i18n_generic,
    'de_LU.UTF-8': i18n_generic,
    'de_CH.UTF-8': i18n_generic,
    'es_ES.UTF-8': i18n_es_generic,
}

def install_translation(locale_name, locale_path):
    """Return a new i18n class instance, depending on the specified
    locale name (eg. "fr_FR.UTF-8"). See output of "locale -a" for a
    list of system-supported locale names. When none matching, default
    class is i18n_generic"""
    language_class = language_class_map.get(locale_name, i18n_generic)
    return language_class(locale_name, locale_path)

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

class i18n_ca_generic(i18n):

    APPELLATIONS = [ u"Avenida", u"Avinguda", u"Calle", u"Camino",
                     u"Camí", u"Carrer",
                     u"Carretera", u"Plaza", u"Plaça", u"Ronda" ]

    DETERMINANTS = [ u" de", u" de la", u" del", u" de las",
                     u" dels", u" de los", u" d'", u" de l'", u"de sa", u"de son", u"de s'",
                     u"de ses", u"d'en", u"de na", u"de n'", u"" ]

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
    C_ACCENT = re.compile(ur"[ç]", re.IGNORECASE | re.UNICODE)

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
        s = self.C_ACCENT.sub("c", s)
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

class i18n_pt_br_generic(i18n):
    APPELLATIONS = [ u"Aeroporto", u"Alameda", u"Área", u"Avenida",
                     u"Campo", u"Chácara", u"Colônia",
                     u"Condomínio", u"Conjunto", u"Distrito", u"Esplanada", u"Estação",
                     u"Estrada", u"Favela", u"Fazenda",
                     u"Feira", u"Jardim", u"Ladeira", u"Lago",
                     u"Lagoa", u"Largo", u"Loteamento", u"Morro", u"Núcleo",
                     u"Parque", u"Passarela", u"Pátio", u"Praça", u"Quadra",
                     u"Recanto", u"Residencial", u"Rua",
                     u"Setor", u"Sítio", u"Travessa", u"Trecho", u"Trevo",
                     u"Vale", u"Vereda", u"Via", u"Viaduto", u"Viela",
                     u"Vila" ]
    DETERMINANTS = [ u" do", u" da", u" dos", u" das", u"" ]
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

class i18n_ar_generic(i18n):
    APPELLATIONS = [ u"شارع", u"طريق", u"زقاق", u"نهج", u"جادة",
                     u"ممر", u"حارة",
                     u"كوبري", u"كوبرى", u"جسر", u"مطلع", u"منزل",
                     u"مفرق", u"ملف", u"تقاطع",
                     u"ساحل",
                     u"ميدان", u"ساحة", u"دوار" ]

    DETERMINANTS = [ u" ال", u"" ]

    SPACE_REDUCE = re.compile(r"\s+")
    PREFIX_REGEXP = re.compile(r"^(?P<prefix>(%s)(%s)?)\s?(?P<name>.+)" %
                                    ("|".join(APPELLATIONS),
                                     "|".join(DETERMINANTS)), re.IGNORECASE
                                                                 | re.UNICODE)

    # for IndexPageGenerator._upper_unaccent_string
    A_ACCENT = re.compile(ur"[اإآ]", re.IGNORECASE | re.UNICODE)

    def __init__(self, language, locale_path):
        self.language = str(language)
        _install_language(language, locale_path)

    def _upper_unaccent_string(self, s):
        s = self.A_ACCENT.sub("أ", s)
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

class i18n_ru_generic(i18n):
    APPELLATIONS = [ u"ул", u"бул", u"пер", u"пр", u"улица", u"бульвар", u"проезд",
                     u"проспект", u"площадь", u"сквер", u"парк" ]
    # only "ул." and "пер." are recommended shortenings, however other words can 
    # occur shortened.
    #
    # http://bit.ly/6ASISp (OSM wiki)
    #

    SPACE_REDUCE = re.compile(r"\s+")
    PREFIX_REGEXP = re.compile(r"^(?P<prefix>(%s)\.?)\s?\b(?P<name>.+)" %
                                    ("|".join(APPELLATIONS)), re.IGNORECASE
                                                                 | re.UNICODE)

    def __init__(self, language, locale_path):
        self.language = str(language)
        _install_language(language, locale_path)

    def _upper_unaccent_string(self, s):
        # usually, there are no accents in russian names, only "ё" sometimes, but
        # not as first letter
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

class i18n_nl_generic(i18n):
    #
    # Dutch streets are often named after people and include a title.
    # The title will be captured as part of the <prefix>
    #
    APPELLATIONS = [ u"St.", u"Sint", u"Ptr.", u"Pater",
                     u"Prof.", u"Professor", u"Past.", u"Pastoor",
                     u"Pr.", u"Prins", u"Prinses", u"Gen.", u"Generaal",
                     u"Mgr.", u"Monseigneur", u"Mr.", u"Meester",
                     u"Burg.", u"Burgermeester", u"Dr.", u"Dokter",
                     u"Ir.", u"Ingenieur", u"Ds.", u"Dominee", u"Deken",
                     u"Drs.",
                     # counting words before street name,
                     # e.g. "1e Walstraat" => "Walstraat (1e)"
                     u"\d+e",
                     u"" ]
    #
    # Surnames in Dutch streets named after people tend to have the middle name
    # listed after the rest of the surname,
    # e.g. "Prins van Oranjestraat" => "Oranjestraat (Prins van)"
    # Likewise, articles are captured as part of the prefix,
    # e.g. "Den Urling" => "Urling (Den)"
    #
    DETERMINANTS = [ u"\s?van der", u"\s?van den", u"\s?van de", u"\s?van",
                     u"\s?Den", u"\s?D'n", u"\s?D'", u"\s?De", u"\s?'T", u"\s?Het",
                     u"" ]
    
    SPACE_REDUCE = re.compile(r"\s+")
    PREFIX_REGEXP = re.compile(r"^(?P<prefix>(%s)(%s)?)\s?\b(?P<name>.+)" %
                                    ("|".join(APPELLATIONS),
                                     "|".join(DETERMINANTS)),
                                      re.IGNORECASE | re.UNICODE)

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
        #
        # Make sure name actually contains something,
        # the PREFIX_REGEXP.match fails on zero-length strings
        #
        if len(name) == 0:
            return name

        name = name.strip()
        name = self.SPACE_REDUCE.sub(" ", name)
        matches = self.PREFIX_REGEXP.match(name)
        #
        # If no prefix was captured, that's okay. Don't substitute
        # the name however, "<name> ()" looks silly
        #
        if matches.group('prefix'):
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
    'nl_BE.UTF-8': i18n_nl_generic,
    'nl_NL.UTF-8': i18n_nl_generic,
    'it_IT.UTF-8': i18n_it_generic,
    'it_CH.UTF-8': i18n_it_generic,
    'de_AT.UTF-8': i18n_generic,
    'de_DE.UTF-8': i18n_generic,
    'de_LU.UTF-8': i18n_generic,
    'de_CH.UTF-8': i18n_generic,
    'es_ES.UTF-8': i18n_es_generic,
    'ca_ES.UTF-8': i18n_ca_generic,
    'pt_BR.UTF-8': i18n_pt_br_generic,
    'da_DK.UTF-8': i18n_generic,
    'ar_AE.UTF-8': i18n_ar_generic,
    'ar_BH.UTF-8': i18n_ar_generic,
    'ar_DZ.UTF-8': i18n_ar_generic,
    'ar_EG.UTF-8': i18n_ar_generic,
    'ar_IN': i18n_ar_generic,
    'ar_IQ.UTF-8': i18n_ar_generic,
    'ar_JO.UTF-8': i18n_ar_generic,
    'ar_KW.UTF-8': i18n_ar_generic,
    'ar_LB.UTF-8': i18n_ar_generic,
    'ar_LY.UTF-8': i18n_ar_generic,
    'ar_MA.UTF-8': i18n_ar_generic,
    'ar_OM.UTF-8': i18n_ar_generic,
    'ar_QA.UTF-8': i18n_ar_generic,
    'ar_SA.UTF-8': i18n_ar_generic,
    'ar_SD.UTF-8': i18n_ar_generic,
    'ar_SY.UTF-8': i18n_ar_generic,
    'ar_TN.UTF-8': i18n_ar_generic,
    'ar_YE.UTF-8': i18n_ar_generic,
    'ru_RU.UTF-8': i18n_ru_generic,
}

def install_translation(locale_name, locale_path):
    """Return a new i18n class instance, depending on the specified
    locale name (eg. "fr_FR.UTF-8"). See output of "locale -a" for a
    list of system-supported locale names. When none matching, default
    class is i18n_generic"""
    language_class = language_class_map.get(locale_name, i18n_generic)
    return language_class(locale_name, locale_path)

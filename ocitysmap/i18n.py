# -*- coding: utf-8; mode: Python -*-

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

    def isrtl(self):
        return False

    def upper_unaccent_string(self, s):
        return s.upper()

class i18n_template_code_CODE(i18n):
    def __init__(self, language, locale_path):
        """Install the _() function for the chosen locale other
           object initialisation"""

        # It's important to convert to str() here because the map_language
        # value coming from the database is Unicode, but setlocale() needs a
        # non-unicode string as the locale name, otherwise it thinks it's a
        # locale tuple.
        self.language = str(language)
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

    def isrtl(self):
        return False


class i18n_fr_generic(i18n):
    APPELLATIONS = [ u"Accès", u"Allée", u"Allées", u"Autoroute", u"Avenue",
                     u"Avenues", u"Barrage",
                     u"Boulevard", u"Carrefour", u"Chaussée", u"Chemin",
                     u"Chemin rural",
                     u"Cheminement", u"Cale", u"Cales", u"Cavée", u"Cité",
                     u"Clos", u"Coin", u"Côte", u"Cour", u"Cours", u"Descente",
                     u"Degré", u"Escalier",
                     u"Escaliers", u"Esplanade", u"Funiculaire",
                     u"Giratoire", u"Hameau", u"Impasse", u"Jardin",
                     u"Jardins", u"Liaison", u"Lotissement", u"Mail",
                     u"Montée", u"Môle",
                     u"Parc", u"Passage", u"Passerelle", u"Passerelles",
                     u"Place", u"Placette", u"Pont", u"Promenade",
                     u"Petite Avenue", u"Petite Rue", u"Quai",
                     u"Rampe", u"Rang", u"Résidence", u"Rond-Point",
                     u"Route forestière", u"Route", u"Rue", u"Ruelle",
                     u"Square", u"Sente", u"Sentier", u"Sentiers", u"Terre-Plein",
                     u"Télécabine", u"Traboule", u"Traverse", u"Tunnel",
                     u"Venelle", u"Villa", u"Virage"
                   ]
    DETERMINANTS = [ u" des", u" du", u" de la", u" de l'",
                     u" de", u" d'", u" aux", u""
                   ]

    SPACE_REDUCE = re.compile(r"\s+")
    PREFIX_REGEXP = re.compile(r"^(?P<prefix>(%s)(%s)?)\s?\b(?P<name>.+)" %
                                    ("|".join(APPELLATIONS),
                                     "|".join(DETERMINANTS)), re.IGNORECASE
                                                                 | re.UNICODE)

    # for IndexPageGenerator.upper_unaccent_string
    E_ACCENT = re.compile(ur"[éèêëẽ]", re.IGNORECASE | re.UNICODE)
    I_ACCENT = re.compile(ur"[íìîïĩ]", re.IGNORECASE | re.UNICODE)
    A_ACCENT = re.compile(ur"[áàâäãæ]", re.IGNORECASE | re.UNICODE)
    O_ACCENT = re.compile(ur"[óòôöõœ]", re.IGNORECASE | re.UNICODE)
    U_ACCENT = re.compile(ur"[úùûüũ]", re.IGNORECASE | re.UNICODE)
    Y_ACCENT = re.compile(ur"[ÿ]", re.IGNORECASE | re.UNICODE)

    def __init__(self, language, locale_path):
        self.language = str(language)
        _install_language(language, locale_path)

    def upper_unaccent_string(self, s):
        s = self.E_ACCENT.sub("e", s)
        s = self.I_ACCENT.sub("i", s)
        s = self.A_ACCENT.sub("a", s)
        s = self.O_ACCENT.sub("o", s)
        s = self.U_ACCENT.sub("u", s)
        s = self.Y_ACCENT.sub("y", s)
        return s.upper()

    def language_code(self):
        return self.language

    def user_readable_street(self, name):
        name = name.strip()
        name = self.SPACE_REDUCE.sub(" ", name)
        name = self.PREFIX_REGEXP.sub(r"\g<name> (\g<prefix>)", name)
        return name

    def first_letter_equal(self, a, b):
        return self.upper_unaccent_string(a) == self.upper_unaccent_string(b)

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

    # for IndexPageGenerator.upper_unaccent_string
    E_ACCENT = re.compile(ur"[éèêëẽ]", re.IGNORECASE | re.UNICODE)
    I_ACCENT = re.compile(ur"[íìîïĩ]", re.IGNORECASE | re.UNICODE)
    A_ACCENT = re.compile(ur"[áàâäã]", re.IGNORECASE | re.UNICODE)
    O_ACCENT = re.compile(ur"[óòôöõ]", re.IGNORECASE | re.UNICODE)
    U_ACCENT = re.compile(ur"[úùûüũ]", re.IGNORECASE | re.UNICODE)

    def __init__(self, language, locale_path):
        self.language = str(language)
        _install_language(language, locale_path)

    def upper_unaccent_string(self, s):
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
        return self.upper_unaccent_string(a) == self.upper_unaccent_string(b)

class i18n_es_generic(i18n):
    APPELLATIONS = [ u"Avenida", u"Avinguda", u"Calle", u"Callejón",
            u"Calzada", u"Camino", u"Camí", u"Carrer", u"Carretera",
            u"Glorieta", u"Parque", u"Pasaje", u"Pasarela", u"Paseo", u"Plaza",
            u"Plaça", u"Privada", u"Puente", u"Ronda", u"Salida", u"Travesia" ]
    DETERMINANTS = [ u" de la", u" de los", u" de las",
                     u" dels", u" del", u" d'", u" de l'",
                     u" de", u"" ]

    SPACE_REDUCE = re.compile(r"\s+")
    PREFIX_REGEXP = re.compile(r"^(?P<prefix>(%s)(%s)?)\s?\b(?P<name>.+)" %
                                    ("|".join(APPELLATIONS),
                                     "|".join(DETERMINANTS)), re.IGNORECASE
                                                                 | re.UNICODE)

    # for IndexPageGenerator.upper_unaccent_string
    E_ACCENT = re.compile(ur"[éèêëẽ]", re.IGNORECASE | re.UNICODE)
    I_ACCENT = re.compile(ur"[íìîïĩ]", re.IGNORECASE | re.UNICODE)
    A_ACCENT = re.compile(ur"[áàâäã]", re.IGNORECASE | re.UNICODE)
    O_ACCENT = re.compile(ur"[óòôöõ]", re.IGNORECASE | re.UNICODE)
    U_ACCENT = re.compile(ur"[úùûüũ]", re.IGNORECASE | re.UNICODE)
    N_ACCENT = re.compile(ur"[ñ]", re.IGNORECASE | re.UNICODE)

    def __init__(self, language, locale_path):
        self.language = str(language)
        _install_language(language, locale_path)

    def upper_unaccent_string(self, s):
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
        return self.upper_unaccent_string(a) == self.upper_unaccent_string(b)

class i18n_ca_generic(i18n):

    APPELLATIONS = [ # Catalan
                     u"Autopista", u"Autovia", u"Avinguda",
                     u"Baixada", u"Barranc", u"Barri", u"Barriada",
                     u"Biblioteca", u"Carrer", u"Carreró", u"Carretera",
                     u"Cantonada", u"Església", u"Estació", u"Hospital",
                     u"Monestir", u"Monument", u"Museu", u"Passatge",
                     u"Passeig", u"Plaça", u"Planta", u"Polígon",
                     u"Pujada", u"Rambla", u"Ronda", u"Travessera",
                     u"Travessia", u"Urbanització", u"Via",
                     u"Avenida", u"Calle", u"Camino", u"Plaza",

                     # Spanish (being distinct from Catalan)
                     u"Acceso", u"Acequia", u"Alameda", u"Alquería",
                     u"Andador", u"Angosta", u"Apartamentos", u"Apeadero",
                     u"Arboleda", u"Arrabal", u"Arroyo", u"Autovía",
                     u"Avenida", u"Bajada", u"Balneario", u"Banda",
                     u"Barranco", u"Barranquil", u"Barrio", u"Bloque",
                     u"Brazal", u"Bulevar", u"Calle", u"Calleja",
                     u"Callejón", u"Callejuela", u"Callizo", u"Calzada",
                     u"Camino", u"Camping", u"Cantera", u"Cantina",
                     u"Cantón", u"Carrera", u"Carrero", u"Carreterín",
                     u"Carretil", u"Carril", u"Caserío", u"Chalet",
                     u"Cinturón", u"Circunvalación", u"Cobertizo",
                     u"Colonia", u"Complejo", u"Conjunto", u"Convento",
                     u"Cooperativa", u"Corral", u"Corralillo", u"Corredor",
                     u"Cortijo", u"Costanilla", u"Costera", u"Cuadra",
                     u"Cuesta", u"Dehesa", u"Demarcación", u"Diagonal",
                     u"Diseminado", u"Edificio", u"Empresa", u"Entrada",
                     u"Escalera", u"Escalinata", u"Espalda", u"Estación",
                     u"Estrada", u"Explanada", u"Extramuros", u"Extrarradio",
                     u"Fábrica", u"Galería", u"Glorieta", u"Gran Vía",
                     u"Granja", u"Hipódromo", u"Jardín", u"Ladera",
                     u"Llanura", u"Malecón", u"Mercado", u"Mirador",
                     u"Monasterio", u"Muelle", u"Núcleo", u"Palacio",
                     u"Pantano", u"Paraje", u"Parque", u"Particular",
                     u"Partida", u"Pasadizo", u"Pasaje", u"Paseo",
                     u"Paseo marítimo", u"Pasillo", u"Plaza", u"Plazoleta",
                     u"Plazuela", u"Poblado", u"Polígono", u"Polígono industrial",
                     u"Portal", u"Pórtico", u"Portillo", u"Prazuela",
                     u"Prolongación", u"Pueblo", u"Puente", u"Puerta",
                     u"Puerto", u"Punto kilométrico", u"Rampla",
                     u"Residencial", u"Ribera", u"Rincón", u"Rinconada",
                     u"Sanatorio", u"Santuario", u"Sector", u"Sendera",
                     u"Sendero", u"Subida", u"Torrente", u"Tránsito",
                     u"Transversal", u"Trasera", u"Travesía", u"Urbanización",
                     u"Vecindario", u"Vereda", u"Viaducto", u"Viviendas",

                     # French (being distinct from Catalan and Spanish)
                     u"Accès", u"Allée", u"Allées", u"Autoroute", u"Avenue", u"Barrage",
                     u"Boulevard", u"Carrefour", u"Chaussée", u"Chemin",
                     u"Cheminement", u"Cale", u"Cales", u"Cavée", u"Cité",
                     u"Clos", u"Coin", u"Côte", u"Cour", u"Cours", u"Descente",
                     u"Degré", u"Escalier",
                     u"Escaliers", u"Esplanade", u"Funiculaire",
                     u"Giratoire", u"Hameau", u"Impasse", u"Jardin",
                     u"Jardins", u"Liaison", u"Mail", u"Montée", u"Môle",
                     u"Parc", u"Passage", u"Passerelle", u"Passerelles",
                     u"Place", u"Placette", u"Pont", u"Promenade",
                     u"Petite Avenue", u"Petite Rue", u"Quai",
                     u"Rampe", u"Rang", u"Résidence", u"Rond-Point",
                     u"Route forestière", u"Route", u"Rue", u"Ruelle",
                     u"Square", u"Sente", u"Sentier", u"Sentiers", u"Terre-Plein",
                     u"Télécabine", u"Traboule", u"Traverse", u"Tunnel",
                     u"Venelle", u"Villa", u"Virage"
                   ]

    DETERMINANTS = [ # Catalan
                     u" de", u" de la", u" del", u" dels", u" d'",
                     u" de l'", u" de sa", u" de son", u" de s'",
                     u" de ses", u" d'en", u" de na", u" de n'",

                     # Spanish (being distinct from Catalan)
                     u" de las",  u" de los",

                     # French (being distinct from Catalan and Spanish)
                     u" du",
                     u""]


    DETERMINANTS = [ u" de", u" de la", u" del", u" de las",
                     u" dels", u" de los", u" d'", u" de l'", u"de sa", u"de son", u"de s'",
                     u"de ses", u"d'en", u"de na", u"de n'", u"" ]

    SPACE_REDUCE = re.compile(r"\s+")
    PREFIX_REGEXP = re.compile(r"^(?P<prefix>(%s)(%s)?)\s?\b(?P<name>.+)" %
                                    ("|".join(APPELLATIONS),
                                     "|".join(DETERMINANTS)), re.IGNORECASE
                                                                 | re.UNICODE)

    # for IndexPageGenerator.upper_unaccent_string
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

    def upper_unaccent_string(self, s):
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
        return self.upper_unaccent_string(a) == self.upper_unaccent_string(b)

class i18n_pt_br_generic(i18n):
    APPELLATIONS = [ u"Aeroporto", u"Aer.", u"Alameda", u"Al.", u"Apartamento", u"Ap.", 
                     u"Área", u"Avenida", u"Av.", u"Beco", u"Bc.", u"Bloco", u"Bl.", 
                     u"Caminho", u"Cam.", u"Campo", u"Chácara", u"Colônia",
                     u"Condomínio", u"Conjunto", u"Cj.", u"Distrito", u"Esplanada", u"Espl.", 
                     u"Estação", u"Est.", u"Estrada", u"Estr.", u"Favela", u"Fazenda",
                     u"Feira", u"Jardim", u"Jd.", u"Ladeira", u"Lago",
                     u"Lagoa", u"Largo", u"Loteamento", u"Morro", u"Núcleo",
                     u"Parque", u"Pq.", u"Passarela", u"Pátio", u"Praça", u"Pç.", u"Quadra",
                     u"Recanto", u"Residencial", u"Resid.", u"Rua", u"R.", 
                     u"Setor", u"Sítio", u"Travessa", u"Tv.", u"Trecho", u"Trevo",
                     u"Vale", u"Vereda", u"Via", u"V.", u"Viaduto", u"Viela",
                     u"Vila", u"Vl." ]
    DETERMINANTS = [ u" do", u" da", u" dos", u" das", u"" ]
    SPACE_REDUCE = re.compile(r"\s+")
    PREFIX_REGEXP = re.compile(r"^(?P<prefix>(%s)(%s)?)\s?\b(?P<name>.+)" %
                                    ("|".join(APPELLATIONS),
                                     "|".join(DETERMINANTS)), re.IGNORECASE
                                                                 | re.UNICODE)

    # for IndexPageGenerator.upper_unaccent_string
    E_ACCENT = re.compile(ur"[éèêëẽ]", re.IGNORECASE | re.UNICODE)
    I_ACCENT = re.compile(ur"[íìîïĩ]", re.IGNORECASE | re.UNICODE)
    A_ACCENT = re.compile(ur"[áàâäã]", re.IGNORECASE | re.UNICODE)
    O_ACCENT = re.compile(ur"[óòôöõ]", re.IGNORECASE | re.UNICODE)
    U_ACCENT = re.compile(ur"[úùûüũ]", re.IGNORECASE | re.UNICODE)

    def __init__(self, language, locale_path):
        self.language = str(language)
        _install_language(language, locale_path)

    def upper_unaccent_string(self, s):
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
        return self.upper_unaccent_string(a) == self.upper_unaccent_string(b)

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

    # for IndexPageGenerator.upper_unaccent_string
    A_ACCENT = re.compile(ur"[اإآ]", re.IGNORECASE | re.UNICODE)

    def __init__(self, language, locale_path):
        self.language = str(language)
        _install_language(language, locale_path)

    def upper_unaccent_string(self, s):
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
        return self.upper_unaccent_string(a) == self.upper_unaccent_string(b)

    def isrtl(self):
        return True

class i18n_ru_generic(i18n):
    # Based on list from Streetmangler:
    # https://github.com/AMDmi3/streetmangler/blob/master/lib/locales/ru.cc
    STATUS_PARTS = [
        (u"улица", [u"ул"]),
        (u"площадь", [u"пл"]),
        (u"переулок", [u"пер", u"пер-к"]),
        (u"проезд", [u"пр-д"]),
        (u"шоссе", [u"ш"]),
        (u"бульвар", [u"бул", u"б-р"]),
        (u"тупик", [u"туп"]),
        (u"набережная", [u"наб"]),
        (u"проспект", [u"просп", u"пр-кт", u"пр-т"]),
        (u"линия", []),
        (u"аллея", []),
        (u"метромост", []),
        (u"мост", []),
        (u"просек", []),
        (u"просека", []),
        (u"путепровод", []),
        (u"тракт", [u"тр-т", u"тр"]),
        (u"тропа", []),
        (u"туннель", []),
        (u"тоннель", []),
        (u"эстакада", [u"эст"]),
        (u"дорога", [u"дор"]),
        (u"спуск", []),
        (u"подход", []),
        (u"подъезд", []),
        (u"съезд", []),
        (u"заезд", []),
        (u"разъезд", []),
        (u"слобода", []),
        (u"район", [u"р-н"]),
        (u"микрорайон", [u"мкр-н", u"мк-н", u"мкр", u"мкрн"]),
        (u"посёлок", [u"поселок", u"пос"]),
        (u"деревня", [u"дер", u"д"]),
        (u"квартал", [u"кв-л", u"кв"]),
    ]

    # matches one or more spaces
    SPACE_REDUCE = re.compile(r"\s+")
    # mapping from status abbreviations (w/o '.') to full status names
    STATUS_PARTS_ABBREV_MAPPING = dict((f, t) for t, ff in STATUS_PARTS for f in ff)
    # set of full (not abbreviated) status parts
    STATUS_PARTS_FULL = set((x[0] for x in STATUS_PARTS))
    # matches any abbreviated status part with optional '.'
    STATUS_ABBREV_REGEXP = re.compile(r"\b(%s)\.?(?=\W|$)" % u"|".join(
        f for t, ff in STATUS_PARTS for f in ff), re.IGNORECASE | re.UNICODE)
    # matches status prefixes at start of name used to move prefixes to the end
    PREFIX_REGEXP = re.compile(
        ur"^(?P<num_prefix>\d+-?(ы?й|я))?\s*(?P<prefix>(%s)\.?)?\s*(?P<name>.+)?" %
        (u"|".join(f for f,t in STATUS_PARTS)), re.IGNORECASE | re.UNICODE)

    def __init__(self, language, locale_path):
        self.language = str(language)
        _install_language(language, locale_path)

    def upper_unaccent_string(self, s):
        # usually, there are no accents in russian names, only "ё" sometimes, but
        # not as first letter
        return s.upper()

    def language_code(self):
        return self.language

    @staticmethod
    def _rewrite_street_parts(matches):
        if (matches.group('num_prefix') is None and
            matches.group('prefix') is not None and
            matches.group('name') in i18n_ru_generic.STATUS_PARTS_FULL):
            return matches.group(0)
        elif matches.group('num_prefix') is None and matches.group('prefix') is None:
            return matches.group(0)
        elif matches.group('name') is None:
            return matches.group(0)
        else:
            #print matches.group('num_prefix', 'prefix', 'name')
            return ", ".join((matches.group('name'),
                " ". join(s.lower()
                    for s in matches.group('prefix', 'num_prefix')
                    if s is not None)
                ))

    def user_readable_street(self, name):
        name = name.strip()
        name = self.SPACE_REDUCE.sub(" ", name)
        # Normalize abbreviations
        name = self.STATUS_ABBREV_REGEXP.sub(lambda m:
                self.STATUS_PARTS_ABBREV_MAPPING.get(
                    m.group(0).replace('.', ''), m.group(0)),
            name)
        # Move prefixed status parts to the end for sorting
        name = self.PREFIX_REGEXP.sub(self._rewrite_street_parts, name)
        # TODO: move "малая", "большая" after name but before status
        return name

    def first_letter_equal(self, a, b):
        return self.upper_unaccent_string(a) == self.upper_unaccent_string(b)

class i18n_be_generic(i18n):
    # Based on code for Russian language:
    STATUS_PARTS = [
        (u"вуліца", [u"вул"]),
        (u"плошча", [u"пл"]),
        (u"завулак", [u"зав", u"зав-к"]),
        (u"праезд", [u"пр-д"]),
        (u"шаша", [u"ш"]),
        (u"бульвар", [u"бул", u"б-р"]),
        (u"тупік", [u"туп"]),
        (u"набярэжная", [u"наб"]),
        (u"праспект", [u"праспект", u"пр-кт", u"пр-т"]),
        (u"алея", []),
        (u"мост", []),
        (u"парк", []),
        (u"тракт", [u"тр-т", u"тр"]),
        (u"раён", [u"р-н"]),
        (u"мікрараён", [u"мкр-н", u"мк-н", u"мкр", u"мкрн"]),
        (u"пасёлак", [u"пас"]),
        (u"вёска", [ u"в"]),
        (u"квартал", [u"кв-л", u"кв"]),
    ]

    # matches one or more spaces
    SPACE_REDUCE = re.compile(r"\s+")
    # mapping from status abbreviations (w/o '.') to full status names
    STATUS_PARTS_ABBREV_MAPPING = dict((f, t) for t, ff in STATUS_PARTS for f in ff)
    # set of full (not abbreviated) status parts
    STATUS_PARTS_FULL = set((x[0] for x in STATUS_PARTS))
    # matches any abbreviated status part with optional '.'
    STATUS_ABBREV_REGEXP = re.compile(r"\b(%s)\.?(?=\W|$)" % u"|".join(
        f for t, ff in STATUS_PARTS for f in ff), re.IGNORECASE | re.UNICODE)
    # matches status prefixes at start of name used to move prefixes to the end
    PREFIX_REGEXP = re.compile(
        ur"^(?P<num_prefix>\d+-?(і|ы|я))?\s*(?P<prefix>(%s)\.?)?\s*(?P<name>.+)?" %
        (u"|".join(f for f,t in STATUS_PARTS)), re.IGNORECASE | re.UNICODE)

    def __init__(self, language, locale_path):
        self.language = str(language)
        _install_language(language, locale_path)

    def upper_unaccent_string(self, s):
        return s.upper()

    def language_code(self):
        return self.language

    @staticmethod
    def _rewrite_street_parts(matches):
        if (matches.group('num_prefix') is None and
            matches.group('prefix') is not None and
            matches.group('name') in i18n_be_generic.STATUS_PARTS_FULL):
            return matches.group(0)
        elif matches.group('num_prefix') is None and matches.group('prefix') is None:
            return matches.group(0)
        elif matches.group('name') is None:
            return matches.group(0)
        else:
            #print matches.group('num_prefix', 'prefix', 'name')
            return ", ".join((matches.group('name'),
                " ". join(s.lower()
                    for s in matches.group('num_prefix', 'prefix')
                    if s is not None)
                ))

    def user_readable_street(self, name):
        name = name.strip()
        name = self.SPACE_REDUCE.sub(" ", name)
        # Normalize abbreviations
        name = self.STATUS_ABBREV_REGEXP.sub(lambda m:
                self.STATUS_PARTS_ABBREV_MAPPING.get(
                    m.group(0).replace('.', ''), m.group(0)),
            name)
        # Move prefixed status parts to the end for sorting
        name = self.PREFIX_REGEXP.sub(self._rewrite_street_parts, name)
        # TODO: move "малая", "большая" after name but before status
        return name

    def first_letter_equal(self, a, b):
        return self.upper_unaccent_string(a) == self.upper_unaccent_string(b)

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
                     u"Drs.", u"Maj.", u"Majoor",
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

    # for IndexPageGenerator.upper_unaccent_string
    E_ACCENT = re.compile(ur"[éèêëẽ]", re.IGNORECASE | re.UNICODE)
    I_ACCENT = re.compile(ur"[íìîïĩ]", re.IGNORECASE | re.UNICODE)
    A_ACCENT = re.compile(ur"[áàâäã]", re.IGNORECASE | re.UNICODE)
    O_ACCENT = re.compile(ur"[óòôöõ]", re.IGNORECASE | re.UNICODE)
    U_ACCENT = re.compile(ur"[úùûüũ]", re.IGNORECASE | re.UNICODE)

    def __init__(self, language, locale_path):
        self.language = str(language)
        _install_language(language, locale_path)

    def upper_unaccent_string(self, s):
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
        if matches == None:
            return name

        if matches.group('prefix'):
            name = self.PREFIX_REGEXP.sub(r"\g<name> (\g<prefix>)", name)
        return name

    def first_letter_equal(self, a, b):
        return self.upper_unaccent_string(a) == self.upper_unaccent_string(b)

class i18n_hr_HR(i18n):
    # for upper_unaccent_string
    C_ACCENT = re.compile(ur"[ćč]", re.IGNORECASE | re.UNICODE)
    D_ACCENT = re.compile(ur"đ|dž", re.IGNORECASE | re.UNICODE)
    N_ACCENT = re.compile(ur"nj", re.IGNORECASE | re.UNICODE)
    L_ACCENT = re.compile(ur"lj", re.IGNORECASE | re.UNICODE)
    S_ACCENT = re.compile(ur"š", re.IGNORECASE | re.UNICODE)
    Z_ACCENT = re.compile(ur"ž", re.IGNORECASE | re.UNICODE)

    def upper_unaccent_string(self, s):
        s = self.C_ACCENT.sub("c", s)
        s = self.D_ACCENT.sub("d", s)
        s = self.N_ACCENT.sub("n", s)
        s = self.L_ACCENT.sub("l", s)
        s = self.S_ACCENT.sub("s", s)
        s = self.Z_ACCENT.sub("z", s)
        return s.upper()

    def __init__(self, language, locale_path):
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

    ## FIXME: only first letter does not work for Croatian digraphs (dž, lj, nj)
    def first_letter_equal(self, a, b):
        """returns True if the letters a and b are equal in the map index,
           e.g. É and E are equals in French map index"""
        return self.upper_unaccent_string(a) == self.upper_unaccent_string(b)

class i18n_pl_generic(i18n):

    APPELLATIONS = [ u"Dr.", u"Doktora", u"Ks.", u"Księdza",
                     u"Generała", u"Gen.",
                     u"Aleja", u"Plac", u"Pl.",
                     u"Rondo", u"rondo", u"Profesora",
                     u"Prof.",
                     u"" ]

    DETERMINANTS = [ u"\s?im.", u"\s?imienia", u"\s?pw.",
                     u"" ]

    SPACE_REDUCE = re.compile(r"\s+")
    PREFIX_REGEXP = re.compile(r"^(?P<prefix>(%s)(%s)?)\s?\b(?P<name>.+)" %
                                    ("|".join(APPELLATIONS),
                                     "|".join(DETERMINANTS)),
                                      re.IGNORECASE | re.UNICODE)


    def __init__(self, language, locale_path):
        self.language = str(language)
        _install_language(language, locale_path)

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
        if matches == None:
            return name

        if matches.group('prefix'):
            name = self.PREFIX_REGEXP.sub(r"\g<name>, \g<prefix>", name)
        return name

    def first_letter_equal(self, a, b):
        return a == b

class i18n_tr_generic(i18n):
    APPELLATIONS = [ u"Sokak", u"Sokağı" ]
    DETERMINANTS = []
    SPACE_REDUCE = re.compile(r"\s+")
    PREFIX_REGEXP = re.compile(r"^(?P<prefix>(%s)(%s)?)\s?\b(?P<name>.+)" %
                                    ("|".join(APPELLATIONS),
                                     "|".join(DETERMINANTS)), re.IGNORECASE
                                                                 | re.UNICODE)

    def __init__(self, language, locale_path):
        self.language = str(language)
        _install_language(language, locale_path)

    def upper_unaccent_string(self, s):
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
        name = self.PREFIX_REGEXP.sub(r"\g<name> (\g<prefix>)", name)
        return name

    def first_letter_equal(self, a, b):
        return self.upper_unaccent_string(a) == self.upper_unaccent_string(b)

class i18n_de_generic(i18n):
    #
    # German streets are often named after people and include a title.
    # The title will be captured as part of the <prefix>
	# Covering airport names and "New"/"Old" as prefixes as well
    #
    APPELLATIONS = [ u"Alte", u"Alter", u"Doktor", u"Dr.",
                     u"Flughafen", u"Flugplatz", u"Gen.,", u"General",
                     u"Neue", u"Neuer", u"Platz",
                     u"Prinz", u"Prinzessin", u"Prof.",
                     u"Professor" ]
    #
    # Surnames in german streets named after people tend to have the middle name
    # listed after the rest of the surname,
    # e.g. "Platz der deutschen Einheit" => "deutschen Einheit (Platz der)"
    # Likewise, articles are captured as part of the prefix,
    # e.g. "An der Märchenwiese" => "Märchenwiese (An der)"
    #
    DETERMINANTS = [ u"\s?An den", u"\s?An der", u"\s?Am",
                     u"\s?Auf den" , u"\s?Auf der"
                     u" an", u" des", u" der", u" von", u" vor"]

    SPACE_REDUCE = re.compile(r"\s+")
    PREFIX_REGEXP = re.compile(r"^(?P<prefix>(%s)(%s)?)\s?\b(?P<name>.+)" %
                                    ("|".join(APPELLATIONS),
                                     "|".join(DETERMINANTS)), re.IGNORECASE
                                                                 | re.UNICODE)

    # for IndexPageGenerator.upper_unaccent_string
    E_ACCENT = re.compile(ur"[éèêëẽ]", re.IGNORECASE | re.UNICODE)
    I_ACCENT = re.compile(ur"[íìîïĩ]", re.IGNORECASE | re.UNICODE)
    A_ACCENT = re.compile(ur"[áàâäã]", re.IGNORECASE | re.UNICODE)
    O_ACCENT = re.compile(ur"[óòôöõ]", re.IGNORECASE | re.UNICODE)
    U_ACCENT = re.compile(ur"[úùûüũ]", re.IGNORECASE | re.UNICODE)

    def __init__(self, language, locale_path):
        self.language = str(language)
        _install_language(language, locale_path)

    def upper_unaccent_string(self, s):
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
        name = self.PREFIX_REGEXP.sub(r"\g<name> (\g<prefix>)", name)
        return name

    def first_letter_equal(self, a, b):
        return self.upper_unaccent_string(a) == self.upper_unaccent_string(b)

class i18n_ast_generic(i18n):

    APPELLATIONS = [ # Asturian
                     u"Accesu", u"Autopista", u"Autovia", u"Avenida",
                     u"Baxada", u"Barrancu", u"Barriu", u"Barriada",
                     u"Biblioteca", u"Cai", u"Caleya",
                     u"Calzada", u"Camín", u"Carretera", u"Cuesta",
                     u"Estación", u"Hospital", u"Iglesia", u"Monasteriu",
                     u"Monumentu", u"Muelle", u"Muséu",
                     u"Palaciu", u"Parque", u"Pasadizu", u"Pasaxe",
                     u"Paséu", u"Planta", u"Plaza", u"Polígonu",
                     u"Ronda", u"Travesía", u"Urbanización", u"Via",
                     u"Xardín", u"Xardinos",

                     # Spanish (different from Asturian)
                     u"Acceso", u"Acequia", u"Alameda", u"Alquería",
                     u"Andador", u"Angosta", u"Apartamentos", u"Apeadero",
                     u"Arboleda", u"Arrabal", u"Arroyo", u"Autovía",
                     u"Bajada", u"Balneario", u"Banda",
                     u"Barranco", u"Barranquil", u"Barrio", u"Bloque",
                     u"Brazal", u"Bulevar", u"Calle", u"Calleja",
                     u"Callejón", u"Callejuela", u"Callizo",
                     u"Camino", u"Camping", u"Cantera", u"Cantina",
                     u"Cantón", u"Carrera", u"Carrero", u"Carreterín",
                     u"Carretil", u"Carril", u"Caserío", u"Chalet",
                     u"Cinturón", u"Circunvalación", u"Cobertizo",
                     u"Colonia", u"Complejo", u"Conjunto", u"Convento",
                     u"Cooperativa", u"Corral", u"Corralillo", u"Corredor",
                     u"Cortijo", u"Costanilla", u"Costera", u"Cuadra",
                     u"Dehesa", u"Demarcación", u"Diagonal",
                     u"Diseminado", u"Edificio", u"Empresa", u"Entrada",
                     u"Escalera", u"Escalinata", u"Espalda", u"Estación",
                     u"Estrada", u"Explanada", u"Extramuros", u"Extrarradio",
                     u"Fábrica", u"Galería", u"Glorieta", u"Gran Vía",
                     u"Granja", u"Hipódromo", u"Jardín", u"Ladera",
                     u"Llanura", u"Malecón", u"Mercado", u"Mirador",
                     u"Monasterio", u"Núcleo", u"Palacio",
                     u"Pantano", u"Paraje", u"Particular",
                     u"Partida", u"Pasadizo", u"Pasaje", u"Paseo",
                     u"Paseo marítimo", u"Pasillo", u"Plaza", u"Plazoleta",
                     u"Plazuela", u"Poblado", u"Polígono", u"Polígono industrial",
                     u"Portal", u"Pórtico", u"Portillo", u"Prazuela",
                     u"Prolongación", u"Pueblo", u"Puente", u"Puerta",
                     u"Puerto", u"Punto kilométrico", u"Rampla",
                     u"Residencial", u"Ribera", u"Rincón", u"Rinconada",
                     u"Sanatorio", u"Santuario", u"Sector", u"Sendera",
                     u"Sendero", u"Subida", u"Torrente", u"Tránsito",
                     u"Transversal", u"Trasera", u"Travesía", u"Urbanización",
                     u"Vecindario", u"Vereda", u"Viaducto", u"Viviendas",
                   ]

    DETERMINANTS = [ # Asturian
                     u" de", u" de la", u" del", u" de les", u" d'",
                     u" de los", u" de l'",

                     # Spanish (different from Asturian)
                     u" de las",
                     u""]


    DETERMINANTS = [ u" de", u" de la", u" del", u" de les",
                     u" de los", u" de las", u" d'", u" de l'", u"" ]

    SPACE_REDUCE = re.compile(r"\s+")
    PREFIX_REGEXP = re.compile(r"^(?P<prefix>(%s)(%s)?)\s?\b(?P<name>.+)" %
                                    ("|".join(APPELLATIONS),
                                     "|".join(DETERMINANTS)), re.IGNORECASE
                                                                 | re.UNICODE)

    # for IndexPageGenerator.upper_unaccent_string
    E_ACCENT = re.compile(ur"[éèêëẽ]", re.IGNORECASE | re.UNICODE)
    I_ACCENT = re.compile(ur"[íìîïĩ]", re.IGNORECASE | re.UNICODE)
    A_ACCENT = re.compile(ur"[áàâäã]", re.IGNORECASE | re.UNICODE)
    O_ACCENT = re.compile(ur"[óòôöõ]", re.IGNORECASE | re.UNICODE)
    U_ACCENT = re.compile(ur"[úùûüũ]", re.IGNORECASE | re.UNICODE)
    N_ACCENT = re.compile(ur"[ñ]", re.IGNORECASE | re.UNICODE)
    H_ACCENT = re.compile(ur"[ḥ]", re.IGNORECASE | re.UNICODE)
    L_ACCENT = re.compile(ur"[ḷ]", re.IGNORECASE | re.UNICODE)

    def __init__(self, language, locale_path):
        self.language = str(language)
        _install_language(language, locale_path)

    def upper_unaccent_string(self, s):
        s = self.E_ACCENT.sub("e", s)
        s = self.I_ACCENT.sub("i", s)
        s = self.A_ACCENT.sub("a", s)
        s = self.O_ACCENT.sub("o", s)
        s = self.U_ACCENT.sub("u", s)
        s = self.N_ACCENT.sub("n", s)
        s = self.H_ACCENT.sub("h", s)
        s = self.L_ACCENT.sub("l", s)
        return s.upper()

    def language_code(self):
        return self.language

    def user_readable_street(self, name):
        name = name.strip()
        name = self.SPACE_REDUCE.sub(" ", name)
        name = self.PREFIX_REGEXP.sub(r"\g<name> (\g<prefix>)", name)
        return name

    def first_letter_equal(self, a, b):
        return self.upper_unaccent_string(a) == self.upper_unaccent_string(b)

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
    'nl_BE.UTF-8': i18n_nl_generic,
    'nl_NL.UTF-8': i18n_nl_generic,
    'it_IT.UTF-8': i18n_it_generic,
    'it_CH.UTF-8': i18n_it_generic,
    'de_AT.UTF-8': i18n_de_generic,
    'de_BE.UTF-8': i18n_de_generic,
    'de_DE.UTF-8': i18n_de_generic,
    'de_LU.UTF-8': i18n_de_generic,
    'de_CH.UTF-8': i18n_de_generic,
    'es_ES.UTF-8': i18n_es_generic,
    'es_AR.UTF-8': i18n_es_generic,
    'es_BO.UTF-8': i18n_es_generic,
    'es_CL.UTF-8': i18n_es_generic,
    'es_CR.UTF-8': i18n_es_generic,
    'es_DO.UTF-8': i18n_es_generic,
    'es_EC.UTF-8': i18n_es_generic,
    'es_SV.UTF-8': i18n_es_generic,
    'es_GT.UTF-8': i18n_es_generic,
    'es_HN.UTF-8': i18n_es_generic,
    'es_MX.UTF-8': i18n_es_generic,
    'es_NI.UTF-8': i18n_es_generic,
    'es_PA.UTF-8': i18n_es_generic,
    'es_PY.UTF-8': i18n_es_generic,
    'es_PE.UTF-8': i18n_es_generic,
    'es_PR.UTF-8': i18n_es_generic,
    'es_US.UTF-8': i18n_es_generic,
    'es_UY.UTF-8': i18n_es_generic,
    'es_VE.UTF-8': i18n_es_generic,
    'ca_ES.UTF-8': i18n_ca_generic,
    'ca_AD.UTF-8': i18n_ca_generic,
    'ca_FR.UTF-8': i18n_ca_generic,
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
    'hr_HR.UTF-8': i18n_hr_HR,
    'ru_RU.UTF-8': i18n_ru_generic,
    'pl_PL.UTF-8': i18n_pl_generic,
    'nb_NO.UTF-8': i18n_generic,
    'nn_NO.UTF-8': i18n_generic,
    'tr_TR.UTF-8': i18n_tr_generic,
    'ast_ES.UTF-8': i18n_ast_generic,
    'sk_SK.UTF-8': i18n_generic,
    'be_BY.UTF-8': i18n_be_generic,
}

def install_translation(locale_name, locale_path):
    """Return a new i18n class instance, depending on the specified
    locale name (eg. "fr_FR.UTF-8"). See output of "locale -a" for a
    list of system-supported locale names. When none matching, default
    class is i18n_generic"""
    language_class = language_class_map.get(locale_name, i18n_generic)
    return language_class(locale_name, locale_path)

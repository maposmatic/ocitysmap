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

"""OCitySMap 2.
"""

__author__ = 'The MapOSMatic developers'
__version__ = '0.2'

class RenderingConfiguration:
    """
    The RenderingConfiguration class encapsulate all the information concerning
    a rendering request. This data is used by the layout renderer, in
    conjonction with its rendering mode (defined by its implementation), to
    produce the map.
    """

    def __init__(self):
        self.title           = None # str
        self.osmid           = None # None / int (shading + city name)
        self.bounding_box    = None # bbox (always)
        self.language        = None # str (locale)
        self.stylesheet      = None # Obj Stylesheet
        self.paper_width_cm  = None
        self.paper_height_cm = None


class Stylesheet:
    def __init__(self):
        self.name        = None # str
        self.description = None # str
        self.path        = None # str

class StreetIndex:
    """
    The StreetIndex class encapsulate all the logic related to the querying and
    rendering of the street index.
    """

    DEFAULT_GRID_SIZE_METERS = 500

    def __init__(self, osmid, bounding_box, language):
        self._osmid = osmid
        self._bbox = bounding_box
        self._language = language

        # TODO: infer a better (smaller) grid size when the bounding box
        # is smaller.
        self._grid_size = DEFAULT_GRID_SIZE_METERS

    def get_grid_size(self):
        """Returns the used grid size."""
        return self._grid_size

    def render(self, surface, x, y, w, h):
        """Render the street and amenities index at the given (x,y) coordinates
        into the provided Cairo surface. The index must not be larger than the
        provided width and height (in pixels).

        Args:
            x (int): horizontal origin position, in pixels.
            y (int): vertical origin position, in pixels.
            w (int): maximum usable width for the index, in pixels.
            h (int): maximum usable height for the index, in pixels.
        """
        ctx = cairo.Context(surface)
        ctx.move_to(x, y)

        # TODO: render index into ctx

        return surface

    def as_csv(self, fobj):
        """Saves the street index as CSV to the provided file object."""

        # TODO: write to CSV

        raise NotImplementedError

    def _get_streets(self):
        raise NotImplementedError

    def _get_amenities(self):
        raise NotImplementedError

class OCitySMap:
    def __init__(self, config_file):
        # Create the registries from config file
        pass

    def get_all_style_configurations(self):
        """Returns the list of all available stylesheet configurations (list of
        Stylesheet objects)."""
        pass

    def get_all_renderers(self):
        """Returns the list of all available layout renderers (list of Renderer
        objects)."""
        pass

    def render(self, config, renderer, output_formats, file_prefix):
        """Renders a job with the given rendering configuration, using the
        provided renderer, to the given output formats.

        Args:
            config (RenderingConfiguration): the rendering configuration
                object.
            renderer (Renderer): the layout renderer to use for this rendering.
            output_formats (list): a list of output formats to render to, from
                the list of supported output formats (pdf, svgz, etc.).
            file_prefix (string): filename prefix for all output files.
        """

        # TODO: instanciate Cairo surface
        renderer.render(config, surface)
        # TODO: save surface to all output formats


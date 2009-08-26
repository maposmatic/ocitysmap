
import math


EARTH_RADIUS = 6370986 # meters


class BoundingBox:
    def __init__(self, lat1, long1, lat2, long2):
        (self._lat1, self._long1) = float(lat1), float(long1)
        (self._lat2, self._long2) = float(lat2), float(long2)

        # make sure lat1/long1 is the upper left, and the others the btm right
        if (self._lat1 < self._lat2):
            self._lat1, self._lat2 = self._lat2, self._lat1
        if (self._long1 > self._long2):
            self._long1, self._long2 = self._long2, self._long1

    @staticmethod
    def parse(points):
        (lat1, long1) = points[0].split(',')
        (lat2, long2) = points[1].split(',')
        return BoundingBox(lat1, long1, lat2, long2)

    def get_top_left(self):
        return (self._lat1, self._long1)

    def get_bottom_right(self):
        return (self._lat2, self._long2)

    def ptstr(self, point):
        return '%.4f,%.4f' % (point[0], point[1])

    def __str__(self):
        return '(%s %s)' % (self.ptstr(self.get_top_left()),
                            self.ptstr(self.get_bottom_right()))

    def spheric_sizes(self):
        """Metric distances at the bounding box top latitude.
        Returns the tuple (metric_size_lat, metric_size_long)
        """
        delta_lat = abs(self._lat1 - self._lat2)
        delta_long = abs(self._long1 - self._long2)
        radius_lat = EARTH_RADIUS * math.cos(math.radians(self._lat1))
        return (EARTH_RADIUS * math.radians(delta_lat),
                radius_lat * math.radians(delta_long))

    def create_expanded(self, dlat, dlong):
        """Return a new bbox of the same size + dlat/dlong added on the sides"""
        return BoundingBox(self._lat1+dlat, self._long1 - dlong,
                           self._lat2-dlat, self._long2 + dlong)

    def get_pixel_size_for_zoom_factor(self, zoom = 17):
        """Return the size in pixels (tuple width,height) needed to
        render the bounding box at the given zoom factor"""
        delta_lat  = abs(self._lat1 - self._lat2)
        delta_long = abs(self._long1 - self._long2)
        # 2^zoom tiles (1 tile = 256 pix) for the whole earth
        pix_x = delta_long * (2 ** (zoom + 8)) / 360
        pix_y = delta_lat  * (2 ** (zoom + 8)) / 180 # 237 ?????
        return (int(math.ceil(pix_x)), int(math.ceil(pix_y)))

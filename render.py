#!/usr/bin/env python
# -*- coding: utf-8; mode: Python -*-

__version__ = '0.1'

import logging
import optparse
import sys

import ocitysmap

l = logging.getLogger('main')

def main():
    usage = '%prog [options] <cityname> [top-left top-right bottom-right bottom-left]'
    parser = optparse.OptionParser(usage=usage,
                                   version='%%prog %s' % __version__)
    parser.add_option('-o', '--output', dest='output', metavar='FILE',
                      default='citymap.svg',
                      help='Specify the output file name (defaults '
                           'to citymap.svg.')
    parser.add_option('-z', '--zoom', dest='zooms', action='append',
                      nargs=5, metavar='NAME BBOX',
                      help='Specify a zoomed section by its named '
                           'bounding box.')

    (options, args) = parser.parse_args()
    if not (len(args) == 1 or len(args) == 5):
        parser.print_help()
        return 1

    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    l.info('OCitySMap v%s starting...' % __version__)

    try:
        renderer = ocitysmap.OCitySMap(args[0], tuple(args[1:5]),
                                       options.zooms)
    except ValueError, e:
        l.error('ValueError: %s!', e)
        return 1
    except ocitysmap.BaseOCitySMapError, e:
        l.error(e)
        return 2
    except KeyboardInterrupt:
        sys.stderr.write(' Aborting.\n')

    return 0

if __name__ == '__main__':
    sys.exit(main())

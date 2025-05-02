#!/Users/hiddemakimei/Desktop/git/vu/IGS/igs/venv/bin/python3.12

import sys

from osgeo.gdal import deprecation_warn

# import osgeo_utils.gdalattachpct as a convenience to use as a script
from osgeo_utils.gdalattachpct import *  # noqa
from osgeo_utils.gdalattachpct import main

deprecation_warn("gdalattachpct")
sys.exit(main(sys.argv))

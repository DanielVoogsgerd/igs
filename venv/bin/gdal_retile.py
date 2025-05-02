#!/Users/hiddemakimei/Desktop/git/vu/IGS/igs/venv/bin/python3.12

import sys

from osgeo.gdal import deprecation_warn

# import osgeo_utils.gdal_retile as a convenience to use as a script
from osgeo_utils.gdal_retile import *  # noqa
from osgeo_utils.gdal_retile import main

deprecation_warn("gdal_retile")
sys.exit(main(sys.argv))

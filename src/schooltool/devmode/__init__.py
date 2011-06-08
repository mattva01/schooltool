# Make a package

# Due to a different structure, the apidoc BASEDIR is no good.
import schooltool.app
from os.path import dirname
try:
    from zope.app.apidoc import utilities
    utilities.BASEDIR = dirname(dirname(dirname(dirname(schooltool.app.__file__))))
except ImportError:
    pass

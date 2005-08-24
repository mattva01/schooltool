# Just for BBB:
from zope.deprecation import deprecated

from schooltool.app.security import \
     SchoolToolAuthenticationUtility as SchoolBellAuthenticationUtility
deprecated(('SchoolBellAuthenticationUtility',),
           'This class has moved to schooltool.app.security. '
           'The reference will be gone in 0.15')

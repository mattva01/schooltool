# Just for BBB:
from zope.deprecation import deprecated

from schooltool.relationship.uri import URIObject
deprecated(('URIObject',),
           'This class has moved to schooltool.relationship.uri. '
           'The reference will be gone in 0.15')

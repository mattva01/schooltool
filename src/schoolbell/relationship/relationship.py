# Just for BBB:
from zope.deprecation import deprecated

from schooltool.relationship.relationship import LinkSet, Link
deprecated(('LinkSet', 'Link'),
           'This class has moved to schooltool.relationship.relationship. '
           'The reference will be gone in 0.15')

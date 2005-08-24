##############################################################################
# BBB: Make sure the old data object references are still there.
from zope.deprecation import deprecated

from schooltool.app.cal import CalendarEvent, Calendar
deprecated(('CalendarEvent', 'Calendar'),
           'This class has moved to schooltool.app.cal '
           'The reference will be gone in 0.15')

##############################################################################

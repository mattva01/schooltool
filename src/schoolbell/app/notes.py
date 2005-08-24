##############################################################################
# BBB: Make sure the old data object references are still there.
from zope.deprecation import deprecated

from schooltool.note.note import Notes, Note
deprecated(('Notes', 'Note'),
           'This class has moved to schooltool.note.note. '
           'The reference will be gone in 0.15')

##############################################################################

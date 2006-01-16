#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""Activity Category

$Id$
"""
__docformat__ = 'reStructuredText'

import optionstorage
from optionstorage import vocabulary, interfaces
from schooltool.app import app
from schooltool import SchoolToolMessage as _

VOCABULARY_NAME = 'schooltool.gradebook.activities'

class CategoryVocabulary(optionstorage.vocabulary.OptionStorageVocabulary):
    """Activity Categories Vocabulary"""

    def __init__(self, context=None, name=None):
        st = app.getSchoolToolApplication()
        if name is None:
            name = VOCABULARY_NAME
        self.dict = optionstorage.queryOptionStorage(st, name)
        # TODO: Only support English for now.
        self.language = 'en'
        self.defaultlanguage = self.dict.getDefaultLanguage()


def getCategories(app):
    """Return the option dictionary for the categories."""
    storage = optionstorage.interfaces.IOptionStorage(app)
    if VOCABULARY_NAME not in storage:
        storage[VOCABULARY_NAME] = optionstorage.OptionDict()
    return storage[VOCABULARY_NAME]


def addDefaultCategoriesToApplication(event):
    dict = getCategories(event.object)
    dict.addValue('assignment', 'en', _('Assignment'))
    dict.addValue('essay', 'en', _('Essay'))
    dict.addValue('exam', 'en', _('Exam'))
    dict.addValue('homework', 'en', _('Homework'))
    dict.addValue('journal', 'en', _('Journal'))
    dict.addValue('lab', 'en', _('Lab'))
    dict.addValue('presentation', 'en', _('Presentation'))
    dict.addValue('project', 'en', _('Project'))
    dict.setDefaultLanguage('en')
    dict.setDefaultKey('assignment')

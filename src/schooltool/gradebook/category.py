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

from zope.interface import classProvides
from zope.schema.interfaces import IVocabularyFactory

import z3c.optionstorage
from z3c.optionstorage import vocabulary, interfaces
from schooltool.app import app
from schooltool import SchoolToolMessage as _

VOCABULARY_NAME = 'schooltool.gradebook.activities'

class CategoryVocabulary(z3c.optionstorage.vocabulary.OptionStorageVocabulary):
    """Activity Categories Vocabulary"""

    classProvides(IVocabularyFactory)

    def __init__(self, context=None, name=None):
        st = app.getSchoolToolApplication()
        if name is None:
            name = VOCABULARY_NAME
        self.dict = z3c.optionstorage.queryOptionStorage(st, name)
        # TODO: Only support English for now.
        self.language = 'en'
        self.defaultlanguage = self.dict.getDefaultLanguage()


def getCategories(app):
    """Return the option dictionary for the categories."""
    storage = z3c.optionstorage.interfaces.IOptionStorage(app)
    if VOCABULARY_NAME not in storage:
        storage[VOCABULARY_NAME] = z3c.optionstorage.OptionDict()
    return storage[VOCABULARY_NAME]

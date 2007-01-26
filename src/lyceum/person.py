from zope.interface import implements
from zope.interface import directlyProvides

from zc.table.interfaces import ISortableColumn
from zc.table.column import GetterColumn

from schooltool.person.person import Person
from schooltool.person.interfaces import IPersonFactory
from schooltool.skin.table import LocaleAwareGetterColumn


class LyceumPerson(Person):
    pass


class PersonFactoryUtility(object):

    implements(IPersonFactory)

    def columns(self):
        title = LocaleAwareGetterColumn(
            name='title',
            title=_(u'Full Name'),
            getter=lambda i, f: i.title,
            subsort=True)
        directlyProvides(title, ISortableColumn)

        return [title]

    def sortOn(self):
        return (("title", False),)

    def groupBy(self):
        return (("grade", False),)

    def __call__(self, *args, **kw):
        result = LyceumPerson(*args, **kw)
        return result

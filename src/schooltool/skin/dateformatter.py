from zope.publisher.browser import BrowserView
from zope.interface import implements

from zope.i18n.locales import Locale
from zope.i18n.locales import LocaleIdentity

from schooltool.skin.interfaces import IDateFormatter

class LocaleLookupMixin(object):
    def getLocale(self):
        if not hasattr(self, 'request'):
            raise NotImplementedError("LocaleLookupMixin need to be applied on a view")

        if self.request.locale.id.language is None:
        # if we dont have any locale defined in the request
        # we set default to english
            id = LocaleIdentity('en', territory='US')
            locale = Locale(id)
        else:
            if hasattr(self.request, 'locale'):
                locale = self.request.locale

        return locale


class DateFormatterFullView( BrowserView, LocaleLookupMixin ):
    implements(IDateFormatter)

    def __call__(self):
        locale = self.getLocale()
        formatter = locale.dates.getFormatter('date','full')
        return formatter.format(self.context)

class DateFormatterMediumView( BrowserView, LocaleLookupMixin ):
    implements(IDateFormatter)

    def __call__(self):
        locale = self.getLocale()
        formatter = locale.dates.getFormatter('date','medium')
        return formatter.format(self.context)

class DateFormatterShortView( BrowserView, LocaleLookupMixin ):
    implements(IDateFormatter)

    def __call__(self):
        locale = self.getLocale()
        formatter = locale.dates.getFormatter('date','short')
        return formatter.format(self.context)

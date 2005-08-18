from zope.app.testing import ztapi

def setUpApplicationPreferences():
    """A utility method for setting up the ApplicationPreferences adapter."""
    from schooltool.app.interfaces import IApplicationPreferences
    from schoolbell.app.app import getApplicationPreferences
    from schooltool.interfaces import ISchoolToolApplication
    ztapi.provideAdapter(ISchoolToolApplication,
                         IApplicationPreferences,
                         getApplicationPreferences)



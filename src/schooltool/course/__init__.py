import stesting

def registerTestSetup():
    from zope.interface import classImplements
    from schooltool.testing import registry

    def haveCalendar():
        from schooltool.course import section
        from schooltool.app.interfaces import IHaveCalendar
        if not IHaveCalendar.implementedBy(section.Section):
            classImplements(section.Section, IHaveCalendar)
    registry.register('CalendarComponents', haveCalendar)

    def bookResources():
        from schooltool.course import section
        from schooltool.resource.interfaces import IBookResources
        if not IBookResources.implementedBy(section.Section):
            classImplements(section.Section, IBookResources)

    registry.register('ResourceComponents', bookResources)

registerTestSetup()
del registerTestSetup


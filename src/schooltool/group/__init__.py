import stesting

def registerTestSetup():
    from zope.interface import classImplements
    from schooltool.testing import registry

    def haveCalendar():
        from schooltool.group import group
        from schooltool.app.interfaces import IHaveCalendar
        if not IHaveCalendar.implementedBy(group.Group):
            classImplements(group.Group, IHaveCalendar)
    registry.register('CalendarComponents', haveCalendar)

registerTestSetup()
del registerTestSetup

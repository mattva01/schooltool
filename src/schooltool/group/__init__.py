# Make a package.

def registerTestSetup():
    from zope.interface import classImplements
    from schooltool.testing import registry

    def addGroupContainer(app):
        from schooltool.group import group
        app['groups'] = group.GroupContainer()
    registry.register('ApplicationContainers', addGroupContainer)

    def haveCalendar():
        from schooltool.group import group
        from schoolbell.app.interfaces import IHaveCalendar
        if not IHaveCalendar.implementedBy(group.Group):
            classImplements(group.Group, IHaveCalendar)
    registry.register('CalendarComponents', haveCalendar)

registerTestSetup()
del registerTestSetup

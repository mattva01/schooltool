# Make a package.

def registerTestSetup():
    from zope.interface import classImplements
    from schoolbell.app.testing import registry

    def addGroupContainer(app):
        from schoolbell.app.group import group
        app['groups'] = group.GroupContainer()
    registry.register('ApplicationContainers', addGroupContainer)

    def haveCalendar():
        from schoolbell.app.group import group
        from schoolbell.app.interfaces import IHaveCalendar
        if not IHaveCalendar.implementedBy(group.Group):
            classImplements(group.Group, IHaveCalendar)
    registry.register('CalendarComponents', haveCalendar)

registerTestSetup()
del registerTestSetup

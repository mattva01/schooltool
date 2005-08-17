# Make a package.

def registerTestSetup():
    from schoolbell.app.testing import registry

    def addGroupContainer(app):
        from schoolbell.app.group import group
        app['groups'] = group.GroupContainer()

    registry.register('ApplicationContainers', addGroupContainer)

registerTestSetup()
del registerTestSetup

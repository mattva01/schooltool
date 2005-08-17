# Make a package.

def registerTestSetup():
    from schoolbell.app.testing import registry

    def addResourceContainer(app):
        from schoolbell.app.resource import resource
        app['resources'] = resource.ResourceContainer()

    registry.register('ApplicationContainers', addResourceContainer)

registerTestSetup()
del registerTestSetup

# Make a package.

def registerTestSetup():
    from schoolbell.app.testing import registry

    def addLevelContainer(app):
        from schooltool.level import level
        app['levels'] = level.LevelContainer()

    registry.register('ApplicationContainers', addLevelContainer)

registerTestSetup()
del registerTestSetup



import stesting

def registerTestSetup():
    from schooltool.testing import registry

    def addSchoolYearContainer(app):
        from schooltool.schoolyear.schoolyear import SchoolYearContainer
        from schooltool.schoolyear.schoolyear import SCHOOLYEAR_CONTAINER_KEY
        app[SCHOOLYEAR_CONTAINER_KEY] = SchoolYearContainer()

    registry.register('ApplicationContainers', addSchoolYearContainer)

registerTestSetup()
del registerTestSetup

# Make a package.

def registerTestSetup():
    from schoolbell.app.testing import registry

    def addCourseAndSectionContainer(app):
        from schooltool.course import course, section
        app['courses'] = course.CourseContainer()
        app['sections'] = section.SectionContainer()

    registry.register('ApplicationContainers', addCourseAndSectionContainer)

registerTestSetup()
del registerTestSetup


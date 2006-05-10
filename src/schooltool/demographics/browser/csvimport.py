from schooltool.person.browser.csvimport import PersonCSVImporter as\
     PersonCSVImporterBase
from schooltool.demographics.person import Person
from schooltool.app.browser.csvimport import BaseCSVImportView

class PersonCSVImporter(PersonCSVImporterBase):
    def personFactory(self, username, title):
        return Person(username=username, title=title)

class PersonCSVImportView(BaseCSVImportView):
    importer_class = PersonCSVImporter
    

#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
SchoolTool section views
"""

from collections import defaultdict
from urllib import urlencode

import zc.table.table
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import adapts, adapter
from zope.component import getMultiAdapter, getAdapter
from zope.component import getUtility
from zope.container.contained import NameChooser
from zope.container.interfaces import INameChooser
from zope.event import notify
from zope.i18n import translate
from zope.i18n.interfaces.locales import ICollator
from zope.interface import implements, Invalid, directlyProvides
from zope.interface import implementer, Interface
from zope.intid.interfaces import IIntIds
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.cachedescriptors.property import Lazy
from zope.schema import Choice
from zope.schema import ValidationError
from zope.security.checker import canAccess
from zope.security.proxy import removeSecurityProxy
from zope.proxy import sameProxiedObjects
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.traversing.browser.interfaces import IAbsoluteURL
from z3c.form import form, subform, field, datamanager, button
from z3c.form.action import ActionErrorOccurred
from z3c.form.interfaces import ActionExecutionError
from z3c.form.interfaces import HIDDEN_MODE
from z3c.form.validator import SimpleFieldValidator
from z3c.form.validator import WidgetValidatorDiscriminators
from zc.table.column import GetterColumn
from zc.table.interfaces import ISortableColumn

from schooltool.app.browser.app import BaseEditView
from schooltool.app.browser.app import RelationshipViewBase
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.utils import vocabulary_titled
from schooltool.basicperson.browser.person import EditPersonRelationships
from schooltool.common import SchoolToolMessage as _
from schooltool.common.inlinept import InheritTemplate
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.course.interfaces import ICourse, ICourseContainer
from schooltool.course.interfaces import ISection, ISectionContainer
from schooltool.course.section import Section
from schooltool.course.section import copySection
from schooltool.course.browser.course import CoursesActiveTabMixin as SectionsActiveTabMixin
from schooltool.person.interfaces import IPerson
from schooltool.resource.browser.resource import EditLocationRelationships
from schooltool.resource.browser.resource import EditEquipmentRelationships
from schooltool.resource.interfaces import ILocation, IEquipment
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.schoolyear.browser.schoolyear import SchoolyearNavBreadcrumbs
from schooltool.skin.containers import ContainerView
from schooltool.skin import flourish
from schooltool.skin.flourish.containers import ContainerDeleteView
from schooltool.skin.flourish.form import Dialog
from schooltool.skin.flourish.form import DialogForm
from schooltool.skin.flourish.form import DisplayForm
from schooltool.skin.flourish.form import Form
from schooltool.skin.flourish.page import LinkViewlet
from schooltool.skin.flourish.page import ModalFormLinkViewlet
from schooltool.skin.flourish.page import Page
from schooltool.skin.flourish.page import RefineLinksViewlet
from schooltool.skin.flourish.breadcrumbs import PageBreadcrumbs
from schooltool.skin.flourish.page import TertiaryNavigationManager
from schooltool import table
from schooltool.term.interfaces import IDateManager
from schooltool.term.interfaces import ITerm
from schooltool.term.term import getPreviousTerm, getNextTerm
from schooltool.term.term import listTerms


class SectionContainerAbsoluteURLAdapter(BrowserView):

    adapts(ISectionContainer, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        container_id = int(self.context.__name__)
        int_ids = getUtility(IIntIds)
        container = int_ids.getObject(container_id)
        url = str(getMultiAdapter((container, self.request), name='absolute_url'))
        return url + '/sections'

    __call__ = __str__


class SectionContainerView(ContainerView):
    """A Course Container view."""

    __used_for__ = ISectionContainer

    @property
    def term(self):
        return ITerm(self.context)

    @property
    def school_year(self):
        return ISchoolYear(self.context)


class SectionCopyingView(SectionContainerView):
    """A view to copy sections from the previous term."""

    __used_for__ = ISectionContainer

    @property
    def container(self):
        term = self.prev_term
        if term is None:
            return None
        return ISectionContainer(term)

    @property
    def prev_term(self):
        return getPreviousTerm(self.term)

    @property
    def select_all_boxes_js(self):
        if self.container is None:
            return ''
        keys = ['"copy.%s"' % section.__name__
                for section in self.batch
                if not section.next]
        return """
            var section_keys = new Array(
                %s
            );

            function selectAll(value) {
                for (key in section_keys) {
                    box = document.getElementById(section_keys[key]);
                    if (box) {
                        box.checked = value;
                    }
                }
            }
        """ % ','.join(keys)

    def update(self):
        if self.container is None:
            return
        if 'COPY' in self.request:
            for name, section in self.container.items():
                key = 'copy.%s' % name
                if key in self.request and not section.next:
                    section = removeSecurityProxy(section)
                    new_section = copySection(section, self.term)
                    section.next = new_section
        SectionContainerView.update(self)


class SectionLinkNextView(SectionContainerView):
    """A view to link a section to one in the next term."""

    __used_for__ = ISectionContainer

    error = u''

    @property
    def container(self):
        term = self.target_term
        if term is None:
            return None
        return ISectionContainer(term)

    @property
    def target_term(self):
        return getNextTerm(self.term)

    def link(self, target_section):
        section = removeSecurityProxy(self.context)
        target_section = removeSecurityProxy(target_section)
        section.next = target_section

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
        if self.container is None:
            return
        if 'LINK' in self.request:
            section_name = self.request.get('LINK_SECTION')
            section = self.container.get(section_name)
            if section_name is None or section is None:
                self.error = translate(_('No section selected.'),
                                       context=self.request)
            else:
                self.link(section)
                self.request.response.redirect(self.nextURL())
        SectionContainerView.update(self)

    def nextURL(self):
        return '%s/@@edit.html' % absoluteURL(self.context, self.request)


class SectionLinkPreviousView(SectionLinkNextView):
    """A view to link a section to one in the previous term."""

    @property
    def target_term(self):
        return getPreviousTerm(self.term)

    def link(self, target_section):
        section = removeSecurityProxy(self.context)
        target_section = removeSecurityProxy(target_section)
        section.previous = target_section


class SectionView(BrowserView):
    """A view for courses providing a list of sections."""

    __used_for__ = ISection

    @property
    def term(self):
        return ITerm(self.context)

    @property
    def school_year(self):
        return ISchoolYear(self.context)

    @property
    def linked_terms(self):
        sections = []
        current = self.context
        while current.previous:
            sections.append(current.previous)
            current = current.previous
        sections.reverse()
        current = self.context
        while current.next:
            sections.append(current.next)
            current = current.next
        for section in sections:
            yield {
                'section': section,
                'term': ITerm(section),
                }

    def renderPersonTable(self):
        persons = ISchoolToolApplication(None)['persons']
        formatter = getMultiAdapter((persons, self.request),
                                    table.interfaces.ITableFormatter)
        formatter.setUp(table_formatter=zc.table.table.StandaloneFullFormatter,
                        items=[removeSecurityProxy(person)
                               for person in self.context.members],
                        batch_size=0)
        return formatter.render()


class SectionNameChooser(NameChooser):

    implements(INameChooser)

    def chooseName(self, name, obj):
        """See INameChooser."""

        i = 1
        n = "1"
        while n in self.context:
            i += 1
            n = unicode(i)
        # Make sure the name is valid
        self.checkName(n, obj)
        return n


class SectionAddView(form.AddForm):
    """A view for adding Sections."""

    default_term = None
    default_course = None
    subforms = None
    _created_obj = None

    template = ViewPageTemplateFile('templates/section_add.pt')

    # Note that we also omit the title field, it will be auto-generated
    # See concerns raised in https://bugs.launchpad.net/schooltool/+bug/389283
    fields = field.Fields(ISection).omit(
        '__name__', 'title',
        'label', 'instructors', 'members', 'courses', 'size',
        'previous', 'next', 'linked_sections')

    def update(self):
        super(SectionAddView, self).update()
        self._finishedAdd = False

        self.course_subform = NewSectionCoursesSubform(
            self.context, self.request, self,
            default_course=self.default_course)
        self.term_subform = NewSectionTermsSubform(
            self.context, self.request, self,
            default_term=self.default_term)

        self.course_subform.update()
        self.term_subform.update()

        if (self.course_subform.errors or
            self.term_subform.errors or
            self.widgets.errors):
            self.status = self.formErrorsMessage
        elif self._created_obj:
            self.add(self._created_obj)
            self._finishedAdd = True

    def create(self, data):
        section = Section()
        form.applyChanges(self, section, data)
        return section

    def add(self, section):
        """Add `contact` to the container.

        Uses the username of `contact` as the object ID (__name__).
        """

        course = self.course_subform.course
        terms = self.term_subform.terms
        if course is None or not terms:
            return None

        # add the section to the first term
        sections = ISectionContainer(terms[0])
        name = INameChooser(sections).chooseName('', section)
        sections[name] = section
        section.courses.add(removeSecurityProxy(course))

        # overwrite section title.
        section.title = "%s (%s)" % (course.title, section.__name__)

        # copy and link section in other selected terms
        for term in terms[1:]:
            new_section = copySection(section, term)
            new_section.previous = section
            section = new_section
        self._finishedAdd = False

    def nextURL(self):
        return absoluteURL(self.context, self.request)

    @button.buttonAndHandler(_('Add'), name='add')
    def handleAdd(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        # Note we skip immediate adding of the object,
        # because we want to check subforms for errors first.
        self._created_obj = self.create(data)

    @button.buttonAndHandler(_("Cancel"), name='cancel')
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(self.nextURL())

    def updateActions(self):
        super(SectionAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


class NewSectionTermsSubform(subform.EditSubForm):
    template = ViewPageTemplateFile('templates/basic_subform.pt')
    prefix = 'terms'

    errors = None
    span = None

    def __init__(self, *args, **kw):
        default_term = kw.pop('default_term', None)
        super(NewSectionTermsSubform, self).__init__(*args, **kw)

        if default_term is None:
            selected_year = removeSecurityProxy(ISchoolYear(self.context))
            active_term = getUtility(IDateManager).current_term
            if (active_term is not None and
                ISchoolYear(active_term) is selected_year):
                default_term = active_term

        self.setUpFields(default_term)

    def setUpFields(self, default_term):
        terms = listTerms(self.context)
        self.vocabulary=vocabulary_titled(terms)
        self.span = defaultdict(lambda:default_term)
        self._addTermChoice('starts', _("Starts in term"))
        self._addTermChoice('ends', _("Ends in term"))

    def _addTermChoice(self, name, title):
        schema_field = Choice(
            __name__=name, title=title,
            required=True,
            vocabulary=self.vocabulary,
            default=self.span[name])

        self.fields += field.Fields(schema_field)

    def getContent(self):
        return self.span

    @property
    def terms(self):
        if self.errors:
            return []
        terms = listTerms(self.context)
        if (self.span['starts'] is None or
            self.span['ends'] is None):
            return []
        return [term for term in terms
                if (term.first >= self.span['starts'].first and
                    term.last <= self.span['ends'].last)]

    @button.handler(SectionAddView.buttons['add'])
    def handleAdd(self, action):
        data, self.errors = self.widgets.extract()
        if self.errors:
            return
        changed = form.applyChanges(self, self.getContent(), data)
        starts = self.span['starts']
        ends = self.span['ends']
        if starts.first > ends.first:
            # XXX: this is a workaround for a bug in z3c.form: subforms do
            #      not handle action execution errors properly.
            #      The bug is fixed in z3c.form 2.0, as far as I know.
            widget_name = '%s.widgets.ends:list' % self.prefix
            error = ActionExecutionError(Invalid(
                _('Starting term ($starts_in) is later than ending term ($ends_in)',
                  mapping={'starts_in': starts.title,
                           'ends_in': ends.title})))
            notify(ActionErrorOccurred(action, error))


# XXX: TODO: Add "--no value--" to the course selector dropdown in
#      NewSectionCoursesSubform, once we depend on z3c.form 2.0.


class NewSectionCoursesSubform(subform.EditSubForm):
    template = ViewPageTemplateFile('templates/basic_subform.pt')
    prefix = 'courses'

    errors = None
    values = None

    def __init__(self, *args, **kw):
        default_course = kw.pop('default_course', None)
        super(NewSectionCoursesSubform, self).__init__(*args, **kw)
        courses = ICourseContainer(self.context)
        self.vocabulary=vocabulary_titled(courses.values())
        self.values = {'course': default_course}
        schema_field = Choice(
            __name__='course', title=_('Course'),
            required=True, vocabulary=self.vocabulary)
        self.fields += field.Fields(schema_field)
        datamanager.DictionaryField(self.values, schema_field)

    def getContent(self):
        return self.values

    @property
    def course(self):
        return self.values.get('course')

    @button.handler(SectionAddView.buttons['add'])
    def handleAdd(self, action):
        data, self.errors = self.widgets.extract()
        if self.errors:
            return
        changed = form.applyChanges(self, self.getContent(), data)


class AddSectionForTerm(SectionAddView):
    """A view for adding Sections for a term."""

    form.extends(SectionAddView)

    def __init__(self, *args, **kw):
        super(AddSectionForTerm, self).__init__(*args, **kw)
        self.default_term = ITerm(self.context)


class AddSectionForCourse(SectionAddView):
    """A view for adding Sections for a course."""

    form.extends(SectionAddView)

    def __init__(self, *args, **kw):
        super(AddSectionForCourse, self).__init__(*args, **kw)
        self.default_course = ICourse(self.context)


class SectionEditView(BaseEditView):
    """View for editing Sections."""

    __used_for__ = ISection

    @property
    def next_term(self):
        return getNextTerm(ITerm(self.context))

    @property
    def previous_term(self):
        return getPreviousTerm(ITerm(self.context))

    def update(self):
        if 'UNLINK_NEXT' in self.request:
            section = removeSecurityProxy(self.context)
            section.next = None
            return ''
        elif 'UNLINK_PREVIOUS' in self.request:
            section = removeSecurityProxy(self.context)
            section.previous = None
            return ''
        return BaseEditView.update(self)


class RelationshipEditConfView(RelationshipViewBase):
    """A relationship editing view that displays conflicts."""

    __call__ = ViewPageTemplateFile('templates/edit_relationships.pt')

    @property
    def term(self):
        return ITerm(self.context)

    @property
    def school_year(self):
        return ISchoolYear(self.context)


class SectionInstructorView(RelationshipEditConfView):
    """View for adding instructors to a Section."""

    __used_for__ = ISection

    title = _("Instructors")
    current_title = _("Current Instructors")
    available_title = _("Available Instructors")

    def getCollection(self):
        return self.context.instructors

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['persons']


class SectionLearnerView(RelationshipEditConfView):
    """View for adding learners to a Section.  """

    __used_for__ = ISection

    title = _("Students")
    current_title = _("Current Students")
    available_title = _("Available Students")

    def getCollection(self):
        return self.context.members

    def getSelectedItems(self):
        """Return a list of selected members."""
        return filter(IPerson.providedBy, self.getCollection())

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['persons']


class SectionLinkageView(BrowserView):
    """A view for seeing all terms of a section and linking it to others."""

    @property
    def year(self):
        return ISchoolYear(self.context)

    @property
    def linked(self):
        return len(self.context.linked_sections) > 1

    @property
    def columns(self):
        linked_sections = dict([(ITerm(section), section)
                                 for section in self.context.linked_sections])
        columns = []
        for term in sorted(self.year.values(), key=lambda t: t.first):
            columns.append({
                'term': term,
                'section': linked_sections.get(term),
                })
        return columns


class ExtendTermView(BrowserView):
    """A view for extending a section to a target term."""

    template = ViewPageTemplateFile('templates/extend_term.pt')

    @property
    def term(self):
        return ITerm(self.context)

    @property
    def extend_term(self):
        return ISchoolYear(self.context).get(self.request['term'])

    def __call__(self):
        section = removeSecurityProxy(self.context)
        year = ISchoolYear(section)
        linked_names = [ITerm(s).__name__ for s in section.linked_sections]
        key = self.request['term']

        if key not in year or key in linked_names or 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())

        elif 'EXTEND' in self.request:
            this_term = ITerm(self.context)
            extend_term = year[key]
            if extend_term.first < this_term.first:
                current = section.linked_sections[0]
                target_term = getPreviousTerm(ITerm(current))
            else:
                current = section.linked_sections[-1]
                target_term = getNextTerm(ITerm(current))
            while ITerm(current).first != extend_term.first:
                new_section = copySection(current, target_term)
                if extend_term.first < this_term.first:
                    new_section.next = current
                    target_term = getPreviousTerm(target_term)
                else:
                    new_section.previous = current
                    target_term = getNextTerm(target_term)
                current = new_section
            self.request.response.redirect(self.nextURL())

        else:
            return self.template()

    def nextURL(self):
        return absoluteURL(self.context, self.request) + '/section_linkage.html'


class LinkExistingView(BrowserView):
    """A view for finding a target section in anoother term for linking."""

    template = ViewPageTemplateFile('templates/link_existing.pt')

    @property
    def term(self):
        return ITerm(self.context)

    @property
    def link_term(self):
        term = ISchoolYear(self.context).get(self.request.get('term'))
        if (term is not None and
            term not in [ITerm(s) for s in self.context.linked_sections]):
            return term

    @property
    def sections(self):
        section = removeSecurityProxy(self.context)
        term = self.link_term

        sections = []
        if term is None:
            return sections

        courses = list(section.courses)
        for target in ISectionContainer(term).values():
            if target in section.linked_sections:
                continue
            if not self.filterSection(target):
                continue
            if courses == list(target.courses):
                sections.append(target)
        return sections

    def filterSection(self, section):
        teacher_filter = self.request.get('teacher', '').lower()
        if not teacher_filter:
            return True
        for teacher in section.instructors:
            name = '%s %s' % (teacher.first_name, teacher.last_name)
            if (teacher_filter in name.lower() or
                teacher_filter in teacher.username.lower()):
                return True
        return False

    @property
    def selected_section(self):
        term = self.link_term
        selection = self.request.get('LINK_SECTION')
        if term is not None and selection is not None:
            section = ISectionContainer(term).get(selection[8:])
            if section not in self.context.linked_sections:
                return section

    @property
    def error(self):
        return 'LINK' in self.request and self.selected_section is None

    def __call__(self):
        section = removeSecurityProxy(self.context)
        term = self.term
        link_term = self.link_term

        if link_term is None or 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())

        elif 'LINK' in self.request:
            target_section = self.selected_section
            if target_section is None:
                return self.template()

            if link_term.first < term.first:
                current = section.linked_sections[0]
                target_term = getPreviousTerm(ITerm(current))
            else:
                current = section.linked_sections[-1]
                target_term = getNextTerm(ITerm(current))

            while target_term.first != link_term.first:
                new_section = copySection(current, target_term)
                if link_term.first < term.first:
                    new_section.next = current
                    target_term = getPreviousTerm(target_term)
                else:
                    new_section.previous = current
                    target_term = getNextTerm(target_term)
                current = new_section

            if link_term.first < term.first:
                target_section.next = current
            else:
                target_section.previous = current

            self.request.response.redirect(self.nextURL())

        else:
            return self.template()

    def nextURL(self):
        return absoluteURL(self.context, self.request) + '/section_linkage.html'


class UnlinkSectionView(BrowserView):
    """A view for unlinking a section."""

    template = ViewPageTemplateFile('templates/unlink_section.pt')

    @property
    def term(self):
        return ITerm(self.context)

    @property
    def sections(self):
        sections = []
        for section in [self.context.previous, self.context.next]:
            if section:
                sections.append({
                    'section': section,
                    'term': ITerm(section),
                    })
        return sections

    def __call__(self):
        section = removeSecurityProxy(self.context)

        if not self.sections or 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())

        elif 'UNLINK' in self.request:
            if section.previous:
                section.previous = None
            if section.next:
                section.next = None
            self.request.response.redirect(self.nextURL())

        else:
            return self.template()

    def nextURL(self):
        return absoluteURL(self.context, self.request) + '/section_linkage.html'


class SectionsTertiaryNavigationManager(TertiaryNavigationManager):

    template = InlineViewPageTemplate("""
        <ul tal:attributes="class view/list_class">
          <li tal:repeat="item view/items"
              tal:attributes="class item/class"
              tal:content="structure item/viewlet">
          </li>
        </ul>
    """)

    @property
    def items(self):
        result = []
        schoolyears = ISchoolYearContainer(self.context)
        active = schoolyears.getActiveSchoolYear()
        if 'schoolyear_id' in self.request:
            schoolyear_id = self.request['schoolyear_id']
            active = schoolyears.get(schoolyear_id, active)
        for schoolyear in schoolyears.values():
            url = '%s/%s?schoolyear_id=%s' % (
                absoluteURL(self.context, self.request),
                'sections',
                schoolyear.__name__)
            result.append({
                    'class': schoolyear.first == active.first and 'active' or None,
                    'viewlet': u'<a href="%s">%s</a>' % (url, schoolyear.title),
                    })
        return result


class SectionsAddLinks(RefineLinksViewlet):
    """Manager for Add links in SectionsView"""


class SectionImportLinks(RefineLinksViewlet):
    """Section import links viewlet."""


class SectionLinks(RefineLinksViewlet):
    """Manager for public links in SectionView"""

    @property
    def title(self):
        return self.context.title


class SectionAddLinks(RefineLinksViewlet):
    """Manager for Add links in SectionView"""


class SectionActionsLinks(RefineLinksViewlet):
    """Manager for Action links in SectionView"""

    body_template = InlineViewPageTemplate("""
        <ul tal:attributes="class view/list_class">
          <li tal:repeat="item view/renderable_items"
              tal:attributes="class item/class"
              tal:content="structure item/viewlet">
          </li>
        </ul>
    """)

    # We don't want this manager rendered at all
    # if there are no renderable viewlets
    @property
    def renderable_items(self):
        result = []
        for item in self.items:
            render_result = item['viewlet']()
            if render_result and render_result.strip():
                result.append({
                        'class': item['class'],
                        'viewlet': render_result,
                        })
        return result

    def render(self):
        if self.renderable_items:
            return super(SectionActionsLinks, self).render()


class SectionAddLinkViewlet(LinkViewlet, SectionsActiveTabMixin):

    @property
    def enabled(self):
        if not flourish.canEdit(self.context):
            return False
        return super(SectionAddLinkViewlet, self).enabled

    @property
    def url(self):
        return '%s/%s' % (absoluteURL(self.schoolyear, self.request),
                          'addSection.html')


class SectionAddLinkFromSectionViewlet(SectionAddLinkViewlet):

    @property
    def enabled(self):
        container = self.context.__parent__
        if not flourish.canEdit(container):
            return False
        return super(SectionAddLinkViewlet, self).enabled

    @property
    def schoolyear(self):
        return ISchoolYear(self.context)

    @property
    def url(self):
        return '%s/%s?camefrom=%s' % (
            absoluteURL(self.schoolyear, self.request),
            'addSection.html',
            absoluteURL(self.context, self.request))


class SectionDeleteLink(ModalFormLinkViewlet):

    @property
    def enabled(self):
        if not flourish.canDelete(self.context):
            return False
        return super(SectionDeleteLink, self).enabled

    @property
    def dialog_title(self):
        title = _(u'Delete ${section}',
                  mapping={'section': self.context.title})
        return translate(title, context=self.request)


class FlourishSectionFilterWidget(table.table.FilterWidget):

    template = ViewPageTemplateFile('templates/f_section_filter.pt')


class FlourishSectionTableFormatter(table.table.SchoolToolTableFormatter):

    def columns(self):
        title = table.column.LocaleAwareGetterColumn(
            name='title',
            title=_(u'Title'),
            getter=lambda i, f: i.title,
            subsort=True)
        directlyProvides(title, ISortableColumn)
        return [title]

    def filter(self, items):
        filter_widget = FlourishSectionFilterWidget(self.context, self.request)
        self.filter_widget = filter_widget
        return filter_widget.filter(items)


def get_courses_titles(section, formatter):
    return ', '.join([course.title for course in section.courses])


def get_section_instructors(section, formatter):
    return ', '.join([person.title for person in section.instructors])


def section_instructors_formatter(value, section, formatter):
    return '<br />'.join([person.title for person in section.instructors])


class FlourishSectionsView(flourish.page.Page,
                           SectionsActiveTabMixin):

    container_class = 'container widecontainer'
    content_template = InlineViewPageTemplate('''
      <div tal:content="structure context/schooltool:content/ajax/view/schoolyear/sections_table" />
    ''')

    @property
    def title(self):
        schoolyear = self.schoolyear
        return _('Sections for ${schoolyear}',
                 mapping={'schoolyear': schoolyear.title})


class SectionsTableBase(table.ajax.Table):

    def columns(self):
        default = table.ajax.Table.columns(self)
        term = table.column.LocaleAwareGetterColumn(
            name='term',
            title=_('Term'),
            getter=lambda i, f: ITerm(i).title,
            subsort=True)
        courses = table.column.LocaleAwareGetterColumn(
            name='courses',
            title=_('Courses'),
            getter=get_courses_titles,
            subsort=True)
        size = GetterColumn(
            name='size',
            title=_('Students'),
            getter=lambda i, f: i.size,
            subsort=True)
        instructors = table.column.LocaleAwareGetterColumn(
            name='instructors',
            title=_('Teachers'),
            getter=get_section_instructors,
            cell_formatter=section_instructors_formatter)
        directlyProvides(term, ISortableColumn)
        directlyProvides(courses, ISortableColumn)
        directlyProvides(instructors, ISortableColumn)
        return default + [term, courses, instructors, size]

    def sortOn(self):
        return (('term', True), ('courses', False), ('title', False))


class SectionsTable(SectionsTableBase):

    pass


class SectionListTable(SectionsTableBase):

    def columns(self):
        default = super(SectionListTable, self).columns()
        title, term, courses, instructors, size = default
        return [title, term, instructors]

    def sortOn(self):
        return (('term', True), ('title', False))

    @Lazy
    def source(self):
        sections = {}
        schoolyear = ISchoolYear(self.context)
        for term in schoolyear.values():
            term_section_container = ISectionContainer(term)
            for section in term_section_container.values():
                name = '%s.%s.%s' % (
                    schoolyear.__name__, term.__name__, section.__name__
                    )
                sections[name] = section
        return sections

    def items(self):
        return self.context.sections


class SchoolYearSectionsTable(SectionsTable):

    @property
    def schoolyear(self):
        return ISchoolYear(self.context)

    @Lazy
    def source(self):
        sections = {}
        schoolyear = self.schoolyear
        for term in schoolyear.values():
            term_section_container = ISectionContainer(term)
            for section in term_section_container.values():
                name = '%s.%s.%s' % (
                    schoolyear.__name__, term.__name__, section.__name__
                    )
                sections[name] = section
        return sections


class SectionsTableFilter(table.ajax.TableFilter, FlourishSectionFilterWidget):

    multiple_terms = True
    template = ViewPageTemplateFile('templates/f_section_table_filter.pt')
    title = _("Section title")

    @property
    def search_id(self):
        return self.manager.html_id+'-search'

    @property
    def search_title_id(self):
        return self.manager.html_id+"-title"

    @property
    def search_course_id(self):
        return self.manager.html_id+"-course"

    @property
    def search_term_ids(self):
        return self.manager.html_id+"-terms"

    @Lazy
    def schoolyear(self):
        app = ISchoolToolApplication(None)
        schoolyears = ISchoolYearContainer(app)
        result = schoolyears.getActiveSchoolYear()
        if 'schoolyear_id' in self.request:
            schoolyear_id = self.request['schoolyear_id']
            result = schoolyears.get(schoolyear_id, result)
        return result

    def termContainer(self):
        return self.schoolyear

    def courseContainer(self):
        return ICourseContainer(self.schoolyear)

    def terms(self):
        result = []
        container = self.termContainer()
        items = sorted(container.items(),
                       key=lambda (tid, term):term.first)
        for id, term in items:
            checked = not self.manager.fromPublication
            if self.search_term_ids in self.request:
                term_ids = self.request[self.search_term_ids]
                if not isinstance(term_ids, list):
                    term_ids = [term_ids]
                checked = id in term_ids
            result.append({'id': id,
                           'title': term.title,
                           'checked': checked,
                           'obj': term})
        return result

    def courses(self):
        result = []
        container = self.courseContainer()
        collator = ICollator(self.request.locale)
        items = sorted(container.items(),
                       cmp=collator.cmp,
                       key=lambda (cid, c): c.title)
        for id, course in items:
            result.append({'id': id,
                           'title': course.title})
        return result

    def filter(self, items):
        if len(self.termContainer()) < 2:
            self.multiple_terms = False
        if self.ignoreRequest:
            return items
        if self.search_term_ids in self.request:
            term_ids = self.request[self.search_term_ids]
            if not isinstance(term_ids, list):
                term_ids = [term_ids]
            terms = []
            for term_id in term_ids:
                term = self.termContainer().get(term_id)
                if term is not None:
                    terms.append(term)
            if terms:
                items = [item for item in items
                         if ITerm(item) in terms]
        elif self.multiple_terms:
            return []
        if self.search_course_id in self.request:
            course_id = self.request[self.search_course_id]
            course = self.courseContainer().get(course_id)
            if course:
                items = [item for item in items
                         if item in course.sections]
        if self.search_title_id in self.request:
            searchstr = self.request[self.search_title_id].lower()
            items = [item for item in items
                     if searchstr in item.title.lower()]
        return items


class SectionListTableFilter(SectionsTableFilter):

    template = ViewPageTemplateFile('templates/f_section_list_table_filter.pt')

    @Lazy
    def schoolyear(self):
        return ISchoolYear(self.context)

    def getSectionCount(self, term):
        return len([section for section in ISectionContainer(term).values()
                    if section in self.context.sections])


class SectionsTableSchoolYear(flourish.viewlet.Viewlet):

    template = InlineViewPageTemplate('''
      <input type="hidden" name="schoolyear_id"
             tal:define="schoolyear_id view/view/schoolyear/__name__|nothing"
             tal:condition="schoolyear_id"
             tal:attributes="value schoolyear_id" />
    ''')


class FlourishSectionContainerDeleteView(ContainerDeleteView):

    def nextURL(self):
        if 'CONFIRM' in self.request:
            schoolyear = ISchoolYear(self.context)
            params = {'schoolyear_id': schoolyear.__name__.encode('utf-8')}
            url = '%s/sections?%s' % (
                absoluteURL(ISchoolToolApplication(None), self.request),
                urlencode(params))
            return url
        return ContainerDeleteView.nextURL(self)


class FlourishSectionView(DisplayForm):

    template = InheritTemplate(Page.template)
    content_template = ViewPageTemplateFile('templates/f_section_view.pt')
    fields = field.Fields(ISection)
    fields = fields.select('__name__', 'title', 'description')

    @property
    def courses(self):
        return list(self.context.courses)

    @property
    def linked_terms(self):
        sections = []
        current = self.context
        while current.previous:
            sections.append(current.previous)
            current = current.previous
        sections.reverse()
        current = self.context
        sections.append(current)
        while current.next:
            sections.append(current.next)
            current = current.next
        return [
            {'term': ITerm(section),
             'section': section,
             'current': section is self.context,
             }
            for section in sections]

    @property
    def title(self):
        schoolyear = ISchoolYear(self.context.__parent__)
        return _('Sections for ${schoolyear}',
                 mapping={'schoolyear': schoolyear.title})

    @property
    def subtitle(self):
        return self.context.title

    def done_link(self):
        schoolyear = ISchoolYear(self.context)
        url = '%s/%s?schoolyear_id=%s' % (
            absoluteURL(ISchoolToolApplication(None), self.request),
            'sections',
            schoolyear.__name__)
        return url

    def updateWidgets(self):
        super(FlourishSectionView, self).updateWidgets()
        for widget in self.widgets.values():
            if not widget.value:
                widget.mode = HIDDEN_MODE

    def has_instructors(self):
        return bool(list(self.context.instructors))

    def has_learners(self):
        return bool(list(self.context.members))

    def has_locations(self):
        return bool([r for r in self.context.resources
                     if ILocation(r, None) is not None])

    def has_equipment(self):
        return bool([r for r in self.context.resources
                     if IEquipment(r, None) is not None])


class ISectionAddTitleHint(Interface):
    """Section add optional title hint text."""


@adapter(ISchoolYear)
@implementer(ISectionAddTitleHint)
def getSectionAddTitleHint(context):
    return _(u"If no title is specified, one will be created based on the "
              "course title.")


class FlourishSectionAddView(Form, SectionAddView):

    template = InheritTemplate(Page.template)
    label = None
    legend = _('Section Information')

    fields = field.Fields(ISection).select('title', 'description')

    @property
    def title(self):
        schoolyear = self.context
        return _('Sections for ${schoolyear}',
                 mapping={'schoolyear': schoolyear.title})

    def updateWidgets(self):
        super(FlourishSectionAddView, self).updateWidgets()
        self.widgets['title'].required = False
        self.widgets['title'].field.required = False
        self.widgets['title'].field.description = getAdapter(self.context,
            ISectionAddTitleHint)

    def update(self):
        super(SectionAddView, self).update()
        self._finishedAdd = False

        self.course_subform = FlourishNewSectionCoursesSubform(
            self.context, self.request, self,
            default_course=self.default_course)
        self.term_subform = FlourishNewSectionTermsSubform(
            self.context, self.request, self,
            default_term=self.default_term)
        self.location_subform = FlourishNewSectionLocationSubform(
            self.context, self.request, self)

        self.course_subform.update()
        self.term_subform.update()
        self.location_subform.update()

        if (self.course_subform.errors or
            self.term_subform.errors or
            self.location_subform.errors or
            self.widgets.errors):
            self.errors = self.course_subform.errors  + \
                          self.term_subform.errors + \
                          self.location_subform.errors + \
                          self.widgets.errors
            self.status = self.formErrorsMessage
        elif self._created_obj:
            self.add(self._created_obj)
            self._finishedAdd = True

    def add(self, section):
        course = self.course_subform.course
        terms = self.term_subform.terms
        location = self.location_subform.location
        if course is None or not terms:
            return None

        # add the section to the first term
        sections = ISectionContainer(terms[0])
        name = INameChooser(sections).chooseName('', section)
        sections[name] = section
        self._section = section
        section.courses.add(removeSecurityProxy(course))

        # if user provides no title, set it to default
        if not section.title:
            section.title = u"%s (%s)" % (course.title, section.__name__)

        # copy and link section in other selected terms
        for term in terms[1:]:
            new_section = copySection(section, term)
            new_section.previous = section
            section = new_section

        # if the user provides a location, add it
        if location is not None:
            for section in self._section.linked_sections:
                section.resources.add(removeSecurityProxy(location))

        self._finishedAdd = False

    def nextURL(self):
        return absoluteURL(self._section, self.request)

    @button.buttonAndHandler(_('Submit'), name='add')
    def handleAdd(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        # Note we skip immediate adding of the object,
        # because we want to check subforms for errors first.
        self._created_obj = self.create(data)

    @button.buttonAndHandler(_("Cancel"), name='cancel')
    def handle_cancel_action(self, action):
        if 'camefrom' in self.request:
            url = self.request['camefrom']
            self.request.response.redirect(url)
            return
        schoolyear = self.context
        url = '%s/%s?schoolyear_id=%s' % (
            absoluteURL(ISchoolToolApplication(None), self.request),
            'sections',
            schoolyear.__name__)
        self.request.response.redirect(url)


class FlourishNewSectionTermsSubform(NewSectionTermsSubform):

    @button.handler(FlourishSectionAddView.buttons['add'])
    def handleAdd(self, action):
        data, self.errors = self.widgets.extract()
        if self.errors:
            return
        changed = form.applyChanges(self, self.getContent(), data)


class FlourishSectionTermError(ValidationError):
    __doc__ = _('Starting term is later than ending term')


class SectionTermsValidator(SimpleFieldValidator):

    def validate(self, value):
        # XXX: hack to display the term error next to the widget!
        if self.widget.__name__ == 'starts':
            starts_term = value
            super(SectionTermsValidator, self).validate(starts_term)
            ends_widget = self.view.widgets['ends']
            ends_value = self.request.get(ends_widget.name)[0]
            ends_term = ends_widget.terms.getTermByToken(ends_value).value
            if starts_term.first > ends_term.first:
                raise FlourishSectionTermError()


WidgetValidatorDiscriminators(SectionTermsValidator,
                              view=FlourishNewSectionTermsSubform)


class FlourishNewSectionCoursesSubform(NewSectionCoursesSubform):

    def __init__(self, *args, **kw):
        default_course = kw.pop('default_course', None)
        subform.EditSubForm.__init__(self, *args, **kw)
        courses = ICourseContainer(self.context)
        collator = ICollator(self.request.locale)
        items = sorted(courses.values(),
                       cmp=collator.cmp,
                       key=lambda course:course.title)
        self.vocabulary=vocabulary_titled(items)
        self.values = {'course': default_course}
        schema_field = Choice(
            __name__='course', title=_('Course'),
            required=True, vocabulary=self.vocabulary)
        self.fields += field.Fields(schema_field)
        datamanager.DictionaryField(self.values, schema_field)


    def updateWidgets(self):
        super(FlourishNewSectionCoursesSubform, self).updateWidgets()
        self.widgets['course'].prompt = True
        self.widgets['course'].promptMessage = _('Select a course')

    @button.handler(FlourishSectionAddView.buttons['add'])
    def handleAdd(self, action):
        data, self.errors = self.widgets.extract()
        if self.errors:
            return
        changed = form.applyChanges(self, self.getContent(), data)


class ISectionAddLocationHint(Interface):
    """Section add optional location hint text."""


@adapter(ISchoolYear)
@implementer(ISectionAddLocationHint)
def getSectionAddLocationHint(context):
    return _(u"Additional locations can be added via the section view.")


class FlourishNewSectionLocationSubform(subform.EditSubForm):

    template = ViewPageTemplateFile('templates/section_add_location_subform.pt')
    prefix = 'location'
    errors = None

    def __init__(self, *args, **kw):
        super(FlourishNewSectionLocationSubform, self).__init__(*args, **kw)
        self.values = {'location': None}

        # add location field with titled lacation resources vocabulary
        app = ISchoolToolApplication(None)
        resources = [r for r in app['resources'].values()
                     if ILocation(r, None) is not None]
        schema_field = Choice(
            __name__='location', title= _("Location"),
            required=False, vocabulary=vocabulary_titled(resources))
        self.fields += field.Fields(schema_field)
        datamanager.DictionaryField(self.values, schema_field)

    def updateWidgets(self):
        super(FlourishNewSectionLocationSubform, self).updateWidgets()
        self.widgets['location'].field.description = getAdapter(self.context,
            ISectionAddLocationHint)

    def getContent(self):
        return self.values

    @property
    def location(self):
        return self.values.get('location')

    @button.handler(FlourishSectionAddView.buttons['add'])
    def handleAdd(self, action):
        data, self.errors = self.widgets.extract()
        if self.errors:
            return
        changed = form.applyChanges(self, self.getContent(), data)


class FlourishSectionEditView(Form, form.EditForm):

    template = InheritTemplate(Page.template)
    label = None
    legend = _('Section Information')
    fields = field.Fields(ISection).select('title', 'description')

    @property
    def title(self):
        return self.context.title

    def update(self):
        return form.EditForm.update(self)

    def updateActions(self):
        super(FlourishSectionEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Submit'), name='apply')
    def handleApply(self, action):
        super(FlourishSectionEditView, self).handleApply.func(self, action)
        # XXX: hacky sucessful submit check
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            url = absoluteURL(self.context, self.request)
            self.request.response.redirect(url)

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)


class FlourishSectionDeleteView(DialogForm, form.EditForm):
    """View used for confirming deletion of a section."""

    dialog_submit_actions = ('apply',)
    dialog_close_actions = ('cancel',)
    label = None

    @button.buttonAndHandler(_("Delete"), name='apply')
    def handleDelete(self, action):
        url = '%s/delete.html?delete.%s&CONFIRM' % (
            absoluteURL(self.context.__parent__, self.request),
            self.context.__name__.encode('utf-8'))
        self.request.response.redirect(url)
        # We never have errors, so just close the dialog.
        self.ajax_settings['dialog'] = 'close'

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        pass

    def updateActions(self):
        super(FlourishSectionDeleteView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


class FlourishSectionInstructorView(EditPersonRelationships):
    """View for adding instructors to a Section."""

    @property
    def title(self):
        return self.context.title

    current_title = _("Current instructors")
    available_title = _("Add instructors")

    def getSelectedItems(self):
        return filter(IPerson.providedBy, self.context.instructors)

    def getCollection(self):
        return self.context.instructors


class FlourishSectionLearnerView(EditPersonRelationships):
    """View for adding learners to a Section."""

    @property
    def title(self):
        return self.context.title

    current_title = _("Current students")
    available_title = _("Add students")

    def getSelectedItems(self):
        return filter(IPerson.providedBy, self.context.members)

    def getCollection(self):
        return self.context.members


class FlourishSectionLocationView(EditLocationRelationships):
    """View for adding locations to a Section."""

    @property
    def title(self):
        return self.context.title

    current_title = _("Current locations")
    available_title = _("Add locations")

    def getCollection(self):
        return self.context.resources

    def getSelectedItems(self):
        return [r for r in self.context.resources
                if ILocation(r, None) is not None]

    def getOmmitedItems(self):
        items = self.getSelectedItems()
        return [r for r in self.getAvailableItemsContainer().values()
                if ILocation(r, None) is None
                or r in items]


class FlourishSectionEquipmentView(EditEquipmentRelationships):
    """View for adding equipment to a Section."""

    @property
    def title(self):
        return self.context.title

    current_title = _("Current equipment")
    available_title = _("Add equipment")

    def getCollection(self):
        return self.context.resources

    def getSelectedItems(self):
        return [r for r in self.context.resources
                if IEquipment(r, None) is not None]

    def getOmmitedItems(self):
        items = self.getSelectedItems()
        return [r for r in self.getAvailableItemsContainer().values()
                if IEquipment(r, None) is None
                or r in items]


class FlourishSectionLinkageView(Page, SectionLinkageView):

    @property
    def columns(self):
        linked_sections = dict([(ITerm(section), section)
                                 for section in self.context.linked_sections])
        columns = []
        for term in sorted(self.year.values(), key=lambda t: t.first):
            section = linked_sections.get(term)
            current = sameProxiedObjects(section, self.context)
            info = {
                'term': term,
                'section': section,
                'current': current,
                'link_id': term.__name__.replace('.', '_'),
                'form_id': term.__name__.replace('.', '_') + '_container',
                }
            if section is not None:
                unlink_form_url = '%s/unlink_section.html' % (
                    absoluteURL(self.context, self.request))
                info['unlink_form_url'] = unlink_form_url
                info['unlink_dialog_title'] = self.unlink_dialog_title(term)
            else:
                extend_form_url = '%s/extend_term.html?term=%s' % (
                    absoluteURL(self.context, self.request),
                    term.__name__)
                link_existing_form_url = '%s/link_existing.html?term=%s' % (
                    absoluteURL(self.context, self.request),
                    term.__name__)
                link_existing_link_id = 'existing_' + info['link_id']
                link_existing_form_id = link_existing_link_id + '_container'
                link_existing_dialog_title = self.link_existing_dialog_title()
                info.update(
                    {'extend_form_url': extend_form_url,
                     'extend_dialog_title': self.extend_dialog_title(term),
                     'link_existing_form_url': link_existing_form_url,
                     'link_existing_link_id': link_existing_link_id,
                     'link_existing_form_id': link_existing_form_id,
                     'link_existing_dialog_title': link_existing_dialog_title,
                     })
            columns.append(info)
        return columns

    @property
    def done_link(self):
        return absoluteURL(self.context, self.request)

    def extend_dialog_title(self, term):
        title = _('Extend ${section} to ${term}',
                  mapping={'section': self.context.title,
                           'term': term.title})
        return translate(title, context=self.request)

    def unlink_dialog_title(self, term):
        title = _('Remove links of ${section}',
                  mapping={'section': self.context.title})
        return translate(title, context=self.request)

    def link_existing_dialog_title(self):
        title = _('Link ${section} to Section in Other Term',
                  mapping={'section': self.context.title})
        return translate(title, context=self.request)


class FlourishExtendTermView(Dialog, ExtendTermView):

    def update(self):
        Dialog.update(self)

        section = removeSecurityProxy(self.context)
        year = ISchoolYear(section)
        linked_names = [ITerm(s).__name__ for s in section.linked_sections]
        key = self.request['term']

        if key not in year or key in linked_names or 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())

        elif 'EXTEND' in self.request:
            this_term = ITerm(self.context)
            extend_term = year[key]
            if extend_term.first < this_term.first:
                current = section.linked_sections[0]
                target_term = getPreviousTerm(ITerm(current))
            else:
                current = section.linked_sections[-1]
                target_term = getNextTerm(ITerm(current))
            while ITerm(current).first != extend_term.first:
                new_section = copySection(current, target_term)
                if extend_term.first < this_term.first:
                    new_section.next = current
                    target_term = getPreviousTerm(target_term)
                else:
                    new_section.previous = current
                    target_term = getNextTerm(target_term)
                current = new_section
            self.request.response.redirect(self.nextURL())


class FlourishUnlinkSectionView(Dialog, UnlinkSectionView):

    def update(self):
        Dialog.update(self)

        section = removeSecurityProxy(self.context)

        if not self.sections or 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())

        elif 'UNLINK' in self.request:
            if section.previous:
                section.previous = None
            if section.next:
                section.next = None
            self.request.response.redirect(self.nextURL())


class FlourishLinkExistingView(Dialog, LinkExistingView):

    reload_parent = False

    def update(self):
        Dialog.update(self)

        section = removeSecurityProxy(self.context)
        term = self.term
        link_term = self.link_term

        if link_term is None or 'CANCEL' in self.request:
            self.reload_parent = True
            self.request.response.redirect(self.nextURL())

        elif 'LINK' in self.request:
            target_section = self.selected_section
            if target_section is None:
                return

            if link_term.first < term.first:
                current = section.linked_sections[0]
                target_term = getPreviousTerm(ITerm(current))
            else:
                current = section.linked_sections[-1]
                target_term = getNextTerm(ITerm(current))

            while target_term.first != link_term.first:
                new_section = copySection(current, target_term)
                if link_term.first < term.first:
                    new_section.next = current
                    target_term = getPreviousTerm(target_term)
                else:
                    new_section.previous = current
                    target_term = getNextTerm(target_term)
                current = new_section

            if link_term.first < term.first:
                target_section.next = current
            else:
                target_section.previous = current

            self.reload_parent = True
            self.request.response.redirect(self.nextURL())


class SectionsYearNavBreadcrumbs(SchoolyearNavBreadcrumbs):

    traversal_name = u'sections'
    title = _('Sections')

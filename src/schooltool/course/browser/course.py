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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
course browser views.
"""

from urllib import urlencode

import  zc.table.table
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.interface import implements
from zope.component import adapts
from zope.component import getMultiAdapter
from zope.component import queryMultiAdapter
from zope.component import getUtility
from zope.container.interfaces import INameChooser
from zope.interface import directlyProvides
from zope.intid.interfaces import IIntIds
from zope.app.form.browser.add import AddView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.browser import BrowserView
from zope.security.checker import canAccess
from zope.security import checkPermission
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.i18n.interfaces.locales import ICollator
from zope.i18n import translate
from zope.viewlet.viewlet import ViewletBase
from zc.table.interfaces import ISortableColumn
from z3c.form import field, button, form
from z3c.form.interfaces import HIDDEN_MODE

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.browser.app import ContentTitle
from schooltool.common.inlinept import InheritTemplate
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.term.interfaces import ITerm
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.skin.containers import ContainerView
from schooltool.course.interfaces import ICourse, ICourseContainer
from schooltool.course.interfaces import ISectionContainer
from schooltool.course.interfaces import ILearner, IInstructor
from schooltool.course.course import Course
from schooltool.skin import flourish
from schooltool.skin.flourish.viewlet import Viewlet
from schooltool.skin.flourish.containers import ContainerDeleteView
from schooltool.skin.flourish.page import RefineLinksViewlet
from schooltool.skin.flourish.page import LinkViewlet
from schooltool.skin.flourish.page import Page
from schooltool.skin.flourish.page import Content
from schooltool.skin.flourish.page import ModalFormLinkViewlet
from schooltool.skin.flourish.form import Form
from schooltool.skin.flourish.form import AddForm
from schooltool.skin.flourish.form import DialogForm
from schooltool.skin.flourish.form import DisplayForm
from schooltool.skin.flourish.page import TertiaryNavigationManager
from schooltool import table
from schooltool.table.interfaces import ITableFormatter
from schooltool.common import SchoolToolMessage as _


class CourseContainerAbsoluteURLAdapter(BrowserView):

    adapts(ICourseContainer, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        container_id = int(self.context.__name__)
        int_ids = getUtility(IIntIds)
        container = int_ids.getObject(container_id)
        url = str(getMultiAdapter((container, self.request), name='absolute_url'))
        return url + '/courses'

    __call__ = __str__


class CourseContainerView(ContainerView):
    """A Course Container view."""

    __used_for__ = ICourseContainer

    index_title = _("Course index")

    @property
    def school_year(self):
        return ISchoolYear(self.context)


class CourseView(BrowserView):
    """A view for courses."""

    __used_for__ = ICourse

    @property
    def school_year(self):
        return ISchoolYear(self.context)

    @property
    def details(self):
        details = []
        for name in ['course_id', 'government_id', 'credits']:
            value = getattr(self.context, name)
            if value is not None and unicode(value).strip():
                details.append({
                    'title': ICourse[name].title,
                    'value': value,
                    })
        return details

    @property
    def sections(self):
        items = []
        for section in self.context.sections:
            term = ITerm(section, None)
            items.append({
                'section': section,
                'term': term,
                })
        def sortKey(item):
            # I consider it acceptable to violate security for sorting purposes
            # in this case.
            section = removeSecurityProxy(item['section'])
            term = removeSecurityProxy(item['term'])
            return u'%s%s%s' % (section.label,
                                term.first,
                                section.__name__)
        return sorted(items, key=sortKey)


class CourseAddView(AddView):
    """A view for adding Courses."""

    def nextURL(self):
        return absoluteURL(self.context.context, self.request)

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
        else:
            return AddView.update(self)


class CoursesViewlet(ViewletBase):
    """A viewlet showing the courses a person is in."""

    def __init__(self, *args, **kw):
        super(CoursesViewlet, self).__init__(*args, **kw)
        self.collator = ICollator(self.request.locale)

    def update(self):
        self.instructorOf = self.sectionsAsTeacher()
        self.learnerOf = self.sectionsAsLearner()

    def isTeacher(self):
        """Find out if the person is an instructor for any sections."""
        return bool(self.instructorOf)

    def isLearner(self):
        """Find out if the person is a member of any sections."""
        return bool(self.learnerOf)

    def sectionsAsTeacher(self):
        """Get the sections the person instructs."""
        return self.sectionsAs(IInstructor)

    def sectionsAsLearner(self):
        """Get the sections the person is a member of."""
        return self.sectionsAs(ILearner)

    def sectionsAs(self, role_interface):
        schoolyears_data = {}
        for section in role_interface(self.context).sections():
            sy = ISchoolYear(section)
            if sy not in schoolyears_data:
                schoolyears_data[sy] = {}
            term = ITerm(section)
            if term not in schoolyears_data[sy]:
                schoolyears_data[sy][term] = []
            schoolyears_data[sy][term].append(section)
        result = []
        for sy in sorted(schoolyears_data, key=lambda x:x.first, reverse=True):
            sy_info = {'obj': sy, 'terms': []}
            for term in sorted(schoolyears_data[sy], key=lambda x:x.first):
                sortingKey = lambda section:{'course':
                                             ', '.join([course.title
                                                        for course in
                                                        section.courses]),
                                             'section_title': section.title}
                term_info = {'obj': term, 'sections': []}
                for section in sorted(schoolyears_data[sy][term],
                                      cmp=self.sortByCourseAndSection,
                                      key=sortingKey):
                    section_info = {'obj': section,
                                    'title': '%s -- %s' % \
                                    (', '.join(course.title
                                               for course in section.courses),
                                     section.title)}
                    term_info['sections'].append(section_info)
                sy_info['terms'].append(term_info)
            result.append(sy_info)
        return result

    def sortByCourseAndSection(self, this, other):
        if this['course'] is other['course']:
            return self.collator.cmp(this['section_title'],
                                     other['section_title'])
        return self.collator.cmp(this['course'], other['course'])


class FlourishCoursesViewlet(Viewlet):
    """A flourish viewlet showing the courses a person is in."""

    template = ViewPageTemplateFile('templates/f_coursesviewlet.pt')
    body_template = None
    render = lambda self, *a, **kw: self.template(*a, **kw)

    def __init__(self, *args, **kw):
        super(FlourishCoursesViewlet, self).__init__(*args, **kw)
        self.collator = ICollator(self.request.locale)

    def update(self):
        self.instructorOf = self.sectionsAsTeacher()
        self.learnerOf = self.sectionsAsLearner()

    def isTeacher(self):
        """Find out if the person is an instructor for any sections."""
        return bool(self.instructorOf)

    def isLearner(self):
        """Find out if the person is a member of any sections."""
        return bool(self.learnerOf)

    def sectionsAsTeacher(self):
        """Get the sections the person instructs."""
        return self.sectionsAs(IInstructor)

    def sectionsAsLearner(self):
        """Get the sections the person is a member of."""
        return self.sectionsAs(ILearner)

    def sectionsAs(self, role_interface):
        schoolyears_data = {}
        for section in role_interface(self.context).sections():
            sy = ISchoolYear(section)
            if sy not in schoolyears_data:
                schoolyears_data[sy] = {}
            term = ITerm(section)
            if term not in schoolyears_data[sy]:
                schoolyears_data[sy][term] = []
            schoolyears_data[sy][term].append(section)
        result = []
        for sy in sorted(schoolyears_data, key=lambda x:x.first, reverse=True):
            sy_info = {'obj': sy, 'terms': []}
            for term in sorted(schoolyears_data[sy],
                               key=lambda x:x.first,
                               reverse=True):
                sortingKey = lambda section:{'course':
                                             ', '.join([course.title
                                                        for course in
                                                        section.courses]),
                                             'section_title': section.title}
                term_info = {'obj': term, 'sections': []}
                for section in sorted(schoolyears_data[sy][term],
                                      cmp=self.sortByCourseAndSection,
                                      key=sortingKey):
                    section_info = {
                        'obj': section,
                        'title': section.title,
                        }
                    term_info['sections'].append(section_info)
                sy_info['terms'].append(term_info)
            result.append(sy_info)
        return result

    def sortByCourseAndSection(self, this, other):
        if this['course'] is other['course']:
            return self.collator.cmp(this['section_title'],
                                     other['section_title'])
        return self.collator.cmp(this['course'], other['course'])


class CoursesTertiaryNavigationManager(TertiaryNavigationManager):

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
                'courses',
                schoolyear.__name__)
            result.append({
                    'class': schoolyear.first == active.first and 'active' or None,
                    'viewlet': u'<a href="%s">%s</a>' % (url, schoolyear.title),
                    })
        return result


class CoursesAddLinks(RefineLinksViewlet):
    """Manager for Add links in CoursesView"""


class CoursesImportLinks(RefineLinksViewlet):
    """Course import links viewlet."""


class CourseAddLinks(RefineLinksViewlet):
    """Manager for Add links in CourseView"""

    def render(self):
        # This check is necessary because the user can be a leader
        # of the context course, which gives him schooltool.edit on it
        if canAccess(self.context.__parent__, '__delitem__'):
            return super(CourseAddLinks, self).render()


class CourseActionsLinks(RefineLinksViewlet):
    """Manager for Action links in CourseView"""

    def render(self):
        # This check is necessary because the user can be a leader
        # of the context course, which gives him schooltool.edit on it
        if canAccess(self.context.__parent__, '__delitem__'):
            return super(CourseActionsLinks, self).render()


class CourseDeleteLink(ModalFormLinkViewlet):

    @property
    def enabled(self):
        if not flourish.canDelete(self.context):
            return False
        return super(CourseDeleteLink, self).enabled

    @property
    def dialog_title(self):
        title = _(u'Delete ${course}',
                  mapping={'course': self.context.title})
        return translate(title, context=self.request)


class CoursesActiveTabMixin(object):

    @property
    def schoolyear(self):
        schoolyears = ISchoolYearContainer(self.context)
        result = schoolyears.getActiveSchoolYear()
        if 'schoolyear_id' in self.request:
            schoolyear_id = self.request['schoolyear_id']
            result = schoolyears.get(schoolyear_id, result)
        return result


class CourseAddLinkViewlet(LinkViewlet, CoursesActiveTabMixin):

    @property
    def url(self):
        courses = ICourseContainer(self.schoolyear)
        return '%s/%s' % (absoluteURL(courses, self.request),
                          'addSchoolToolCourse.html')


class CourseAddLinkFromCourseViewlet(CourseAddLinkViewlet):

    @property
    def schoolyear(self):
        return ISchoolYear(self.context.__parent__)

    @property
    def url(self):
        courses = ICourseContainer(self.schoolyear)
        return '%s/%s?camefrom=%s' % (
            absoluteURL(courses, self.request),
            'addSchoolToolCourse.html',
            absoluteURL(self.context, self.request))


class FlourishCoursesView(table.table.TableContainerView,
                          CoursesActiveTabMixin):

    content_template = InlineViewPageTemplate('''
      <div>
        <tal:block content="structure view/container/schooltool:content/ajax/table" />
      </div>
    ''')

    @property
    def title(self):
        schoolyear = self.schoolyear
        return _('Courses for ${schoolyear}',
                 mapping={'schoolyear': schoolyear.title})

    @property
    def container(self):
        schoolyear = self.schoolyear
        return ICourseContainer(schoolyear)


def getCoursesTable(context, request, view, manager):
    container = view.container
    table = queryMultiAdapter(
        (container, request, view, manager),
        flourish.interfaces.IViewlet,
        'table')
    return table


class CoursesTableBase(table.ajax.Table):

    def columns(self):
        title = table.table.LocaleAwareGetterColumn(
            name='title',
            title=_(u'Title'),
            getter=lambda i, f: i.title,
            subsort=True)
        course_id = table.table.LocaleAwareGetterColumn(
            name='course_id',
            title=_('Course ID'),
            getter=lambda i, f: i.course_id or '',
            subsort=True)
        directlyProvides(title, ISortableColumn)
        directlyProvides(course_id, ISortableColumn)
        return [title, course_id]


class CoursesTable(CoursesTableBase):

    pass


class CourseListTable(CoursesTableBase):

    @property
    def source(self):
        schoolyear = ISchoolYear(self.context)
        return ICourseContainer(schoolyear)

    def items(self):
        return self.context.courses


class CourseTableSchoolYear(flourish.viewlet.Viewlet):
    template = InlineViewPageTemplate('''
      <input type="hidden" name="schoolyear_id"
             tal:define="schoolyear_id view/view/schoolyear/__name__|nothing"
             tal:condition="schoolyear_id"
             tal:attributes="value schoolyear_id" />
    ''')


class CourseTableDoneLink(flourish.viewlet.Viewlet):
    template = InlineViewPageTemplate('''
      <h3 tal:define="can_manage context/schooltool:app/schooltool:can_edit"
          class="done-link" i18n:domain="schooltool">
        <tal:block condition="can_manage">
          <a tal:attributes="href string:${context/schooltool:app/@@absolute_url}/manage"
             i18n:translate="">Done</a>
        </tal:block>
        <tal:block condition="not:can_manage">
          <a tal:attributes="href request/principal/schooltool:person/@@absolute_url"
             i18n:translate="">Done</a>
        </tal:block>
      </h3>
      ''')


class CourseContainerTitle(ContentTitle):

    @property
    def title(self):
        schoolyear = ISchoolYear(self.context)
        return _('Courses for ${schoolyear}',
                 mapping={'schoolyear': schoolyear.title})


class FlourishCourseContainerDeleteView(ContainerDeleteView):

    def nextURL(self):
        if 'CONFIRM' in self.request:
            schoolyear = ISchoolYear(self.context)
            params = {'schoolyear_id': schoolyear.__name__.encode('utf-8')}
            url = '%s/courses?%s' % (
                absoluteURL(ISchoolToolApplication(None), self.request),
                urlencode(params))
            return url
        return ContainerDeleteView.nextURL(self)


class FlourishCourseView(DisplayForm):

    template = InheritTemplate(Page.template)
    content_template = ViewPageTemplateFile('templates/f_course_view.pt')
    fields = field.Fields(ICourse)
    fields = fields.select('__name__', 'title', 'description', 'course_id', 'government_id', 'credits')

    @property
    def sections(self):
        return list(self.context.sections)

    @property
    def canModify(self):
        return checkPermission('schooltool.edit', self.context)

    @property
    def title(self):
        schoolyear = ISchoolYear(self.context.__parent__)
        return _('Courses for ${schoolyear}',
                 mapping={'schoolyear': schoolyear.title})

    @property
    def subtitle(self):
        return self.context.title

    def done_link(self):
        schoolyear = ISchoolYear(self.context.__parent__)
        url = '%s/%s?schoolyear_id=%s' % (
            absoluteURL(ISchoolToolApplication(None), self.request),
            'courses',
            schoolyear.__name__)
        return url

    def updateWidgets(self):
        super(FlourishCourseView, self).updateWidgets()
        for widget in self.widgets.values():
            if not widget.value:
                widget.mode = HIDDEN_MODE

    def has_leaders(self):
        return bool(list(self.context.leaders))


class FlourishCourseViewDoneLink(flourish.viewlet.Viewlet):

    template = InlineViewPageTemplate('''
    <h3 class="done-link" i18n:domain="schooltool">
      <a tal:attributes="href view/view/done_link"
         i18n:translate="">Done</a>
    </h3>
    ''')


class FlourishCourseAddView(AddForm):

    template = InheritTemplate(Page.template)
    label = None
    legend = _('Course Information')
    fields = field.Fields(ICourse)
    fields = fields.select('title', 'description', 'course_id', 'government_id', 'credits')

    def updateActions(self):
        super(FlourishCourseAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Submit'), name='add')
    def handleAdd(self, action):
        super(FlourishCourseAddView, self).handleAdd.func(self, action)

    @button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        if 'camefrom' in self.request:
            url = self.request['camefrom']
            self.request.response.redirect(url)
            return
        schoolyear = ISchoolYear(self.context)
        url = '%s/%s?schoolyear_id=%s' % (
            absoluteURL(ISchoolToolApplication(None), self.request),
            'courses',
            schoolyear.__name__)
        self.request.response.redirect(url)

    def create(self, data):
        course = Course(data['title'], data.get('description'))
        form.applyChanges(self, course, data)
        return course

    def add(self, course):
        chooser = INameChooser(self.context)
        name = chooser.chooseName(u'', course)
        self.context[name] = course
        self._course = course
        return course

    def nextURL(self):
        return absoluteURL(self._course, self.request)

    @property
    def title(self):
        schoolyear = ISchoolYear(self.context)
        return _('Courses for ${schoolyear}',
                 mapping={'schoolyear': schoolyear.title})


class FlourishCourseEditView(Form, form.EditForm):

    template = InheritTemplate(Page.template)
    label = None
    legend = _('Course Information')
    fields = field.Fields(ICourse)
    fields = fields.select('title', 'description', 'course_id', 'government_id', 'credits')

    @property
    def title(self):
        return self.context.title

    def update(self):
        return form.EditForm.update(self)

    def updateActions(self):
        super(FlourishCourseEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Submit'), name='apply')
    def handleApply(self, action):
        super(FlourishCourseEditView, self).handleApply.func(self, action)
        # XXX: hacky sucessful submit check
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            url = absoluteURL(self.context, self.request)
            self.request.response.redirect(url)

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)


class FlourishCourseDeleteView(DialogForm, form.EditForm):
    """View used for confirming deletion of a course."""

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
        super(FlourishCourseDeleteView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


class FlourishCourseFilterWidget(table.table.FilterWidget):

    template = ViewPageTemplateFile('templates/f_course_filter.pt')

    def filter(self, results):
        if 'SEARCH' in self.request:
            searchstr = self.request['SEARCH'].lower()
            results = [item for item in results
                       if searchstr in item.title.lower() or
                       (item.course_id and searchstr in item.course_id.lower())]
        return results


class CoursesTableFilter(table.ajax.TableFilter, FlourishCourseFilterWidget):

    title = _("Title or course ID")

    def filter(self, results):
        if self.ignoreRequest:
            return results
        return FlourishCourseFilterWidget.filter(self, results)


class FlourishCourseTableFormatter(table.table.SchoolToolTableFormatter):

    def columns(self):
        title = table.table.LocaleAwareGetterColumn(
            name='title',
            title=_(u'Title'),
            getter=lambda i, f: i.title,
            subsort=True)
        course_id = table.table.LocaleAwareGetterColumn(
            name='course_id',
            title=_('Course ID'),
            getter=lambda i, f: i.course_id or '',
            subsort=True)
        directlyProvides(title, ISortableColumn)
        directlyProvides(course_id, ISortableColumn)
        return [title, course_id]


class FlourishManageCoursesOverview(Content, CoursesActiveTabMixin):

    body_template = ViewPageTemplateFile(
        'templates/f_manage_courses_overview.pt')

    @property
    def has_schoolyear(self):
        return self.schoolyear is not None

    @property
    def courses(self):
        return ICourseContainer(self.schoolyear, None)

    @property
    def sections(self):
        if self.has_schoolyear:
            result = []
            for term in self.schoolyear.values():
                sections = ISectionContainer(term)
                result.extend(list(sections.values()))
            return result

    @property
    def render_sections_link(self):
        return self.schoolyear is not None and \
               self.schoolyear and \
               self.courses is not None and \
               self.courses

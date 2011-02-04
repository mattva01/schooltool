#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2009 Shuttleworth Foundation
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
Functional Testing Utilities for schooltool.report

"""
import os

from schooltool.testing.functional import ZCMLLayer
from schooltool.report import report


dir = os.path.abspath(os.path.dirname(__file__))
filename = os.path.join(dir, 'ftesting.zcml')

report_functional_layer = ZCMLLayer(filename,
                                   __name__,
                                   'report_functional_layer')


class MockStudentReference(report.StudentReportReference):
    title = 'Mock Student Report'
    description = 'Just a mock student report.'


class MockStudentRequest(report.StudentReportRequest):
    title = 'Mock Student Report'
    extra = '/request_student_report.html'


class MockGroupReference(report.GroupReportReference):
    title = 'Mock Group Report'
    description = 'Just a mock group report.'


class MockGroupRequest(report.GroupReportRequest):
    title = 'Mock Group Report'
    extra = '/request_group_report.html'


class MockSchoolYearReference(report.SchoolYearReportReference):
    title = 'Mock SchoolYear Report'
    description = 'Just a mock schoolyear report.'


class MockSchoolYearRequest(report.SchoolYearReportRequest):
    title = 'Mock SchoolYear Report'
    extra = '/request_schoolyear_report.html'


class MockTermReference(report.TermReportReference):
    title = 'Mock Term Report'
    description = 'Just a mock term report.'


class MockTermRequest(report.TermReportRequest):
    title = 'Mock Term Report'
    extra = '/request_term_report.html'


class MockSectionReference(report.SectionReportReference):
    title = 'Mock Section Report'
    description = 'Just a mock section report.'


class MockSectionRequest(report.SectionReportRequest):
    title = 'Mock Section Report'
    extra = '/request_section_report.html'


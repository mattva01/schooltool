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
Use zpkgsetup to build Zope and SchoolTool

$Id$
"""
import os
import site
import sys

here = os.path.dirname(os.path.abspath(__file__))
buildsupport = os.path.join(here, "buildsupport")

sys.path.insert(0, buildsupport)
# Process *.pth files from buildsupport/:
site.addsitedir(buildsupport)

import zpkgsetup.package
import zpkgsetup.publication
import zpkgsetup.setup


here = os.path.dirname(os.path.abspath(__file__))

context = zpkgsetup.setup.SetupContext(
    "SchoolTool", "SVN", __file__)

context.load_metadata(
    os.path.join(here, "releases", "SchoolTool",
                 zpkgsetup.publication.PUBLICATION_CONF))

context.walk_packages("src")
context.setup()

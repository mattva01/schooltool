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
Main SchoolTool script.
"""
import os
import sys
import getopt
import locale
import gettext
import logging
import errno
import pkg_resources
from StringIO import StringIO
from collections import defaultdict

import ZConfig
import transaction
import zope.configuration.config
import zope.configuration.xmlconfig
from ZODB.ActivityMonitor import ActivityMonitor
from ZODB.interfaces import IDatabase
from zope.interface import directlyProvides, implements
from zope.component import provideUtility
from zope.component import provideAdapter, adapts
from zope.event import notify
from zope.publisher.interfaces.http import IHTTPRequest
from zope.i18n.interfaces import IUserPreferredLanguages
from zope.app.appsetup import DatabaseOpened
from zope.app.publication.zopepublication import ZopePublication
from zope.traversing.interfaces import IContainmentRoot
from zope.lifecycleevent import ObjectAddedEvent
from zope.app.dependable.interfaces import IDependable
from zope.component.hooks import getSite, setSite, setHooks
from zope.component import getUtility
from zope.component import getAdapters
from zope.interface import directlyProvidedBy
from zope.intid import IntIds
from zope.intid.interfaces import IIntIds
from zope.component.interfaces import ISite
from zope.site import LocalSiteManager

from schooltool.app.interfaces import ApplicationStartUpEvent
from schooltool.app.interfaces import ApplicationInitializationEvent
from schooltool.app.interfaces import IPluginInit, IPluginStartUp
from schooltool.app.interfaces import ICatalogStartUp
from schooltool.app.interfaces import ISchoolToolInitializationUtility
from schooltool.app.app import SchoolToolApplication
from schooltool.app.app import getApplicationPreferences
from schooltool.app import pdf
from schooltool.person.interfaces import IPersonFactory
from schooltool.app.interfaces import ICookieLanguageSelector
from schooltool.app.interfaces import CatalogSetUpEvent
from schooltool.app.interfaces import CatalogStartUpEvent
from schooltool.utility.utility import setUpUtilities
from schooltool.utility.utility import UtilitySpecification


MANAGER_USERNAME = 'manager'
MANAGER_PASSWORD = 'schooltool'

locale_charset = locale.getpreferredencoding()

localedir = os.path.join(os.path.dirname(__file__), '..', 'locales')
catalog = gettext.translation('schooltool', localedir, fallback=True)
_ = lambda us: catalog.ugettext(us).encode(locale_charset, 'replace')
_._domain = 'schooltool'


class Options(object):
    config = None
    pack = False
    restore_manager = False
    manager_password = MANAGER_PASSWORD
    config_file = ''


class CookieLanguageSelector(object):
    implements(ICookieLanguageSelector)

    def getLanguageList(self):
        return self.available_languages

    def getSelectedLanguage(self):
        return self.context.cookies.get("schooltool.lang", self.available_languages[0])

    def setSelectedLanguage(self, lang):
        self.context.response.setCookie("schooltool.lang", lang)


def setLanguage(lang):
    """Set the language for the user interface."""
    if lang == 'auto':
        return # language is negotiated at runtime through Accept-Language.

    if len(lang.split(",")) > 1:

        class CookiePreferredLanguage(CookieLanguageSelector):
            adapts(IHTTPRequest)
            implements(IUserPreferredLanguages)

            def __init__(self, context):
                self.context = context
                self.available_languages = [language.strip()
                                            for language in lang.split(",")]

            def getPreferredLanguages(self):
                return (self.getSelectedLanguage(),)

        provideAdapter(CookiePreferredLanguage, provides=IUserPreferredLanguages)
        return

    class SinglePreferredLanguage(object):

        adapts(IHTTPRequest)
        implements(IUserPreferredLanguages)

        def __init__(self, context):
            pass

        def getPreferredLanguages(self):
            return (lang, )

    # Replace the default adapter with one that always asks for the language
    # specified in the configuration file.
    provideAdapter(SinglePreferredLanguage)


class StreamWrapper(object):
    r"""Unicode-friendly wrapper for writable file-like objects.

    Here the terms 'encoding' and 'charset' are used interchangeably.

    The main use case for StreamWrapper is wrapping sys.stdout and sys.stderr
    so that you can forget worrying about charsets of your data.

        >>> import schooltool.app.main
        >>> old_locale_charset = schooltool.app.main.locale_charset
        >>> schooltool.app.main.locale_charset = 'UTF-8'

        >>> sw = StreamWrapper(StringIO())
        >>> print >> sw, u"Hello, world! \u00b7\u263b\u00b7"
        >>> sw.stm.getvalue()
        'Hello, world! \xc2\xb7\xe2\x98\xbb\xc2\xb7\n'

    By default printing Unicode strings to stdout/stderr will raise Unicode
    errors if the stream encoding does not include some characters you are
    printing.  StreamWrapper will replace unconvertable characters to question
    marks, therefore you should only use it for informative messages where such
    loss of information is acceptable.

        >>> schooltool.app.main.locale_charset = 'US-ASCII'
        >>> sw = StreamWrapper(StringIO())
        >>> print >> sw, u"Hello, world! \u00b7\u263b\u00b7"
        >>> sw.stm.getvalue()
        'Hello, world! ???\n'

    StreamWrapper converts all unicode strings that are written to it to the
    encoding defined in the wrapped stream's 'encoding' attribute, or, if that
    is None, to the locale encoding.  Typically the stream's encoding attribute
    is set when the stream is connected to a console device, and None when the
    stream is connected to a file.  On Unix systems the console encoding
    matches the locale charset, but on Win32 systems they differ.

        >>> s = StringIO()
        >>> s.encoding = 'ISO-8859-1'
        >>> sw = StreamWrapper(s)
        >>> print >> sw, u"Hello, world! \u00b7\u263b\u00b7"
        >>> sw.stm.getvalue()
        'Hello, world! \xb7?\xb7\n'

    You can print other kinds of objects:

        >>> sw = StreamWrapper(StringIO())
        >>> print >> sw, 1, 2,
        >>> print >> sw, 3
        >>> sw.stm.getvalue()
        '1 2 3\n'

    but not 8-bit strings:

        >>> sw = StreamWrapper(StringIO())
        >>> print >> sw, "\xff"
        Traceback (most recent call last):
          ...
        UnicodeDecodeError: 'ascii' codec can't decode byte 0xff in position 0: ordinal not in range(128)

    In addition to 'write', StreamWrapper provides 'flush' and 'writelines'

        >>> sw = StreamWrapper(StringIO())
        >>> sw.write('xyzzy\n')
        >>> sw.flush()
        >>> sw.writelines(['a', 'b', 'c', 'd'])
        >>> sw.stm.getvalue()
        'xyzzy\nabcd'

    Clean up:

        >>> schooltool.app.main.locale_charset = old_locale_charset

    """

    def __init__(self, stm):
        self.stm = stm
        self.encoding = getattr(stm, 'encoding', None)
        if self.encoding is None:
            self.encoding = locale_charset

    def write(self, obj):
        self.stm.write(obj.encode(self.encoding, 'replace'))

    def flush(self):
        self.stm.flush()

    def writelines(self, seq):
        for obj in seq:
            self.write(obj)

    def close(self):
        self.stm.close()


class UnicodeFileHandler(logging.StreamHandler):
    """A handler class which writes records to disk files.

    This class differs from logging.FileHandler in that it can handle Unicode
    strings with graceful degradation.
    """

    def __init__(self, filename):
        stm = StreamWrapper(open(filename, 'a'))
        logging.StreamHandler.__init__(self, stm)

    def close(self):
        self.stream.close()


def setUpLogger(name, filenames, format=None):
    """Set up a named logger.

    Sets up a named logger to log into filenames with the given format.
    Two filenames are special: 'STDOUT' means sys.stdout and 'STDERR'
    means sys.stderr.
    """
    formatter = logging.Formatter(format)
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(logging.INFO)
    for filename in filenames:
        if filename == 'STDOUT':
            handler = logging.StreamHandler(sys.stdout)
        elif filename == 'STDERR':
            handler = logging.StreamHandler(sys.stderr)
        else:
            handler = UnicodeFileHandler(filename)
        handler.setFormatter(formatter)
        logger.addHandler(handler)


class PluginDependency(object):

    def __init__(self, plugin, name,
                 other_plugin=None, other_name=None,
                 inverse=False):
        self.plugin, self.name = plugin, name
        self.other_plugin, self.other_name = other_plugin, other_name
        self.inverse = inverse

    def __str__(self):
        direction = '_before_'
        if self.inverse:
            direction = '_after_'
        if self.other_plugin:
            return ('%(plugin)s named "%(name)s" must be executed '
                    '%(before_or_after)s %(other)s named "%(other_name)s".' % {
                        'plugin': self.plugin,
                        'name': self.name,
                        'other': self.other_plugin,
                        'other_name': self.other_name,
                        'before_or_after': direction,
                        })
        return ('%(plugin)s named "%(name)s" must be executed '
                '%(before_or_after)s another.' % {
                    'plugin': self.plugin,
                    'name': self.name,
                    'before_or_after': direction,
                    })


class CyclicPluginActionOrderException(Exception):

    def __init__(self, dependencies):
        self.dependencies = dependencies

    def __repr__(self):
        return (_("Cannot resolve plugin action order:\n") +
                '\n'.join([str(dep) for dep in self.dependencies]))

    __str__ = __repr__


class PluginActionSorter(object):
    new, open, closed = 'new', 'open', 'closed'
    status = None
    result = None
    dependencies = None
    adapters = None

    def __init__(self, adapters):
        self.adapters = list(adapters)
        self.dependencies = defaultdict(lambda:list())
        cache = dict(self.adapters)
        for name, plugin in self.adapters:
            for after in list(plugin.after):
                self.dependencies[name].append(
                    PluginDependency(cache[after], after))
            for before in list(plugin.before):
                self.dependencies[before].append(
                    PluginDependency(plugin, name, inverse=True))

    def _visit(self, adapter):
        name, plugin = adapter
        if self.status[name] == self.new:
            self.status[name] = self.open
            for dependency in self.dependencies[name]:
                errors = self._visit((dependency.name, dependency.plugin))
                if errors is not None:
                    if not dependency.inverse:
                        return errors + [PluginDependency(
                            dependency.plugin, dependency.name,
                            plugin, name,
                            )]
                    else:
                        return errors + [PluginDependency(
                            plugin, name,
                            dependency.plugin, dependency.name,
                            inverse=True
                            )]
            self.result.append(plugin)
            self.status[name] = self.closed

        elif self.status[name] == self.closed:
            return None # already visited

        elif self.status[name] == self.open:
            return [] # a cyclic dependency

    def __call__(self):
        self.status = dict([(name, self.new)
                            for name, plugin in self.adapters])
        self.result = []
        for adapter in self.adapters:
            errors = self._visit(adapter)
            if errors is not None:
                raise CyclicPluginActionOrderException(errors)
        return self.result


def executePluginActions(actions):
    for action in actions:
        try:
            action()
        except Exception, exception:
            print >> sys.stderr, "Failed to execute %s: %s" % (action, exception)


def startSchoolToolCatalogs(event):
    adapters = getAdapters((event.object, ), ICatalogStartUp)
    sorter = PluginActionSorter(adapters)
    executePluginActions(sorter())


def initializeSchoolToolPlugins(event):
    adapters = getAdapters((event.object, ), IPluginInit)
    sorter = PluginActionSorter(adapters)
    executePluginActions(sorter())


def startSchoolToolPlugins(event):
    adapters = getAdapters((event.object, ), IPluginStartUp)
    sorter = PluginActionSorter(adapters)
    executePluginActions(sorter())


def get_schooltool_plugin_configurations():
    """Returns a list of tuples (configuration, handler).

    Configuration is a string containing XML that will be included in
    the config-schema.

    Handler is a function that performs the actual work based on the
    configuration.
    """

    plugin_configurations = list(pkg_resources.iter_entry_points(
            'schooltool.plugin_configuration'))
    return [entry.load().get_configuration()
            for entry in plugin_configurations]


plugin_configurations = get_schooltool_plugin_configurations()


class SchoolToolMachinery(object):

    ZCONFIG_SCHEMA = os.path.join(os.path.dirname(__file__),
                                  'config-schema.xml')

    Options = Options

    def readConfig(self, filename):
        # Read configuration file
        schema_string = open(self.ZCONFIG_SCHEMA).read()
        plugins = [configuration
                   for (configuration, handler) in plugin_configurations]
        schema_string = schema_string % {'plugins': "\n".join(plugins)}
        schema_file = StringIO(schema_string)

        schema = ZConfig.loadSchemaFile(schema_file, self.ZCONFIG_SCHEMA)

        config, handler = ZConfig.loadConfig(schema, filename)
        return config, handler

    def configureComponents(self, options, site_zcml=None):
        """Configure Zope 3 components."""
        # Hook up custom component architecture calls
        setHooks()
        context = zope.configuration.config.ConfigurationMachine()

        for config, handler in plugin_configurations:
            if handler is not None:
                handler(options, context)

        if options.config.devmode:
            context.provideFeature('devmode')

        zope.configuration.xmlconfig.registerCommonDirectives(context)

        if site_zcml is None:
            site_zcml = options.config.site_definition
        context = zope.configuration.xmlconfig.file(
            site_zcml, context=context)

        # Store the configuration context
        from zope.app.appsetup import appsetup
        appsetup.__dict__['__config_context'] = context

    def configureReportlab(self, fontdirs):
        """Configure reportlab given a path to TrueType fonts.

        Disables PDF support in SchoolTool if fontdir is empty.
        Outputs a warning to stderr in case of errors.
        """
        if not fontdirs:
            return

        existing_directories = []
        for fontdir in fontdirs.split(':'):
            if os.path.isdir(fontdir):
                existing_directories.append(fontdir)

        if not existing_directories:
            print >> sys.stderr, (_("Warning: font directories '%s' do"
                                    " not exist.\nPDF support disabled.")
                                  % fontdirs)
            return

        for font_file in pdf.font_map.values():
            font_exists = False
            for fontdir in existing_directories:
                font_path = os.path.join(fontdir, font_file)
                if os.path.exists(font_path):
                    font_exists = True
            if not font_exists:
                print >> sys.stderr, _("Warning: font '%s' does not exist"
                                       " in the font directories '%s'.\n"
                                       "PDF support disabled.") % (font_file,
                                                                   fontdirs)
                return

        pdf.setUpFonts(existing_directories)

    def configure(self, options):
        self.options = options
        self.configureComponents(
            options,
            site_zcml=options.config.site_definition)
        setLanguage(options.config.lang)
        self.configureReportlab(options.config.reportlab_fontdir)


class SchoolToolServer(SchoolToolMachinery):

    system_name = "SchoolTool"

    def load_options(self, argv):
        """Parse the command line and read the configuration file."""
        options = self.Options()

        # Parse command line
        progname = os.path.basename(argv[0])
        try:
            opts, args = getopt.gnu_getopt(argv[1:], 'c:hdr:',
                                           ['config=', 'pack',
                                            'help',
                                            'restore-manager=',
                                            'manage'])
        except getopt.error, e:
            print >> sys.stderr, "%s: %s" % (progname, e)
            print >> sys.stderr, _("Run %s -h for help.") % progname
            sys.exit(1)
        for k, v in opts:
            if k in ('-h', '--help'):
                print (_("\n"
                        "Usage: %s [options]\n"
                        "Options:\n"
                        "  -c, --config xxx       use this configuration file\n"
                        "  -h, --help             show this help message\n"
                        "  --pack                 pack the database\n"
                        "  -r, --restore-manager password\n"
                        "                         restore the manager user with the provided password\n"
                        "                         (read password from the standart input if 'password'\n"
                        "                         is '-')\n"
                        ) % progname).strip()
                sys.exit(0)
            if k in ('-c', '--config'):
                options.config_file = v
            if k in ('-p', '--pack'):
                options.pack = True
            if k in ('-r', '--restore-manager'):
                options.restore_manager = True
                if v != '-':
                    options.manager_password = v
                else:
                    from getpass import getpass
                    password = getpass(_("Manager password: "))
                    options.manager_password = password

        if not options.config_file:
            print >> sys.stderr, _("No configuration file given")
            sys.exit(1)

        print _("Reading configuration from %s") % options.config_file
        try:
            options.config, handler = self.readConfig(options.config_file)
        except ZConfig.ConfigurationError, e:
            print >> sys.stderr, "%s: %s" % (progname, e)
            sys.exit(1)
        if options.config.database.config.storage is None:
            print >> sys.stderr, "%s: %s" % (progname, _(
                "No storage defined in the configuration file."))

            sys.exit(1)

        return options

    def bootstrapSchoolTool(self, db):
        """Bootstrap SchoolTool database."""
        connection = db.open()
        root = connection.root()
        app_obj = root.get(ZopePublication.root_name)
        if app_obj is None:
            app = SchoolToolApplication()

            # Run school specific initialization code
            initializationUtility = getUtility(
                ISchoolToolInitializationUtility)
            initializationUtility.initializeApplication(app)

            directlyProvides(app, directlyProvidedBy(app) + IContainmentRoot)
            root[ZopePublication.root_name] = app
            # savepoint to make sure that the app object has
            # a _p_jar. This is needed to make things like
            # KeyReference work, which in turn is needed to
            # make the catalog work. We make this savepoint
            # optimistic because it will then work with any registered
            # data managers that do not support this feature.
            transaction.savepoint(optimistic=True)

            # set up the site so that local utility setups and catalog
            # indexing would work properly
            if not ISite.providedBy(app):
                app.setSiteManager(LocalSiteManager(app))

            setSite(app)

            # We must set up the int ids utility before setting up any
            # of the plugin specific catalogs, as catalogs rely on
            # IntIds being present
            setUpUtilities(app, [UtilitySpecification(IntIds, IIntIds)])

            # tell plugins to initialize their catalogs, must be done
            # before initializing plugins themselves or else all the
            # initial groups, persons, resources will not get indexed
            notify(CatalogSetUpEvent(app))
            notify(CatalogStartUpEvent(app))

            # initialize plugins themselves
            notify(ApplicationInitializationEvent(app))

            notify(ObjectAddedEvent(app))

            # unset the site so we would not confuse other
            # bootstraping code
            setSite(None)

            self.restoreManagerUser(app, MANAGER_PASSWORD)
            self.initializePreferences(app)
        transaction.commit()
        connection.close()

    def initializePreferences(self, app):
        prefs = getApplicationPreferences(app)
        prefs.initializeTimezone()

    def startApplication(self, db):
        last_site = getSite()
        connection = db.open()
        root = connection.root()
        app = root[ZopePublication.root_name]
        setSite(app)
        notify(CatalogStartUpEvent(app))
        notify(ApplicationStartUpEvent(app))
        setSite(last_site)
        transaction.commit()
        connection.close()

    def restoreManagerUser(self, app, password):
        """Ensure there is a manager user

        Create a user if needed, set password to default, grant
        manager permissions
        """
        # set the site so that catalog utilities and person factory
        # utilities and subscribers were available
        setSite(app)
        if MANAGER_USERNAME not in app['persons']:
            factory = getUtility(IPersonFactory)
            manager = factory.createManagerUser(MANAGER_USERNAME)
            app['persons'][MANAGER_USERNAME] = manager
            IDependable(manager).addDependent('')
        manager = app['persons'][MANAGER_USERNAME]
        manager.setPassword(password)
        app['persons'].super_user = manager
        setSite(None)

    def setup(self, options):
        """Configure SchoolTool."""
        setUpLogger(None, options.config.error_log_file,
                    "%(asctime)s %(message)s")
        setUpLogger('accesslog', options.config.web_access_log_file)

        # Shut up ZODB lock_file, because it logs tracebacks when unable
        # to lock the database file, and we don't want that.
        logging.getLogger('ZODB.lock_file').disabled = True

        self.configure(options)

        # Connect to the database
        db = self.openDB(options)

        return db

    def openDB(self, options):
        # Open the database
        db_configuration = options.config.database
        try:
            db = db_configuration.open()
            if options.pack:
                db.pack()
        except IOError, e:
            print >> sys.stderr, _("Could not initialize the database:\n%s") % e
            if e.errno == errno.EAGAIN: # Resource temporarily unavailable
                print >> sys.stderr, _("\nPerhaps another %s instance"
                                       " is using it?") % self.system_name
            sys.exit(1)

        self.bootstrapSchoolTool(db)
        notify(DatabaseOpened(db))

        if options.restore_manager:
            connection = db.open()
            root = connection.root()
            app = root[ZopePublication.root_name]
            self.restoreManagerUser(app, options.manager_password)
            transaction.commit()
            connection.close()

        # TODO: don't start application when running from command line
        #if options.pack or options.restore_manager:
        #    return db

        self.startApplication(db)

        provideUtility(db, IDatabase)
        db.setActivityMonitor(ActivityMonitor())

        return db

    def main(self, argv=sys.argv):
        options = self.load_options(argv)
        db = self.setup(options)


def main():
    SchoolToolServer().main()

if __name__ == '__main__':
    main()

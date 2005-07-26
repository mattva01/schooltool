import re

class Browser(object):
    def __init__(self, url=None, mech_browser=None):
        if mech_browser is None:
            import mechanize
            mech_browser = mechanize.Browser()

        self.mech_browser = mech_browser
        if url is not None:
            self.open(url)

    def open(self, url, data=None):
        self.mech_browser.open(url, data)

    def addHeader(self, key, value):
        self.mech_browser.addheaders.append( (key, value) )

    @property
    def url(self):
        return self.mech_browser.geturl()

    def reload(self):
        self.mech_browser.reload()
        self._changed()

    def goBack(self, count=1):
        self.mech_browser.back(self, count)
        self._changed()

    @property
    def links(self, *args, **kws):
        return self.mech_browser.links(*args, **kws)

    @property
    def isHtml(self):
        return self.mech_browser.viewing_html()

    @property
    def title(self):
        return self.mech_browser.title()

    def click(self, text=None, url=None, id=None, name=None, coord=(1,1)):
        form, control = self._findControl(text, id, name, type='submit')
        if control is not None:
            self._clickSubmit(form, control, coord)
            self._changed()
            return

        # if we get here, we didn't find a control to click, so we'll look for
        # a regular link

        if id is not None:
            predicate = lambda link: link.attrs.get('id') == id
            self.mech_browser.follow_link(predicate=predicate)
        else:
            if text is not None:
                text_regex = re.compile(text)
            else:
                text_regex = None
            if url is not None:
                url_regex = re.compile(url)
            else:
                url_regex = None

            self.mech_browser.follow_link(text_regex=text_regex,
                                          url_regex=url_regex)
        self._changed()

    @property
    def _findControl(self):
        def _findControl(text, id, name, type=None, form=None):
            for control_form, control in self._controls:
                if form is None or control_form == form:
                    if (((id is not None and control.id == id)
                    or (name is not None and control.name == name)
                    or (text is not None and re.search(text, str(control.value)))
                    ) and (type is None or control.type == type)):
                        self.mech_browser.form = control_form
                        return control_form, control

            return None, None
        return _findControl
        
    def _findForm(self, id, name, action):
        for form in self.mech_browser.forms():
            if ((id is not None and form.attrs.get('id') == id)
            or (name is not None and form.name == name)
            or (action is not None and re.search(action, str(form.action)))):
                self.mech_browser.form = form
                return form

        return None
        
    def _clickSubmit(self, form, control, coord):
        self.mech_browser.open(form.click(
                    id=control.id, name=control.name, coord=coord))

    __controls = None
    @property
    def _controls(self):
        if self.__controls is None:
            self.__controls = []
            for form in self.mech_browser.forms():
                for control in form.controls:
                    self.__controls.append( (form, control) )
        return self.__controls

    @property
    def controls(self):
        return ControlsMapping(self)

    @property
    def forms(self):
        return FormsMapping(self)

    def getControl(self, text, type=None, form=None):
        form, control = self._findControl(text, text, text, type, form)
        if control is None:
            raise ValueError('could not locate control: ' + text)
        return Control(control)

    @property
    def contents(self):
        response = self.mech_browser.response()
        old_location = response.tell()
        response.seek(0)
        for line in iter(lambda: response.readline().strip(), ''):
            pass
        contents = response.read()
        response.seek(old_location)
        return contents

    @property
    def headers(self):
        return self.mech_browser.response().info()

    def _changed(self):
        self.__controls = None


class Control(object):
    def __init__(self, control):
        self.mech_control = control

    def __getattr__(self, name):
        names = ['options', 'disabled', 'type', 'name', 'readonly', 'multiple']
        if name in names:
            return getattr(self.mech_control, name, None)
        else:
            raise AttributeError(name)

    @apply
    def value():
        def fget(self):
            value = self.mech_control.value
            if self.mech_control.type == 'checkbox':
                value = bool(value)
            return value
        def fset(self, value):
            if self.mech_control.type == 'file':
                self.mech_control.add_file(value)
                return
            if self.mech_control.type == 'checkbox':
                if value: 
                    value = ['on']
                else:
                    value = []
            self.mech_control.value = value
        return property(fget, fset)

    def clear(self):
        self.mech_control.clear()

    @property
    def options(self):
        try:
            return self.mech_control.possible_items()
        except:
            raise AttributeError('options')


class FormsMapping(object):
    def __init__(self, browser):
        self.browser = browser

    def __getitem__(self, key):
        try:
            form = self.browser._findForm(key, key, None)
        except ValueError:
            raise KeyError(key)
        return Form(self.browser, form)

    def __contains__(self, item):
        return self.browser._findForm(key, key, None) is not None


class ControlsMapping(object):
    def __init__(self, browser, form=None):
        """Initialize the ControlsMapping
        
        browser - a Browser instance
        form - a ClientForm instance
        """
        self.browser = browser
        self.mech_form = form

    def __getitem__(self, key):
        form, control = self.browser._findControl(key, key, key)
        if control is None:
            raise KeyError(key)
        if self.mech_form is not None and self.mech_form != form:
            raise KeyError(key)
        return Control(control).value

    def __setitem__(self, key, value):
        form, control = self.browser._findControl(key, key, key)
        if control is None:
            raise KeyError(key)
        Control(control).value = value

    def __contains__(self, item):
        try:
            self[item]
        except KeyError:
            return False
        else:
            return True

    def update(self, mapping):
        for k, v in mapping.items():
            self[k] = v


class Form(ControlsMapping):
    
    def __getattr__(self, name):
        names = ['action', 'method', 'enctype', 'name']
        if name in names:
            return getattr(self.mech_form, name, None)
        else:
            raise AttributeError(name)

    @property
    def id(self):
        return self.mech_form.attrs.get(id)

    @property
    def controls(self):
        return ControlsMapping(browser=self.browser, form=self.mech_form)

    def submit(self, text=None, id=None, name=None, coord=(1,1)):
        form, control = self.browser._findControl(
            text, id, name, type='submit', form=self.mech_form)
        if control is not None:
            self.browser._clickSubmit(form, control, coord)
            self.browser._changed()
            return
    

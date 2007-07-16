import os.path
from paste.script.templates import var, Template

HOME = os.path.expanduser('~')

class SchoolToolDeploy(Template):
    _template_dir = 'schooltool_template'
    summary = "(Paste) deployment of a SchoolTool application"

    vars = [
        var('eggs_dir', 'Location where zc.buildout will look for and place '
            'packages', default=os.path.join(HOME, 'buildout-eggs'))
        ]

    def check_vars(self, vars, cmd):
        vars = super(SchoolToolDeploy, self).check_vars(vars, cmd)
        vars['eggs_dir'] = os.path.expanduser(vars['eggs_dir'])
        return vars

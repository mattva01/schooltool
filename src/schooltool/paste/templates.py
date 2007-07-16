import os.path
from paste.script.templates import var, Template

HOME = os.path.expanduser('~')

class SchoolToolDeploy(Template):
    _template_dir = 'schooltool_template'
    summary = "(Paste) deployment of a SchoolTool application"

    def check_vars(self, vars, cmd):
        vars = super(SchoolToolDeploy, self).check_vars(vars, cmd)
        vars['abspath'] = os.path.join(os.path.abspath(cmd.options.output_dir), vars['project'])
        return vars

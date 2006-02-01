#!/usr/bin/env python
"""
Convert SchoolTool's unit test coverage reports to HTML.

Usage: coverage_reports.py [report-directory [output-directory]]

Locates plain-text coverage reports (files named dotted.package.name.cover) in
the report directory and produces HTML reports in the output directory.  The
format of plain-text coverage reports is as follows: the file name is a dotted
Python module name with a .cover suffix (e.g. schooltool.app.__init__.cover).
Each line corresponds to the source file line with a 7 character wide prefix.
The prefix is one of

  '       ' if a line is not an executable code line
  '  NNN: ' where NNN is the number of times this line was executed
  '>>>>>> ' if this line was never executed

You can produce such files with the SchoolTool test runner by specifying
--coverage on the command line.  Usually you will use the supplied makefile
and type 'make coverage'.  The makefile also contains a rule to create
the necessary directory for HTML reports and generate them.  The full
invocation to produce HTML coverage reports is thus

  make coverage coverage-reports-html

"""

import sys
import os


class CoverageNode(dict):
    """Tree node.

    Leaf nodes have no children (items() == []) and correspond to Python
    modules.  Branches correspond to Python packages.  Child nodes are
    accessible via the Python mapping protocol, as you would normally use
    a dict.  Item keys are non-qualified module names.
    """

    def __str__(self):
        covered, total = self.coverage
        uncovered = total - covered
        return '%s%% covered (%s of %s lines uncovered)' % \
               (self.percent, uncovered, total)

    @property
    def percent(self):
        """Compute the coverage percentage."""
        covered, total = self.coverage
        if total != 0:
            return int(100 * covered / total)
        else:
            return 100

    @property
    def coverage(self):
        """Return (number_of_lines_covered, number_of_executable_lines).

        Computes the numbers recursively for the first time and caches the
        result.
        """
        if not hasattr(self, '_total'): # first-time computation
            self._covered = self._total = 0
            for substats in self.values():
                covered_more, total_more = substats.coverage
                self._covered += covered_more
                self._total += total_more
        return self._covered, self._total

    @property
    def uncovered(self):
        """Compute the number of uncovered code lines."""
        covered, total = self.coverage
        return total - covered


def parse_file(filename):
    """Parse a plain-text coverage report and return (covered, total)."""
    covered = 0
    total = 0
    for line in file(filename):
        if line.startswith(' '*7) or len(line) < 7:
            continue
        total += 1
        if not line.startswith('>>>>>>'):
            covered += 1
    return (covered, total)


def get_file_list(path, filter_fn=None):
    """Return a list of files in a directory.

    If you can specify a predicate (a callable), only file names matching it
    will be returned.
    """
    return filter(filter_fn, os.listdir(path))


def filename_to_list(filename):
    """Return a list of package/module names from a filename.

    One example is worth a thousand descriptions:

        >>> filename_to_list('schooltool.app.__init__.cover')
        ['schooltool', 'app', '__init__']

    """
    return filename.split('.')[:-1]


def get_tree_node(tree, index):
    """Return a tree node for a given path.

    The path is a sequence of child node names.

    Creates intermediate and leaf nodes if necessary.
    """
    node = tree
    for i in index:
        node = node.setdefault(i, CoverageNode())
    return node


def create_tree(filelist, path):
    """Create a tree with coverage statistics.

    Takes the directory for coverage reports and a list of filenames relative
    to that directory.  Parses all the files and constructs a module tree with
    coverage statistics.

    Returns the root node of the tree.
    """
    tree = CoverageNode()
    for filename in filelist:
        tree_index = filename_to_list(filename)
        node = get_tree_node(tree, tree_index)
        filepath = os.path.join(path, filename)
        node._covered, node._total = parse_file(filepath)
    return tree


def traverse_tree(tree, index, function):
    """Preorder traversal of a tree.

    ``index`` is the path of the root node (usually []).

    ``function`` gets one argument: the path of a node.
    """
    function(index)
    for key, node in tree.items():
        traverse_tree(node, index + [key], function)


def index_to_url(index):
    """Construct a relative hyperlink to a tree node given its path."""
    if index:
        return '%s.html' % '.'.join(index)
    return 'index.html'


def index_to_filename(index):
    """Construct the plain-text coverage report filename for a node."""
    if index:
        return '%s.cover' % '.'.join(index)
    return ''


def index_to_nice_name(index):
    """Construct an indented name for the node given its path."""
    if index:
        return '&nbsp;' * 4 * (len(index) - 1) + index[-1]
    else:
        return 'Everything'


def index_to_name(index):
    """Construct the full name for the node given its path."""
    if index:
        return '.'.join(index)
    return 'everything'


def generate_html(output_filename, tree, my_index, info, path):
    """Generate HTML for a tree node.

    ``output_filename`` is the output file name.

    ``tree`` is the root node of the tree.

    ``my_index`` is the path of the node for which you are generating this HTML
    file.

    ``info`` is a list of paths of child nodes.

    ``path`` is the directory name for the plain-text report files.
    """
    html = open(output_filename, 'w')
    print >> html, """
    <html>
      <head><title>Unit test coverage for %(name)s</title>
      <style type="text/css">
        a {text-decoration: none; display: block; padding-right: 1em;}
        a:hover {background: #EFA;}
        hr {height: 1px; border: none; border-top: 1px solid gray;}
        .notcovered {background: #FCC;}
      </style>
      </head>
      <body><h1>Unit test coverage for %(name)s</h1>
      <table>
    """ % {'name': index_to_name(my_index)}
    def key(node_path):
        node = get_tree_node(tree, node_path)
        return (len(node_path), -node.uncovered)
    info.sort(key=key)
    for file_index in info:
        if not file_index:
            continue # skip root node
        node = get_tree_node(tree, file_index)
        covered, total = node.coverage
        uncovered = total - covered
        percent = node.percent
        nice_name = index_to_nice_name(file_index)
        if not node.keys():
            nice_name += '.py'
        else:
            nice_name += '/'
        print >> html, '<tr><td><a href="%s">%s</a></td>' % \
                       (index_to_url(file_index), nice_name),
        print >> html, '<td>covered %s%% (%s of %s uncovered)</td></tr>' % \
                       (percent, uncovered, total)
    print >> html, '</table><hr/>'
    if not get_tree_node(tree, my_index):
        file_path = os.path.join(path, index_to_filename(my_index))
        # XXX can get painful if filenames contain unsafe characters
        pipe = os.popen('enscript -q --footer --header -h --language=html'
                        ' --highlight=python --color -o - %s' % file_path, 'r')
        text = pipe.read()
        pipe.close()
        text = text[text.find('<PRE>'):]
        text = text[:text.find('</PRE>')]
        def color_uncov(line):
            if '&gt;&gt;&gt;&gt;&gt;&gt;' in line:
                return ('<div class="notcovered">%s</div>'
                        % line.rstrip('\n'))
            return line
        text = ''.join(map(color_uncov, text.splitlines(True)))
        print >> html, '<pre>%s</pre>' % text
    print >> html, """
    </body>
    </html>"""
    html.close()


def generate_htmls_from_tree(tree, path, report_path):
    """Generate HTML files for all nodes in the tree.

    ``tree`` is the root node of the tree.

    ``path`` is the directory name for the plain-text report files.

    ``report_path`` is the directory name for the output files.
    """
    def make_html(my_index):
        info = []
        def list_parents_and_children(index):
            position = len(index)
            my_position = len(my_index)
            if position <= my_position and index == my_index[:position]:
                info.append(index)
            elif (position == my_position + 1 and
                  index[:my_position] == my_index):
                info.append(index)
            return
        traverse_tree(tree, [], list_parents_and_children)
        output_filename = os.path.join(report_path, index_to_url(my_index))
        if not my_index:
            return # skip root node
        generate_html(output_filename, tree, my_index, info, path)
    traverse_tree(tree, [], make_html)


def make_coverage_reports(path, report_path):
    """Convert reports from ``path`` into HTML files in ``report_path``."""
    def filter_fn(filename):
        return (filename.endswith('.cover') and
                filename.startswith('schooltool') and
                'tests' not in filename and
                not filename.startswith('<'))
    filelist = get_file_list(path, filter_fn)
    tree = create_tree(filelist, path)
    generate_htmls_from_tree(tree, path, report_path)


def main():
    """Process command line arguments and produce HTML coverage reports."""
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = 'coverage'
    if len(sys.argv) > 2:
        report_path = sys.argv[2]
    else:
        report_path = 'coverage/reports'
    make_coverage_reports(path, report_path)


if __name__ == '__main__':
    main()

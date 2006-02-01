#!/usr/bin/env python

import sys
import os
import subprocess
from pprint import pprint


class CoverageNode(dict):

    def __str__(self):
        covered, total = self.coverage
        uncovered = total - covered
        return '%s%% covered (%s of %s lines uncovered)' % \
               (self.percent, uncovered, total)

    @property
    def percent(self):
        covered, total = self.coverage
        if total != 0:
            return int(100 * covered / total)
        else:
            return 100

    @property
    def coverage(self):
        if not hasattr(self, '_total'): # caching
            self._covered, self._total = 0, 0
            for substats in self.values():
                covered_more, total_more = substats.coverage
                self._covered += covered_more
                self._total += total_more
        return self._covered, self._total


def parse_file(path):
    """Parse file and return (covered, total)."""
    covered = 0
    total = 0
    for line in file(path):
        if line.startswith('>>>>>>'):
            total += 1
        try:
            passes = int(line.split(":")[0])
            total += 1
            covered += 1
        except:
            pass
    return (covered, total)


def get_file_list(path, filter_fn=None):
    return filter(filter_fn, os.listdir(path))


def filename_to_list(filename):
    return filename.split('.')[:-1]


def get_tree_node(tree, index):
    node = tree
    for i in index:
        node = node.setdefault(i, CoverageNode())
    return node


def create_tree(filelist, path):
    tree = CoverageNode()
    for filename in filelist:
        tree_index = filename_to_list(filename)
        node = get_tree_node(tree, tree_index)
        filepath = os.path.join(path, filename)
        node._covered, node._total = parse_file(filepath)
    return tree


def traverse_tree(tree, index, function):
    function(index)
    for key, node in tree.items():
        traverse_tree(node, index + [key], function)


def index_to_url(index):
    if index:
        return '%s.html' % '.'.join(index)
    return 'index.html'


def index_to_filename(index):
    if index:
        return '%s.cover' % '.'.join(index)
    return ''


def index_to_nice_name(index):
    if index:
        return '&nbsp;' * 4 * (len(index) - 1) + index[-1]
    else:
        return 'All'


def index_to_name(index):
    if index:
        return '.'.join(index)
    return 'All'


def generate_html(url, tree, my_index, info, path):
    html = open(url, 'w')
    print >> html, """
    <html>
      <head><title>Unit test coverage report for %s</title>
      <style type="text/css">
        a {text-decoration: none; display: block; padding-right: 1em;}
        a:hover {background: #EFA;}
        hr {height: 1px; border: none; border-top: 1px solid gray;}
      </style>
      </head>
      <body><h1>%s</h1>
      <table>
    """ % (index_to_name(my_index), index_to_name(my_index))
    def make_cmp_for_index(sort_by_coverage=False):
        if sort_by_coverage:
            def smart_sort(a, b):
                if len(a) != len(b): return cmp(len(a), len(b))
                a_p = get_tree_node(tree, a).percent
                b_p = get_tree_node(tree, b).percent
                return cmp(a_p, b_p)
            return smart_sort
        else:
            return lambda a, b: cmp(a, b)
    info.sort(make_cmp_for_index(True))
    for file_index in info:
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
        tmp_path = url + '.tmp'
        enscript = 'enscript -q --footer --header -h --language=html --highlight=python --color '
        enscript += '%s -o %s' % (file_path, tmp_path)
        # XXX can get painful if filenames contain unsafe characters
        os.system(enscript)
        text = open(tmp_path).read()
        os.remove(tmp_path)
        text = text[text.find('<PRE>'):]
        text = text[:text.find('</PRE>')]
        def color_uncov(line):
            if '&gt;&gt;&gt;&gt;&gt;&gt;' in line:
                return '<span style="background: #FCC">%s</span>' % line
            return line
        text = '\n'.join(map(color_uncov, text.splitlines()))
        print >> html, '<pre>%s</pre>' % text
    print >> html, """
    </body>
    </html>"""
    html.close()


def generate_htmls_from_tree(tree, path, report_path):
    def make_html(my_index):
        info = []
        def list_parents_and_childs(index):
            position = len(index)
            my_position = len(my_index)
            if position <= my_position and index == my_index[:position]:
                info.append(index)
            elif (position == my_position + 1 and
                  index[:my_position] == my_index):
                info.append(index)
            return
        traverse_tree(tree, [], list_parents_and_childs)
        url = os.path.join(report_path, index_to_url(my_index))
        generate_html(url, tree, my_index, info, path)
    traverse_tree(tree, [], make_html)


def make_coverage_reports(path, report_path):
    def filter_fn(filename):
        return ('tests' not in filename and
                'schooltool' in filename and
                not filename.startswith('<'))
    filelist = get_file_list(path, filter_fn)
    tree = create_tree(filelist, path)
    generate_htmls_from_tree(tree, path, report_path)


def main():
    path = 'coverage'
    report_path = 'reports'
    if len(sys.argv) > 1:
        path = sys.argv[1]
    if len(sys.argv) > 2:
        report_path = sys.argv[2]

    make_coverage_reports(path, report_path)


if __name__ == '__main__':
    main()

#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
Sorting algorithms for viewlet managers.
"""
import itertools


def scc_tarjan(items, graph):
    """Tarjan's strongly connected components algorithm."""
    result = []
    stack = []
    low = {}
    lmax = len(items)

    def visit(n):
        if n in low:
            return
        i = len(low)
        low[n] = i
        pos = len(stack)
        stack.append(n)

        edges = graph.get(n, ())
        if edges:
            for m in items:
                if m in edges:
                    visit(m)
                    low[n] = min(low[n], low[m])

        if low[n] == i:
            component = tuple(stack[pos:])
            stack[pos:] = []
            result.append(component)
            for item in component:
                low[item] = lmax

    for n in items:
        visit(n)

    return result


def topological_sort(items, graph, reverse=False):
    L = []
    S = []

    iter_items = lambda: reverse and reversed(items) or iter(items)
    riter_items = lambda: reverse and iter(items) or reversed(items)

    C = dict.fromkeys(items, 0)
    for n in iter_items():
        C[n] = len(graph.get(n, ()))
        if not C[n]:
            S.append(n)

    while S:
        n = S.pop(0)
        if reverse:
            L.insert(0, n)
        else:
            L.append(n)
        for m in riter_items():
            edges = graph.get(m)
            if edges and n in edges:
                C[m] -= 1
                if C[m] == 0:
                    S.insert(0, m)

    if reverse:
        L = [m for m in items if C[m]] + L
    else:
        L += [m for m in items if C[m]]

    return L


def dependency_graph(before, after):
    graph = {}
    for m, ns in before.items():
        for n in ns:
            if n not in graph:
                graph[n] = set()
            graph[n].add(m)

    for n, ms in after.items():
        for m in ms:
            if n not in graph:
                graph[n] = set()
            graph[n].add(m)
    return graph


def scc_presorted(items, before, after):
    presorted = topological_sort(items, before, reverse=True)
    presorted = topological_sort(presorted, after)
    graph = dependency_graph(before, after)
    components = scc_tarjan(presorted, graph)
    return components


def dependency_sort(items, before, after):
    components = scc_presorted(items, before, after)
    return list(itertools.chain(*components))

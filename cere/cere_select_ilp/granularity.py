#!/usr/bin/env python

import sys
import os
import cPickle as pickle
import networkx as nx
from common.graph_utils import *
import cere_configure
import logging
import csv
from pulp import LpInteger, LpMinimize, LpProblem, LpStatus, LpVariable, lpSum, GLPK

logger = logging.getLogger('ILP selector')
tolerated_error = [5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,99.9]

class Error_table:
    def __init__(self):
        self.table = []

    def complete_error_table(self, error, coverage):
        self.table = self.table + [[error,coverage]]

    def write_table(self, error_file):
        output = open(error_file,'w')
        output.write("Error,Exec Time\n")
        for c in self.table:
            output.write(str(c[0]) + "," + str(c[1]) + "\n")

class Unsolvable(Exception):
    pass

def solve(graph, err, max_coverage=100, step=5):
    coverage = max_coverage
    for n,d in graph.nodes(data=True):
        d['_matching'] = True
        d["_selected"] = False
        if d['_error'] > err: d['_matching'] = False
    while(coverage > 0):
        try:
            s = list(solve_under_coverage(graph, coverage))
            return s, coverage
        except Unsolvable:
            coverage = coverage - step
    
    raise Unsolvable()

def solve_under_coverage(graph, min_coverage=80):

    prob = LpProblem("granularity selection", LpMinimize)
    codelet_vars = LpVariable.dicts("codelet",
            graph,
            lowBound=0,
            upBound=1,
            cat=LpInteger)

    # Objective function:
    prob += lpSum([codelet_vars[n]*d['_coverage'] for n,d in graph.nodes(data=True)])

    # and with good coverage
    prob += (lpSum([codelet_vars[n]*d['_coverage'] for n,d in graph.nodes(data=True)]) >= min_coverage)

    # selected codelets should match
    for n,d in graph.nodes(data=True):
        if not d['_matching']:
            prob += codelet_vars[n] == 0

    # Finally we should never include both the children and the parents
    for dad in graph.nodes():
        for son in graph.nodes():
            if not dad in nx.ancestors(graph, son):
                continue
            # We cannot select dad and son at the same time
            prob += codelet_vars[dad] + codelet_vars[son] <= 1

    #prob.solve(GLPK())
    prob.solve()
    if (LpStatus[prob.status] != 'Optimal'):
        raise Unsolvable()

    for v in prob.variables():
        assert v.varValue == 1.0 or v.varValue == 0.0
        if v.varValue == 1.0:

            for n,d in graph.nodes(data=True):
                if ("codelet_"+str(n)) == v.name:
                    d["_selected"] = True
                    yield n

def solve_with_best_granularity(error):
    target_error = error
    assert(target_error in tolerated_error)

    graph = load_graph()
    if graph == None:
        logger.critical("Cannot load graph. Did you run cere profile?")
        return False

    if( len(graph.nodes()) == 0):
        logger.info('Graph is empty, nothing to select')
        return True
    error_filename = "{0}/table_error.csv".format(cere_configure.cere_config["cere_measures_path"])
    padding = max([len(d['_name']) for n,d in graph.nodes(data=True)])

    table = Error_table()
    target_error_chosen = set()
    graph.graph['coverage'] = 0

    for err in tolerated_error:
        logger.info("Computing matching with a maximum error of {0}%".format(err))
        try:
            chosen, coverage = solve(graph, err)
            table.complete_error_table(err, coverage)
        except(Unsolvable):
            table.complete_error_table(err, coverage)

    try:
        target_error_chosen, target_coverage = solve(graph, target_error)
    except(Unsolvable):
        logger.error("Solution impossible")

    table.write_table(error_filename)
    logger.info("Solved with coverage >= {0}".format(target_coverage))
    for c in target_error_chosen:
        graph.graph['coverage'] = graph.graph['coverage'] + graph.node[c]['_coverage']
        print >>sys.stderr, "> {0} {1}".format(graph.node[c]['_name'].ljust(padding), graph.node[c]['_coverage'])
    save_graph(graph)
    return True

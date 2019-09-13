import networkx as nx
import csv
import neal
import math
from dwave_qbsolv import QBSolv
from cvrptw_problem import CVRPTWProblem
from cvrptw_solvers import *
from itertools import combinations, permutations

import numpy as np

# format:
# nodes.csv: id|enu_east|enu_north|enu_up|lla_longitude|lla_latitude|lla_altitude
# edges.csv: id_1|id_2|distance|time_0|time_1|...|time_23
# TODO: lokalizacje magazynów, paczkomatów itp

GRAPH_PATH = '../tests/bruxelles'
DIST_TO_TIME = float(1) / float(444)
TIME_WINDOWS_RADIUS = 2
VEHICLES_NUM = 10
CAPACITY = 20


def round_to_time_block(time, max_time, time_blocks_num):
    return min(math.ceil((time/max_time)*time_blocks_num), time_blocks_num-1)


def read_test(path):
    in_file = open(path, 'r')

    # Number of time blocks
    time_blocks_num = int(in_file.readline())

    # Number of vehicles
    vehicles_num = int(in_file.readline())

    # Capacities of vehicles
    line = in_file.readline().split()
    capacities = [int(i) for i in line]

    # Number of magazines.
    magazines_num = int(in_file.readline())

    # Number of destinations.
    dests_num = int(in_file.readline())

    nodes_num = magazines_num + dests_num
    print(magazines_num)
    print(dests_num)
    print(nodes_num)

    time_windows_raw = [(0., 0.)] * nodes_num
    print(time_windows_raw)
    weights = np.zeros(nodes_num, dtype=int)

    max_time = 0

    for i in range(dests_num):
        order = in_file.readline().split()

        weight = int(order[0])
        tw_start = float(order[1])
        tw_end = float(order[2])
        max_time = max(max_time, tw_end)
        time_window = (tw_start, tw_end)

        time_windows_raw[i + magazines_num] = time_window
        weights[i + magazines_num] = weight
        time_windows = [(round_to_time_block(ts, max_time, time_blocks_num),
                         round_to_time_block(te, max_time, time_blocks_num))
                        for (ts, te) in time_windows_raw]
    # Creating costs and time_costs matrix.
    costs = np.zeros((nodes_num, nodes_num), dtype=float)
    time_costs = np.zeros((nodes_num, nodes_num), dtype=int)

    max_time *= 1.5

    for i, j in product(range(nodes_num), range(nodes_num)):
        cost_line = in_file.readline().split()
        costs[i][j] = float(cost_line[0])
        time_costs[i][j] = round_to_time_block(float(cost_line[0]) / 400., max_time, time_blocks_num)
    sources = [i for i in range(magazines_num)]
    dests = [i for i in range(magazines_num, nodes_num)]

    in_file.close()

    print("sources:")
    print(sources)
    print("dests:")
    print(dests)
    print("time costs:")
    print(time_costs)
    print("capacities:")
    print(capacities)
    print("weights:")
    print(weights)
    print("time windows:")
    print(time_windows)

    problem = CVRPTWProblem(sources, costs, time_costs, capacities, dests, weights, time_windows,
                            vehicles_num, time_blocks_num)
    return problem


def energy(qubo, smp, prt):
    ans = dict()
    for k in smp.keys():
        if smp[k] == 1:
            ans[k] = 0
    eng = 0
    for k in ans.keys():
        if qubo.__contains__((k, k)):
            eng += qubo[(k, k)]
            if abs(qubo[(k, k)]) > 1 and prt:
                print(k, ' --> ', qubo[(k, k)])

    for (k1, k2) in combinations(ans.keys(), 2):
        if qubo.__contains__((k1, k2)):
            eng += qubo[(k1, k2)]
            if abs(qubo[(k1, k2)]) > 1 and prt:
                print((k1, k2), ' --> ', qubo[(k1, k2)])

        if qubo.__contains__((k2, k1)):
            eng += qubo[(k2, k1)]
            if abs(qubo[(k2, k1)]) > 1 and prt:
                print((k2, k1), ' --> ', qubo[(k2, k1)])

    return eng




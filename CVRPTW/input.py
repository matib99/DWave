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

GRAPH_PATH = '../tests/bruxelles'
DIST_TO_TIME = float(1) / float(444)
TIME_WINDOWS_DIFF = 1
TIME_WINDOWS_RADIUS = 2
VEHICLES_NUM = 10
CAPACITY = 20


def floor_to_value(x, val):
    return math.floor(x / val) * val


def round_to_time_block(time, max_time, time_blocks_num):
    return int(min(math.ceil((time/max_time)*time_blocks_num), time_blocks_num-1))


def create_graph_from_csv(path):
    g = nx.DiGraph(directed=True)

    with open(path+"/vertex_weigths.csv", mode='r') as e_infile:
        reader = csv.reader(e_infile)
        next(reader)
        for row in reader:
            id1 = int(row[0])
            id2 = int(row[1])
            dist = float(row[2])
            time = float(dist * float(DIST_TO_TIME))
            g.add_edge(id1, id2, distance=dist, time=time)

    return g


def read_full_test(path, time_blocks_num, graph_path=GRAPH_PATH):
    graph = create_graph_from_csv(graph_path)
    in_file = open(path, 'r')

    # Smaller id's of sources and orders.
    nodes_id = list()

    # Reading magazines.
    next(in_file)
    nodes_id = [int(s) for s in in_file.readline().split() if s.isdigit()]
    magazines_num = len(nodes_id)

    # Reading destinations, time_windows and weights.
    next(in_file)
    dests_num = int(in_file.readline())
    nodes_num = dests_num + magazines_num

    time_windows_raw = [(0., 0.)] * nodes_num
    weights = np.zeros((nodes_num), dtype=int)
    max_time = 0
    for i in range(dests_num):
        order = in_file.readline().split()

        dest = int(order[0])
        time_window = (float(order[1]), float(order[2]))
        weight = int(order[3])
        if float(order[2]) > max_time:
            max_time = float(order[2])
        nodes_id.append(dest)
        time_windows_raw[i + magazines_num] = time_window
        weights[i + magazines_num] = weight

    max_time *= 1.5

    time_windows = [(round_to_time_block(ts, max_time, time_blocks_num),
                     round_to_time_block(te, max_time, time_blocks_num))
                    for (ts, te) in time_windows_raw]
    '''
    time_windows = [(0, max_time-1) for _ in time_windows_raw]
    '''
    next(in_file)
    vehicles = int(in_file.readline())
    capacities = np.zeros(vehicles, dtype=int)

    for i in range(vehicles):
        line = in_file.readline().split()
        capacities[i] = int(line[1])

    # Creating costs and time_costs matrix.
    costs = np.zeros((nodes_num, nodes_num), dtype=float)
    time_costs = np.zeros((nodes_num, nodes_num), dtype=int)

    for i in range(nodes_num):
        source = nodes_id[i]
        _, paths = nx.single_source_dijkstra(graph, source, weight='distance')
        for j in range(nodes_num):
            d = nodes_id[j]
            path = paths[d]

            prev = source
            for node in path[1:]:
                edge = graph.get_edge_data(prev, node)
                costs[i][j] += edge['distance']
                # time_costs[i][j] += edge['time']
                time_costs[i][j] = round_to_time_block(edge['time'], max_time, time_blocks_num)
                prev = node

    sources = [i for i in range(magazines_num)]
    dests = [i for i in range(magazines_num, nodes_num)]
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
                            vehicles, time_blocks_num)
    in_file.close()
    return problem


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
    time_windows_raw = [(0., 0.)] * nodes_num
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
        time_costs[i][j] = round_to_time_block(float(cost_line[0]) * DIST_TO_TIME, max_time, time_blocks_num)
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


def energy(qubo, smp, prnt):
    ans = dict()
    for k in smp.keys():
        if smp[k] == 1:
            ans[k] = 0
    eng = 0
    for k in ans.keys():
        if qubo.__contains__((k, k)):
            eng += qubo[(k, k)]
            if abs(qubo[(k, k)]) > 1 and prnt:
                print(k, ' --> ', qubo[(k, k)])

    for (k1, k2) in combinations(ans.keys(), 2):
        if qubo.__contains__((k1, k2)):
            eng += qubo[(k1, k2)]
            if abs(qubo[(k1, k2)]) > 1 and prnt:
                print((k1, k2), ' --> ', qubo[(k1, k2)])

        if qubo.__contains__((k2, k1)):
            eng += qubo[(k2, k1)]
            if abs(qubo[(k2, k1)]) > 1 and prnt:
                print((k2, k1), ' --> ', qubo[(k2, k1)])

    return eng




import networkx as nx
import csv
import neal
import math
from cvrptw_problem import CVRPTWProblem
from cvrptw_solvers import *

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
    return min(math.ceil((time/max_time)*time_blocks_num), time_blocks_num)


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

    for i, j in product(range(nodes_num), range(nodes_num)):
        cost_line = in_file.readline().split()
        costs[i][j] = float(cost_line[0])
        # nie wiem czemu tutaj było += zamiast = na dole ???
        time_costs[i][j] = round_to_time_block(float(cost_line[1]), max_time, time_blocks_num)

    sources = [i for i in range(magazines_num)]
    dests = [i for i in range(magazines_num, nodes_num)]

    in_file.close()

    print("sources:")
    print(sources)
    print("costs:")
    print(costs)
    print("time costs:")
    print(time_costs)
    print("capacities:")
    print(capacities)
    print("dests:")
    print(dests)
    print("weights:")
    print(weights)
    print("time windows:")
    print(time_windows)

    problem = CVRPTWProblem(sources, costs, time_costs, capacities, dests, weights, time_windows, vehicles_num, time_blocks_num)
    return problem


# testowanie...
prb = read_test('test.test')
# te parametry trzeba dodać i być może zmienić coś w cvrptwproblem bo się generują błędne rozwiązania
qdict = prb.get_cvrptw_qubo(1000., 100., 1000., 5., 5.).dict

print("annealing")
solver = neal.SimulatedAnnealingSampler()
response = solver.sample_qubo(qdict)

for sample in response:
    solution = CVRPTWSolution(prb, sample)
    print(solution.check())
    solution.description()
# solution = CVRPTWSolution(prb, response)



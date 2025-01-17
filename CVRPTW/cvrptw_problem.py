from qubo_helper import Qubo
from itertools import combinations, permutations


class CVRPTWProblem:

    def __init__(self, sources, costs, time_costs, capacities, dests, weights, time_windows, vehicles_num, time_blocks_num):

        self.costs = costs
        self.time_costs = time_costs
        self.capacities = capacities
        self.dests = dests
        self.weights = weights

        self.time_windows = time_windows
        self.time_blocks_num = time_blocks_num
        self.dests_num = len(dests)
        self.vehicles_num = vehicles_num
        self.max_cost = max(costs[a][b] for (a, b) in combinations(dests + sources, 2)) * 1.25
        self.min_cost = min(costs[a][b] for (a, b) in combinations(dests + sources, 2))
        self.zero_edges = []
        # Merging all sources into one source.
        source = 0
        weights[source] = 0
        self.source = source
        in_nearest_sources = dict()
        out_nearest_sources = dict()

        # Finding nearest source for all destinations.
        for dest in dests:
            in_nearest = sources[0]
            out_nearest = sources[0]
            for s in sources:
                costs[source][s] = 0
                costs[s][source] = 0
                if costs[s][dest] < costs[in_nearest][dest]:
                    in_nearest = s
                if costs[dest][s] < costs[dest][out_nearest]:
                    out_nearest = s
            costs[source][dest] = costs[in_nearest][dest]
            costs[dest][source] = costs[dest][out_nearest]
            time_costs[source][dest] = time_costs[in_nearest][dest]
            time_costs[dest][source] = time_costs[dest][out_nearest]
            in_nearest_sources[dest] = in_nearest
            out_nearest_sources[dest] = out_nearest
        time_costs[source][source] = 0

        self.in_nearest_sources = in_nearest_sources
        self.out_nearest_sources = out_nearest_sources

        # edges to 'delete later'
        for (a, b, c) in permutations(dests, 3):
            if time_costs[a][b] + time_costs[b][c] == time_costs[a][c]:
                self.zero_edges.append((a, c))

    def get_capacity_qubo(self, capacity_const):
        tw = self.time_windows
        dests = self.dests
        weights = self.weights
        cap_qubo = Qubo()
        for vehicle in range(self.vehicles_num):
            capacity = self.capacities[vehicle]
            for (d1, d2) in combinations(dests, 2):
                for (t1, t2) in combinations(range(self.time_blocks_num), 2):
                    if (tw[d1][0] < t1 < tw[d1][1]) and (tw[d2][0] < t2 < tw[d2][1]):
                        index = ((vehicle, d1, t1), (vehicle, d2, t2))
                        cost = capacity_const * weights[d1] * weights[d2] / capacity**2
                        cap_qubo.add(index, cost)
        return cap_qubo

    def get_time_windows_qubo(self, time_windows_const, penalty_const):
        tw_qubo = Qubo()
        for d in self.dests:
            tw = self.time_windows[d]
            for (t1, t2) in combinations(range(self.time_blocks_num), 2):
                for v in range(self.vehicles_num):
                    index = ((v, d, t1), (v, d, t2))
                    index_m = ((v, d, t2), (v, d, t1))
                    index1 = ((v, d, t1), (v, d, t1))
                    index2 = ((v, d, t2), (v, d, t2))

                    # we don't want vehicles to be late
                    if t1 > tw[1]:
                        tw_qubo.add(index1, penalty_const)
                    if t2 > tw[1]:
                        tw_qubo.add(index2, penalty_const)

                    # vehicle can 'visit' certain destination only once. But it can wait for the time window to start
                    # waiting is represented by 2 visits: one before the time window and one at the beginning of it
                    # (because there is no point in waiting any longer)
                    # this should be the only exception in which vehicle can visit twice the same destination
                    if t1 < t2:
                        if t2 != tw[0]:
                            tw_qubo.add(index, penalty_const)
                            tw_qubo.add(index_m, penalty_const)

            for t in range(self.time_blocks_num):
                if tw[0] <= t <= tw[1]:
                    for v in range(self.vehicles_num):
                        index = ((v, d, t), (v, d, t))
                        # reward for being on time
                        tw_qubo.add(index, time_windows_const)
                if t < tw[0]:
                    for t2 in range(t, tw[0]):
                        for d2 in self.dests:
                            if d2 != d:
                                for v in range(self.vehicles_num):
                                    index = ((v, d, t), (v, d2, t2))
                                    index_m = ((v, d2, t2), (v, d, t))
                                    # if vehicle is at the destination before time window it should wait
                                    tw_qubo.add(index, penalty_const)
                                    tw_qubo.add(index_m, penalty_const)
        return tw_qubo

    def get_sources_qubo(self, cost_const, penalty_const, reward_const, time_windows_const):
        src_qubo = Qubo()
        dests = self.dests
        source = self.source
        costs = self.costs
        time_blocks_num = self.time_blocks_num
        for dest in dests:
            in_time = self.time_costs[source][dest]  # [0]
            for t in range(time_blocks_num):
                out_time = self.time_costs[dest][source]  # [t]
                for v in range(self.vehicles_num):
                    in_index = ((v, source, 0), (v, dest, t))
                    out_index = ((v, dest, t), (v, source, t + out_time))
                    dest_index = ((v, dest, t), (v, dest, t))

                    # too early to arrive from source
                    if t < in_time:
                        src_qubo.add(dest_index, penalty_const)

                    else:
                        if t == in_time:
                            cost = (costs[source][dest] - self.min_cost) * cost_const  # [0]
                            src_qubo.add(in_index, (reward_const * 0.5 + cost) * 0.75)
                        else:
                            src_qubo.add(in_index, 0)

                    # to late to go back to the source
                    if time_blocks_num - t - 1 < out_time:
                        src_qubo.add(out_index, penalty_const)
                    else:
                        cost = (costs[dest][source] - self.min_cost) * cost_const  # [0]
                        src_qubo.add(out_index, (reward_const * 0.5 + cost) * 0.75)

                    for t2 in range(t, min(t + out_time, time_blocks_num - 1)):
                        # too fast
                        pnl_index = ((v, dest, t), (v, source, t2))
                        src_qubo.add(pnl_index, penalty_const)

        for v in range(self.vehicles_num):
            for t in range(time_blocks_num):
                src_index = ((v, source, t), (v, source, t))
                src_qubo.add(src_index, time_windows_const)

        for (t1, t2) in combinations(range(1, time_blocks_num), 2):
            for v in range(self.vehicles_num):
                index = ((v, source, t1), (v, source, t2))
                src_qubo.add(index, penalty_const)

        # vehicle must start and end at source
        for t in range(1, time_blocks_num):
            for d in dests:
                for v in range(self.vehicles_num):
                    for t2 in range(t, time_blocks_num):
                        index = ((v, source, t), (v, d, t2))
                        src_qubo.add(index, penalty_const)
        return src_qubo

    def get_cvrptw_qubo(self,
                        penalty_const, reward_const, capacity_const, time_windows_const):

        dests_num = self.dests_num
        cost_const = (-0.5 * reward_const / ((self.max_cost - self.min_cost) * dests_num))
        dests = self.dests
        costs = self.costs
        time_costs = self.time_costs
        vehicles_num = self.vehicles_num
        time_blocks_num = self.time_blocks_num

        vrp_qubo = Qubo()

        for (d1, d2) in permutations(dests, 2):
            for (t1, t2) in combinations(range(time_blocks_num), 2):
                if t1 + time_costs[d1][d2] == t2:
                    for i in range(vehicles_num):
                        # going from (d1) to (d2) at the time (t1) with vehicle (i)
                        cost = (costs[d1][d2] - self.min_cost) * cost_const  # [t]
                        var2 = (i, d2, t2)  # [t]
                        var1 = (i, d1, t1)
                        vrp_qubo.add((var1, var2), (reward_const / dests_num + cost))
                        # reward for visiting destination + cost of travel
                        # parameters on edges are positive if t2 - t2 = time_cost[d1][d2]
                        # zero if t2 - t2 > time_cost[d1][d2] and (penalty const) if t2 - t2 < time_cost[d1][d2]

                else:
                    if d1 != d2:
                        if t1 + time_costs[d1][d2] > t2:
                            for i in range(vehicles_num):
                                # cannot go from (b) to (a) at the time (t1) in (dt)
                                var1 = (i, d1, t1)
                                var3 = (i, d2, t2)
                                vrp_qubo.add((var1, var3), penalty_const)
                        else:
                            for i in range(vehicles_num):
                                # waiting
                                var1 = (i, d1, t1)
                                var3 = (i, d2, t2)
                                vrp_qubo.add((var1, var3), 0)

        # cannot be in 2 places at the same time
        for (d1, d2) in combinations(dests, 2):
            for t in range(time_blocks_num):
                for i in range(vehicles_num):
                    var1 = (i, d1, t)
                    var2 = (i, d2, t)
                    vrp_qubo.add((var1, var2), penalty_const)

        # customer cannot be visited twice in different times
        for d in dests:
            for (t1, t2) in permutations(range(time_blocks_num), 2):
                for (i1, i2) in combinations(range(vehicles_num), 2):
                    var1 = (i1, d, t1)
                    var2 = (i2, d, t2)
                    vrp_qubo.add((var1, var2), penalty_const)

        # customer cannot be visited twice in the same time by 2 different vehicles
        for d in dests:
            for t in range(time_blocks_num):
                for (i1, i2) in combinations(range(vehicles_num), 2):
                    var1 = (i1, d, t)
                    var2 = (i2, d, t)
                    vrp_qubo.add((var1, var2), penalty_const)

        print("src")
        src_qubo = self.get_sources_qubo(cost_const, penalty_const, reward_const / dests_num,
                                         time_windows_const / dests_num)
        print("cap")
        cap_qubo = self.get_capacity_qubo(capacity_const)
        print("tw")
        tw_qubo = self.get_time_windows_qubo(time_windows_const / dests_num, penalty_const)
        print("merge")
        vrp_qubo.merge_with(src_qubo, 1, 1)
        vrp_qubo.merge_with(cap_qubo, 1, 1)
        vrp_qubo.merge_with(tw_qubo, 1, 1)
        print("bound")
        vrp_qubo.bound(-penalty_const, penalty_const)

        return vrp_qubo

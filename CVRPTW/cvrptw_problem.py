from qubo_helper import Qubo
from itertools import combinations, permutations, combinations_with_replacement


# VRP problem with multi-source
class CVRPTWProblem:

    TIME_WINDOW_RADIUS = 10
    TIME_BLOCK = 10

    def __init__(self, sources, costs, time_costs, capacities, dests, weights, time_windows, vehicles_num, time_blocks_num):

        self.costs = costs
        self.time_costs = time_costs
        self.capacities = capacities
        self.dests = dests
        self.weights = weights

        self.time_windows = time_windows
        self.time_blocks_num = time_blocks_num
        self.vehicles_num = vehicles_num

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

    def get_capacity_qubo(self, capacity_const):
        dests = self.dests
        weights = self.weights
        cap_qubo = Qubo()
        for vehicle in range(self.vehicles_num):
            capacity = self.capacities[vehicle]
            for (d1, d2) in combinations(dests, 2):
                for (t1, t2) in combinations(range(self.time_blocks_num), 2):
                    index = ((vehicle, d1, t1), (vehicle, d2, t2))
                    cost = capacity_const * weights[d1] * weights[d2] / capacity**2
                    cap_qubo.add(index, cost)
        return cap_qubo

    def get_time_windows_qubo(self, penalty_const, reward_const):
        tw_qubo = Qubo()
        for d in self.dests:
            tw = self.time_windows[d]
            for t in range(self.time_blocks_num):
                for v in range(self.vehicles_num):
                    index = ((v, d, t),(v, d, t))
                    if tw[0] > t or tw[1] < t:
                        tw_qubo.add(index, penalty_const)
                    else:
                        tw_qubo.add(index, reward_const)
        return tw_qubo

    # z tą funkcją są pewne problemy, ponieważ siędodają zmienne od źródła a one nieco psują, więc na
    # razie je usunę
    def get_sources_qubo(self, order_const_m, order_const_r, penalty_const, reward_const):
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
                    out_index = ((v, dest, t), (v, source, time_blocks_num - 1))
                    dest_index = ((v, dest, t), (v, dest, t))

                    # too early to arrive from source
                    if t < in_time:
                        print(str(t) + " < in_time --> " + str(in_time))
                        # src_qubo.add(in_index, penalty_const)
                        src_qubo.add(dest_index, penalty_const)

                    else:
                        cost = (costs[source][dest] - order_const_m) / order_const_r  # [0]
                        src_qubo.add(in_index, cost)

                    # to late to go back to the source
                    if time_blocks_num - t - 1 < out_time:
                        print(str(time_blocks_num - t - 1) + " > out_time --> " + str(out_time))
                        # src_qubo.add(out_index, penalty_const)
                        src_qubo.add(dest_index, penalty_const)
                    else:
                        cost = (costs[dest][source] - order_const_m) / order_const_r  # [t]
                        src_qubo.add(out_index, cost)

                    # visiting source can only be at the beginning and at the end
                    src_index = ((v, source, t), (v, source, t))
                    if t != time_blocks_num - 1 and t != 0:
                        src_qubo.add(src_index, penalty_const)
                    else:
                        src_qubo.add(src_index, reward_const)

        return src_qubo

    def get_cvrptw_qubo(self,
                        penalty_const, reward_const, order_const_m, order_const_r, capacity_const, time_windows_const):

        dests = self.dests
        costs = self.costs
        time_costs = self.time_costs
        vehicles_num = self.vehicles_num
        time_blocks_num = self.time_blocks_num
        vrp_qubo = Qubo()

        for (d1, d2) in permutations(dests, 2):
            for (t1, t2) in combinations(range(time_blocks_num), 2):
                if t1 + time_costs[d1][d2] <= t2:
                    for i in range(vehicles_num):
                        # going from (d1) to (d2) at the time (t) with vehicle (i)
                        # nie wiem jak dobrze nazwać te stałe od order
                        # zamieniłem tu kolejność d1 i d2 na intuicyjniejszą, nie wiem czy będzie dobrze działać
                        # ale na moje powinno
                        cost = (costs[d1][d2] - order_const_m)/order_const_r  # [t]
                        var2 = (i, d2, t2)  # [t]
                        var1 = (i, d1, t1)
                        vrp_qubo.add((var1, var2), cost)
                        print(((var1, var2), cost))

                else:
                    if t1 <= t2:
                        for i in range(vehicles_num):
                            # cannot go from (b) to (a) at the time (t1) in (dt)
                            var1 = (i, d1, t1)
                            var3 = (i, d2, t2)
                            vrp_qubo.add((var1, var3), penalty_const)

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
                for (i1, i2) in combinations_with_replacement(range(vehicles_num), 2):
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

        src_qubo = self.get_sources_qubo(order_const_m, order_const_r, penalty_const, reward_const)
        cap_qubo = self.get_capacity_qubo(capacity_const)
        tw_qubo = self.get_time_windows_qubo(time_windows_const, reward_const)

        vrp_qubo.merge_with(src_qubo, 1, 1)
        vrp_qubo.merge_with(cap_qubo, 1, 1)
        vrp_qubo.merge_with(tw_qubo, 1, 1)

        vrp_qubo.bound(reward_const, penalty_const)

        return vrp_qubo

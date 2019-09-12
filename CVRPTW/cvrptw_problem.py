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
        self.dests_num = len(dests)
        self.vehicles_num = vehicles_num
        self.max_cost = max(costs[a][b] for (a, b) in combinations(dests + sources, 2)) * 1.25
        self.min_cost = min(costs[a][b] for (a, b) in combinations(dests + sources, 2))
        self.zero_edges = []
        print('min : ', self.min_cost)
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

        for (a, b, c) in permutations(dests, 3):
            if time_costs[a][b] + time_costs[b][c] == time_costs[a][c]:
                print("trójka: ", (a, b, c))
                self.zero_edges.append((a, c))
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

                    if t1 > tw[1]:
                        tw_qubo.add(index1, penalty_const)
                    if t2 > tw[1]:
                        tw_qubo.add(index2, penalty_const)

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
                                    # anti "teleport" penalty
                                    tw_qubo.add(index, penalty_const)
                                    tw_qubo.add(index_m, penalty_const)

        return tw_qubo

    # z tą funkcją są pewne problemy, ponieważ siędodają zmienne od źródła a one nieco psują, więc na
    # razie je usunę
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
                    # poprawione outdest, żeby mół przyjeżdżać kiedy chce
                    out_index = ((v, dest, t), (v, source, t + out_time))
                    dest_index = ((v, dest, t), (v, dest, t))

                    # too early to arrive from source
                    if t < in_time:
                        src_qubo.add(dest_index, penalty_const)

                    else:
                        if t == in_time:
                            cost = (costs[source][dest] - self.min_cost) * cost_const  # [0]
                            src_qubo.add(in_index, (reward_const * 0.5 + cost) * 0.75)
                            # print('in - ', in_index, ' - ', (reward_const * 0.5 + cost) * 0.75)
                        else:
                            src_qubo.add(in_index, 0)

                    # to late to go back to the source
                    if time_blocks_num - t - 1 < out_time:
                        src_qubo.add(out_index, penalty_const)
                    else:
                        cost = (costs[dest][source] - self.min_cost) * cost_const  # [0]
                        src_qubo.add(out_index, (reward_const * 0.5 + cost) * 0.75)
                        # print('out - ', out_index, ' - ', (reward_const * 0.5 + cost) * 0.75)

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
        print(src_qubo.dict.values())
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
                        # going from (d1) to (d2) at the time (t) with vehicle (i)
                        # nie wiem jak dobrze nazwać te stałe od order
                        # zamieniłem tu kolejność d1 i d2 na intuicyjniejszą, nie wiem czy będzie dobrze działać
                        # ale na moje powinno
                        cost = (costs[d1][d2] - self.min_cost) * cost_const  # [t]
                        var2 = (i, d2, t2)  # [t]
                        var1 = (i, d1, t1)
                        # print((d1, d2), ': droga: ', costs[d1][d2], ' cost: ', cost, ' qubo: ', (reward_const / dests_num + cost))
                        vrp_qubo.add((var1, var2), (reward_const / dests_num + cost))
                        # nagroda za dobre odwiedzenie + kara za odległość

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

        src_qubo = self.get_sources_qubo(cost_const, penalty_const, reward_const / dests_num,
                                         time_windows_const / dests_num)
        cap_qubo = self.get_capacity_qubo(capacity_const)
        tw_qubo = self.get_time_windows_qubo(time_windows_const / dests_num, penalty_const)

        vrp_qubo.merge_with(src_qubo, 1, 1)
        vrp_qubo.merge_with(cap_qubo, 1, 1)
        vrp_qubo.merge_with(tw_qubo, 1, 1)

        print('złooooo:', self.zero_edges)
        '''for (a, c) in self.zero_edges:
            dt = time_costs[a][c]
            for t in range(time_blocks_num - dt - 1):
                for v in range(vehicles_num):
                    index = ((v, a, t), (v, c, t + dt))
                    print('dupa: ', index)
                    if vrp_qubo.dict[index] < 0.9 * penalty_const:
                        vrp_qubo.set(index, 0)'''

        vrp_qubo.bound(-penalty_const, penalty_const)

        return vrp_qubo

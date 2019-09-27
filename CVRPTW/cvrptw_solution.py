import operator


class CVRPTWSolution:
    def __init__(self, problem, sample, solution=None):
        self.problem = problem

        if solution is not None:
            self.solution = solution
        else:
            result = list()
            for _ in range(self.problem.vehicles_num):
                result.append([])

            # Decoding solution from qubo sample
            for (v, c, t) in sample:
                if sample[(v, c, t)] == 1 and c != 0:
                    result[v].append((c, t))

            for v in range(self.problem.vehicles_num):
                result[v].sort(key=operator.itemgetter(1))

            # Adding first and last magazine.
            for l in result:
                if len(l) != 0:
                        l.insert(0, (problem.in_nearest_sources[l[0][0]], 0))
                        l.append((problem.out_nearest_sources[l[len(l) - 1][0]], self.problem.time_blocks_num-1))

            self.solution = result

    # Checks capacity and visiting.
    def check(self):
        capacities = self.problem.capacities
        time_windows = self.problem.time_windows
        weights = self.problem.weights
        solution = self.solution

        '''for vehicle_dests in solution:
            cap = capacities[vehicle_num]
            for (dest, _) in vehicle_dests:
                cap -= weights[dest]
            if cap < 0:
                print("capacities")
                return False'''
        result = True

        for v in range(self.problem.vehicles_num):
            cap = capacities[v]
            weight = 0
            prev = -42
            for (dest, t) in solution[v]:
                if dest not in self.problem.dests:
                    continue
                if (t < time_windows[dest][0] or t > time_windows[dest][1]) and prev == dest:
                    print('Destination no. ', dest, 'not visited at time(visited: ', t, 'time window: ',
                          time_windows[dest], ')')
                    result = False
                weight += weights[dest]
                prev = dest
            if cap < weight:
                print("Vehicle no." + str(v) + " overloaded (weight: " + str(weight) + "kg, capacity: " + str(cap)+")")
                result = False

        dests = self.problem.dests
        answer_dests = [dest for vehicle_dests in solution for (dest, _) in vehicle_dests[1:-1]]
        answer_dests = list(dict.fromkeys(answer_dests))
        if len(dests) != len(answer_dests):
            result = False

        lists_cmp = set(dests) & set(answer_dests)
        if lists_cmp == len(dests):
            result = False

        return result

    def total_cost(self):
        costs = self.problem.costs
        source = self.problem.source
        solution = self.solution
        cost = 0

        for vehicle_dests in solution:
            prev = vehicle_dests[0]
            for (dest, t) in vehicle_dests[1:]:
                cost += costs[prev][dest][t]
                prev = dest
            cost += costs[prev][source][t]

        return cost

    def all_time_costs(self):
        time_costs = self.problem.time_costs
        source = self.problem.source
        solution = self.solution
        result = list()

        for vehicle_dests in solution:
            prev = vehicle_dests[0]
            cost = 0
            for (dest, t) in vehicle_dests[1:]:
                cost += time_costs[prev][dest][t]
                prev = dest
            result.append(cost)

        return result

    def description(self):
        costs = self.problem.costs
        solution = self.solution
        weights = self.problem.weights
        total_cost = 0
        vehicle_num = 0
        for vehicle_dests in solution:
            cost = 0
            weight = 0

            print('Vehicle number ', vehicle_num, ' : ')

            if len(vehicle_dests) == 0:
                print('    Vehicle is not used.')
                continue

            print('    Startpoint : ', vehicle_dests[0][0])
            dests_num = 1
            prev = vehicle_dests[0][0]
            for (dest, t) in vehicle_dests[1:len(vehicle_dests) - 1]:

                cost += costs[prev][dest]  # [t]
                weight += weights[dest]
                print('     ->Destination number ', dests_num, ' : ', dest, ', reached at time ', t, '.')
                dests_num += 1
                prev = dest

            endpoint = vehicle_dests[len(vehicle_dests) - 1]
            cost += costs[prev][endpoint[0]]  # [t]
            print('    Endpoint : ', endpoint[0], ', reached at time ', endpoint[1], '.')

            print('')
            print('    Total cost of vehicle : ', cost)
            print('    Total weight of vehicle : ', weight)
            print('    Capacity of vehicle : ', self.problem.capacities[vehicle_num])
            total_cost += cost
            vehicle_num += 1

        print('')
        print('')
        print('Total cost of all vehicles : ', total_cost)

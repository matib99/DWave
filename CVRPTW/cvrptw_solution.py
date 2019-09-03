import operator

class CVRPTWSolution:
    def __init__(self, problem, sample, solution=None):
        self.problem = problem

        if solution!=None:
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
        weights = self.problem.weights
        solution = self.solution
        vehicle_num = 0

        for vehicle_dests in solution:
            cap = capacities[vehicle_num]
            for (dest, _) in vehicle_dests:
                cap -= weights[dest]
            if cap < 0:
                return False

        dests = self.problem.dests
        answer_dests = [dest for vehicle_dests in solution for (dest, _) in vehicle_dests[1:-1]]
        if len(dests) != len(answer_dests):
            return False

        lists_cmp = set(dests) & set(answer_dests)
        if lists_cmp == len(dests):
            return False

        return True

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
        time_costs = self.problem.time_costs
        solution = self.solution

        vehicle_num = 0
        for vehicle_dests in solution:
            time = 0
            cost = 0

            print('Vehicle number ', vehicle_num, ' : ')

            if len(vehicle_dests) == 0:
                print('    Vehicle is not used.')
                continue

            print('    Startpoint : ', vehicle_dests[0])
            dests_num = 1
            prev = vehicle_dests[0][0]
            for (dest, t) in vehicle_dests[1:len(vehicle_dests) - 1]:

                cost += costs[prev][dest]  # [t]
                # time += time_costs[prev][dest]  # [t]
                print('    Destination number ', dests_num, ' : ', dest, ', reached at time ', t, '.')
                dests_num += 1
                prev = dest

            endpoint = vehicle_dests[len(vehicle_dests) - 1]
            cost += costs[prev][endpoint[0]]  # [t]
            # time += time_costs[prev][endpoint]  # [t]
            print('    Endpoint : ', endpoint[0], ', reached at time ', endpoint[1], '.')

            print('')
            print('    Total cost of vehicle : ', cost)

            vehicle_num += 1

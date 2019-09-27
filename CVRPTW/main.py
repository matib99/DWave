from input import *
from dwave.system.samplers import DWaveSampler
from DWaveSolvers import hybrid_solver
import hybrid

from cvrptw_problem import *
# testowanie...

DWAVE_API_TOKEN = 'token'

endpoint = 'https://cloud.dwavesys.com/sapi'

prb = read_test('tests/medium/medium-5.test')
# prb = read_full_test('tests/compare_tests/medium1-1.test', 25, 'tests/bruxelles')

penalty_const = 10000.
reward_const = -5000.
capacity_const = 100.
time_windows_const = -200.


print("qubo generation")

qdict = prb.get_cvrptw_qubo(penalty_const, reward_const, capacity_const,
                            time_windows_const).dict
printqubo = False
if printqubo:
    for key in qdict.keys():
        ((v, d, t), (v2, d2, t2)) = key
        # if qdict[key] < penalty_const and abs(qdict[(key)]) > 0.1:
        if (v == v2) and (d == d2) and (d != 0) and (t != t2):
            print(key, end='')
            print(" - ", end='')
            print(qdict[key])

print("annealing")

solver = hybrid_solver()
# solver = neal.SimulatedAnnealingSampler()
dwave_sampler = DWaveSampler(token=DWAVE_API_TOKEN, endpoint=endpoint)
response = solver.sample_qubo(qdict)

for sample in response:
    # for key in sample:
        # if sample[key] == 1:
            # print(key)

    solution = CVRPTWSolution(prb, sample)
    solution.description()
    # print(solution.total_cost())
    print(solution.check())
    print('energy: ', energy(qdict, sample, False))
    print()

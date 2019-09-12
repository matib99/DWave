from input import *
from dwave.system.samplers import DWaveSampler

from cvrptw_problem import *
# testowanie...

sapi_token = 'DEV-cba9fa3ac818295889696ec5ac1e2ac0d0e7cb86'

endpoint = 'https://cloud.dwavesys.com/sapi'


prb = read_test('tests/small/small-4.test')

penalty_const = 10000.
reward_const = -1000.
capacity_const = 10.
time_windows_const = -200.


# te parametry trzeba dodać i być może zmienić coś w cvrptwproblem bo się generują błędne rozwiązania
# qdict = prb.get_cvrptw_qubo(1000., 100., 1000., 5., 5.).dict

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

solver = QBSolv()
# solver = neal.SimulatedAnnealingSampler()
dwave_sampler = DWaveSampler(token=sapi_token, endpoint=endpoint)
response = solver.sample_qubo(qdict, solver=dwave_sampler, num_reads=1, solver_limit=2000, auto_scale=True)


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
# solution = CVRPTWSolution(prb, response)

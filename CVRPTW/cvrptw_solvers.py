from qubo_helper import Qubo
from itertools import product
import DWaveSolvers
from cvrptw_solution import CVRPTWSolution
import networkx as nx
import numpy as np
from queue import Queue


# Attributes : VRPProblem
class CVRPTWSolver:
    def __init__(self, problem):
        self.problem = problem

    def set_problem(self, problem):
        self.problem = problem

    def solve(self, only_one_const, order_const, capacity_const,
            solver_type = 'qbsolv', num_reads=50):
        pass


class FullQuboSolver(CVRPTWSolver):
    def solve(self, penalty_const, order_const_m, order_const_r, capacity_const, time_windows_const,
            solver_type = 'qbsolv', num_reads=50):
        dests = len(self.problem.dests)
        vehicles = len(self.problem.capacities)

        limits = [dests for _ in range(vehicles)]

        cvrptw_qubo = self.problem.get_cvrptw_qubo(penalty_const, order_const_m, order_const_r, capacity_const, time_windows_const)
        samples = DWaveSolvers.solve_qubo(cvrptw_qubo.dict, solver_type=solver_type, num_reads=num_reads)
        sample = samples[0]
        solution = CVRPTWSolution(self.problem, sample, limits)
        return solution


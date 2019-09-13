from dwave.system.samplers import DWaveSampler
from dwave.system.composites import EmbeddingComposite
from dwave_qbsolv import QBSolv
from hybrid.reference.kerberos import KerberosSampler
from dimod.reference.samplers import ExactSolver
import hybrid
import dimod
import neal

# Creates hybrid solver.
def hybrid_solver():
    workflow = hybrid.LoopUntilNoImprovement(
        hybrid.RacingBranches(
        hybrid.InterruptableTabuSampler(),
        hybrid.EnergyImpactDecomposer(size=20)
        | hybrid.QPUSubproblemAutoEmbeddingSampler()
        | hybrid.SplatComposer()) | hybrid.ArgMin(), convergence=3)
    return hybrid.HybridSampler(workflow)

def get_solver(solver_type):
    solver = None
    if solver_type == 'standard':
        solver = EmbeddingComposite(DWaveSampler())
    if solver_type == 'hybrid':
        solver = hybrid_solver()
    if solver_type == 'kerberos':
        solver = KerberosSampler()
    if solver_type == 'qbsolv':
        solver = QBSolv()
    return solver

# Solves qubo on qpu.
def solve_qubo(qubo, solver_type = 'qbsolv', limit = 1, num_reads = 50):
    sampler = get_solver(solver_type)

    response = None
    if solver_type == 'hybrid':
        response = sampler.sample_qubo(qubo.dict)
    elif solver_type == 'qbsolv':
        response = sampler.sample_qubo(qubo.dict, num_reads = num_reads)
    elif solver_type == 'standard':
        response = QBSolv().sample_qubo(qubo.dict, solver = sampler, chain_strength = 800, num_reads = num_reads)
    else:
        response = sampler.sample_qubo(qubo.dict, num_reads = num_reads)
    return list(response)[:limit]
    

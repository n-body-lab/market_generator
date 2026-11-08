"""Paired 100-seed default-market credit-floor comparison.

python experiments/credit_floor_comparison.py --seeds 100
"""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean, median
from time import perf_counter
from hivemarket_generator import MarketConfig, generate_market, dumps
from hivemarket_generator.scheduling import verify_solution
from hivemarket_generator.serialization import primitive

FLOORS = (0, 1, 3, 5)


def run(seeds: int = 100) -> dict:
    if seeds < 1:
        raise ValueError('seeds must be positive')
    rows = []
    for seed in range(seeds):
        baseline = None
        digest = None
        for floor in FLOORS:
            config = MarketConfig(seed=seed, minimum_initial_credits=floor)
            start = perf_counter()
            result = generate_market(config)
            elapsed = perf_counter()-start
            if baseline is None:
                baseline = result
                digest = hashlib.sha256(dumps({
                    'market': result.market, 'reference': result.reference_solution,
                    'reference_budgets': result.reference_budgets,
                    'candidates': result.candidates, 'token_routes': result.token_routes,
                    'initial_owners': result.initial_state.owners,
                    'initial_progress': result.initial_state.progress,
                    'initial_histories': result.initial_state.histories,
                }).encode()).hexdigest()
            assert result.market == baseline.market
            assert result.candidates == baseline.candidates and result.token_routes == baseline.token_routes
            assert result.reference_solution == baseline.reference_solution
            assert result.reference_budgets == baseline.reference_budgets
            assert result.initial_state.owners == baseline.initial_state.owners
            assert result.initial_state.progress == baseline.initial_state.progress
            assert result.initial_state.histories == baseline.initial_state.histories
            assert result.initial_state.balances == tuple(max(floor,b) for b in baseline.initial_state.balances)
            final = verify_solution(result.market,result.initial_state,result.reference_solution)
            assert result.feasibility_status == 'verified'
            allocation = result.metadata['credit_allocation']
            additional = sum(result.initial_state.balances)-sum(baseline.initial_state.balances)
            assert allocation['additional_credits_from_floor'] == additional
            rows.append({
                'seed':seed, 'minimum_initial_credits':floor, 'config':primitive(config),
                'structure_and_reference_sha256':digest, 'structure_and_reference_identical':True,
                'reference_budgets':result.reference_budgets, 'initial_credits':result.initial_state.balances,
                'final_credits':final.balances, 'credit_allocation':allocation,
                'total_initial_credits':sum(result.initial_state.balances),
                'additional_credits_from_floor':additional, 'reference_feasible':True,
                'reference_objective':result.reference_solution.objective,
                'optimality_status':result.optimality_status, 'generation_seconds':elapsed,
            })
        if (seed+1) % 10 == 0 or seed+1 == seeds:
            print(f'Verified {seed+1}/{seeds} paired seeds',flush=True)
    summary = []
    for floor in FLOORS:
        group = [r for r in rows if r['minimum_initial_credits']==floor]
        agents = sum(r['config']['n_agents'] for r in group)
        summary.append({
            'minimum_initial_credits':floor, 'markets':len(group), 'agents':agents,
            'fraction_markets_with_zero_credit_agents':mean(r['credit_allocation']['zero_credit_agents']>0 for r in group),
            'fraction_agents_with_zero_credits':sum(r['credit_allocation']['zero_credit_agents'] for r in group)/agents,
            'fraction_agents_zero_credits_unfinished_tasks':sum(
                r['credit_allocation']['zero_credit_agents_with_unfinished_tasks'] for r in group)/agents,
            'mean_total_initial_credits':mean(r['total_initial_credits'] for r in group),
            'median_total_initial_credits':median(r['total_initial_credits'] for r in group),
            'mean_additional_credits_from_floor':mean(r['additional_credits_from_floor'] for r in group),
            'reference_feasibility_rate':mean(r['reference_feasible'] for r in group),
            'mean_generation_seconds':mean(r['generation_seconds'] for r in group),
        })
    return {'protocol':{
        'seeds':list(range(seeds)), 'floors':FLOORS,
        'configuration':'MarketConfig defaults: 6 agents, 12 tokens; exact cap 20000 unchanged',
        'agent_fraction_denominator':'all agents in the condition, not just agents with unfinished tasks',
        'structure_and_reference_identical_across_floors':True,
        'interpretation':'Liquidity/feasibility measurement, not autonomous coordination evidence',
    }, 'summary':summary, 'runs':rows}


def table(data: dict) -> str:
    lines = ['| Floor | Markets with zero credits | Zero-credit agents | Zero-credit, unfinished agents | Mean total credits | Median total credits | Mean added credits | Reference feasible |',
             '|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in data['summary']:
        lines.append(f"| {r['minimum_initial_credits']} | {r['fraction_markets_with_zero_credit_agents']:.1%} | "
                     f"{r['fraction_agents_with_zero_credits']:.1%} | {r['fraction_agents_zero_credits_unfinished_tasks']:.1%} | "
                     f"{r['mean_total_initial_credits']:.2f} | {r['median_total_initial_credits']:.2f} | "
                     f"{r['mean_additional_credits_from_floor']:.2f} | {r['reference_feasibility_rate']:.0%} |")
    return '\n'.join(lines)+'\n'


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds',type=int,default=100)
    parser.add_argument('--output',type=Path,default=Path('experiments/data/credit_floor_comparison.json.gz'))
    args=parser.parse_args()
    data=run(args.seeds)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(primitive(data),indent=2,allow_nan=False)+'\n'
    if args.output.suffix=='.gz':
        import gzip
        args.output.write_bytes(gzip.compress(text.encode(),mtime=0))
    else:
        args.output.write_text(text)
    summary_path=args.output.with_name(args.output.name.removesuffix('.gz').removesuffix('.json')+'.md')
    summary_path.write_text('# Paired credit-floor comparison\n\n'+table(data))
    print(table(data))

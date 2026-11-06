"""Controlled studies A-D and preset distributions; deterministic inputs, timed runs.

python experiments/characterise.py --seeds 100 --output experiments/data/characterisation.json
"""
import argparse
from dataclasses import replace
import json
from pathlib import Path
from statistics import mean, median
from time import perf_counter
from hivemarket_generator import (
    MarketConfig, GenerationFailure, generate_market, prepare_market, economic_family,
    analyse_fragility, count_feasible_sequences, financing_dependence, solve_exact)
from hivemarket_generator.optimization import reference_quality
from hivemarket_generator.serialization import primitive


def record(config: MarketConfig, fragility: bool = False) -> dict:
    start = perf_counter()
    try:
        r = generate_market(config)
    except GenerationFailure as error:
        return {'seed': config.seed, 'config': config, 'success': False, 'attempts': error.attempts,
                'generation_seconds': perf_counter()-start,
                'last_realised': error.last_realised_properties}
    elapsed = perf_counter()-start
    start = perf_counter()
    exact = solve_exact(r.market, r.initial_state, 2000, r.reference_solution)
    row = {'seed': config.seed, 'config': config, 'success': True,
           'attempts': r.metadata['generation_attempts'], 'generation_seconds': elapsed,
           'requested': r.metadata['requested_properties'], 'realised': r.metadata['realised_properties'],
           'routing': r.difficulty['routing'], 'resources': r.difficulty['resources'],
           'reference': r.reference_solution.objective, 'best': exact.best_solution.objective,
           'solver_seconds': perf_counter()-start, 'solver_conclusion': exact.conclusion,
           'solver_expanded': exact.expanded_states, 'solver_discovered': exact.discovered_states,
           'lower_bound': exact.lower_bound, 'gap': exact.optimality_gap,
           'quality': reference_quality(r.reference_solution, exact.best_solution if exact.status == 'optimal' else None),
           'financing': financing_dependence(r)}
    if fragility:
        row['fragility'] = analyse_fragility(r.market, r.initial_state, 1000)
    return row


def run(seeds: int) -> dict:
    data = {'protocol': {'seeds': list(range(seeds)), 'solver_state_cap': 2000,
                         'fragility_state_cap_per_search': 1000,
                         'generation_attempt_limit': 100,
                         'interpretation': 'Full-information economic structure; no agent behaviour or discovery traces.'},
            'presets': [], 'A': [], 'A_conflict': [], 'B': [], 'C': [], 'D': []}
    for level in ('easy', 'medium', 'hard'):
        for seed in range(seeds):
            # Distribution study avoids costly optimisation for six-agent markets.
            config = MarketConfig.preset(level, seed=seed, exact_state_limit=0)
            start = perf_counter()
            try:
                r = generate_market(config)
                data['presets'].append({'level': level, 'seed': seed, 'success': True,
                                        'attempts': r.metadata['generation_attempts'],
                                        'generation_seconds': perf_counter()-start,
                                        'realised': r.metadata['realised_properties'],
                                        'reference': r.reference_solution.objective})
            except GenerationFailure as error:
                data['presets'].append({'level': level, 'seed': seed, 'success': False,
                                        'attempts': error.attempts, 'generation_seconds': perf_counter()-start})
        print('presets', level, flush=True)
    # Negative control: targeted price modifications force an indirect dependency,
    # conflicting with an exact all-direct target. Report exhaustion, do not relax.
    for seed in range(seeds):
        data['A_conflict'].append(record(MarketConfig(
            n_agents=4, n_tokens=3, task_dependency_range=(1, 2),
            price_range=(1, 20), price_modifications=2, budget_leeway=.2,
            structural_constraints={'mean_dependency_depth': (1, 1)},
            seed=seed, exact_state_limit=0)))
    print('A negative control', flush=True)
    for interval in ((1, 1), (1.5, 2), (2, 3)):
        for seed in range(seeds):
            config = MarketConfig(n_agents=4, n_tokens=3, task_dependency_range=(1, 2),
                                  price_range=(1, 20), price_modifications=0, budget_leeway=.2,
                                  structural_constraints={'mean_dependency_depth': interval},
                                  seed=seed, exact_state_limit=0)
            data['A'].append(record(config))
        print('A', interval, flush=True)
    for seed in range(seeds):
        # Paired structure is identical: only balances change with leeway.
        base = economic_family('fragile', seed)
        for leeway in (0, 1, 4):
            r = prepare_market(base.market, replace(base.config, budget_leeway=leeway, exact_state_limit=0))
            data['B'].append({'seed': seed, 'leeway': leeway, 'market': r.market,
                              'budgets': r.initial_state.balances,
                              'fragility': analyse_fragility(r.market, r.initial_state, 1000),
                              'sequences': count_feasible_sequences(r.market, r.initial_state, 3, 10000),
                              'financing': financing_dependence(r)})
    print('B complete', flush=True)
    for concentration in (.1, 1., 5.):
        for overlap in ((0, .5), (.8, 1.)):
            for seed in range(seeds):
                config = MarketConfig(n_agents=3, n_tokens=3, task_dependency_range=(1, 2), seed=seed,
                                      ownership_concentration=concentration, budget_leeway=0,
                                      structural_constraints={'shared_demand_fraction': overlap},
                                      exact_state_limit=0)
                row = record(config, fragility=True)
                row['concentration'] = concentration
                row['overlap_target'] = overlap
                data['C'].append(row)
            print('C', concentration, overlap, flush=True)
    for n, k in ((2, 2), (3, 2), (3, 3), (4, 3)):
        for seed in range(seeds):
            config = MarketConfig(n_agents=n, n_tokens=k, task_dependency_range=(1, min(k, 3)),
                                  seed=seed, exact_state_limit=0)
            data['D'].append(record(config))
        print('D', n, k, flush=True)
    return data


def distribution(values: list[float]) -> dict | None:
    if not values:
        return None
    values = sorted(values)
    return {'n': len(values), 'mean': mean(values), 'median': median(values),
            'min': values[0], 'p10': values[int(.1*(len(values)-1))],
            'p90': values[int(.9*(len(values)-1))], 'max': values[-1]}


def summary(data: dict) -> dict:
    output = {}
    for section in ('presets', 'A', 'A_conflict', 'B', 'C', 'D'):
        groups = {}
        for row in data[section]:
            if section == 'presets': label = row['level']
            elif section in ('A', 'A_conflict'): label = str(row['config']['structural_constraints']['mean_dependency_depth'])
            elif section == 'B': label = str(row['leeway'])
            elif section == 'C': label = str((row['concentration'], row['overlap_target']))
            else: label = str((row['config']['n_agents'], row['config']['n_tokens']))
            groups.setdefault(label, []).append(row)
        output[section] = {}
        for label, rows in groups.items():
            valid = [r for r in rows if r.get('success', True)]
            exact = [r for r in valid if r.get('solver_conclusion') == 'optimal']
            fragile = [r['fragility']['decision_fragility'] for r in valid if 'fragility' in r
                       and r['fragility']['decision_fragility'] is not None]
            output[section][label] = {
                'attempted': len(rows), 'accepted': len(valid), 'failure_rate': 1-len(valid)/len(rows),
                'mean_attempts': mean(r.get('attempts', 1) for r in rows),
                'constraint_satisfaction_rate_among_returned': 1.0 if valid else None,
                'candidate_acceptance_rate': len(valid)/sum(r.get('attempts', 1) for r in rows),
                'generation_seconds': distribution([r['generation_seconds'] for r in rows if 'generation_seconds' in r]),
                'solver_seconds': distribution([r['solver_seconds'] for r in valid if 'solver_seconds' in r]),
                'optimal_count': len(exact),
                'reference_optimal_count': sum(r['quality']['reference_is_optimal'] for r in exact),
                'fragility': distribution(fragile), 'fragility_available': len(fragile),
                'affordable_actions': distribution([r['fragility']['affordable_actions'] for r in valid if 'fragility' in r]),
                'preserving_actions': distribution([r['fragility']['preserving_actions'] for r in valid if 'fragility' in r]),
                'sequence_count_horizon_3': distribution([r['sequences']['count'] for r in valid if 'sequences' in r and r['sequences']['count'] is not None]),
                'properties': {name: distribution([r['realised'][name] for r in valid if 'realised' in r])
                               for name in ('indirect_dependency_fraction', 'mean_dependency_depth', 'ownership_hhi',
                                            'shared_demand_fraction', 'shared_intermediaries', 'competitive_alternative_fraction')},
            }
    return output


def markdown_summary(statistics: dict) -> str:
    lines = ['# Controlled market studies: measured summary', '',
             'See difficulty_validation.md for definitions, configurations and limitations.', '']
    for study, groups in statistics.items():
        lines += [f'## {study}', '',
                  '| Condition | Returned / requested | Mean attempts | Mean generation ms | Mean depth | Mean HHI | Mean F (available n) | Proven optima | Reference optimal |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for label, row in groups.items():
            def avg(value):
                return f"{value['mean']:.3f}" if value else '—'
            depth = row['properties']['mean_dependency_depth']
            hhi = row['properties']['ownership_hhi']
            ms = f"{1000*row['generation_seconds']['mean']:.2f}" if row['generation_seconds'] else '—'
            lines.append(f"| {label} | {row['accepted']}/{row['attempted']} | {row['mean_attempts']:.2f} | {ms} | "
                         f"{avg(depth)} | {avg(hhi)} | {avg(row['fragility'])} ({row['fragility_available']}) | "
                         f"{row['optimal_count']} | {row['reference_optimal_count']} |")
        lines.append('')
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', type=int, default=100)
    parser.add_argument('--output', type=Path, default=Path('experiments/data/characterisation.json.gz'))
    args = parser.parse_args()
    if args.seeds < 1:
        parser.error('seeds must be positive')
    data = primitive(run(args.seeds))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, allow_nan=False)+'\n'
    if args.output.suffix == '.gz':
        import gzip
        args.output.write_bytes(gzip.compress(text.encode(), mtime=0))
    else:
        args.output.write_text(text)
    summary_path = args.output.with_name(args.output.name.removesuffix('.gz').removesuffix('.json') + '_summary.json')
    summary_path.write_text(json.dumps(summary(data), indent=2, allow_nan=False)+'\n')
    summary_path.with_suffix('.md').write_text(markdown_summary(summary(data)))
    print('Saved', args.output, summary_path)

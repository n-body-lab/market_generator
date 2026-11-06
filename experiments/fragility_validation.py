"""Small V0.3 validation: decoy sensitivity and genuinely goal-relevant choices."""
import json
from dataclasses import replace
from pathlib import Path
from hivemarket_generator import economic_family, analyse_fragility, dumps
from hivemarket_generator.serialization import primitive


def run() -> dict:
    decoys = []
    for count in (1, 3, 5, 10, 20):
        r = economic_family('highly_constrained', seed=42, decoys=count)
        f = analyse_fragility(r.market, r.initial_state)
        decoys.append({'decoys': count, 'full_fragility': f['full_affordable_action_fragility'],
                       'goal_relevant_fragility': f['goal_relevant_fragility'],
                       'affordable_actions': f['affordable_actions'], 'goal_relevant_actions': f['goal_relevant_actions']})
    choices = []
    for seed in range(5):
        r = economic_family('goal_relevant_fragile', seed)
        choices.append({'seed': seed, 'prices': r.market.prices, 'balances': r.initial_state.balances,
                        'analysis': analyse_fragility(r.market, r.initial_state)})
    return {'criterion': 'Token has an unmet agent-token requirement in the pre-action state.',
            'decoy_study': decoys, 'goal_relevant_family': choices}


if __name__ == '__main__':
    output = Path('experiments/data/fragility_v03.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    data = run()
    output.write_text(json.dumps(primitive(data), indent=2)+'\n')
    lines = ['# V0.3 fragility validation', '', '| Decoys | Full affordable-action fragility | Goal-relevant fragility |',
             '|---:|---:|---:|']
    lines += [f"| {r['decoys']} | {r['full_fragility']:.6f} | {r['goal_relevant_fragility']:.6f} |" for r in data['decoy_study']]
    lines += ['', 'The two-agent goal-relevant family has two unmet tasks, two relevant affordable actions,',
              'one destructive action and one preserving action at each seed 0–4: both fragilities are 0.5.',
              'These are full-information economic measurements, not observed agent difficulty.', '']
    output.with_suffix('.md').write_text('\n'.join(lines))
    r = economic_family('goal_relevant_fragile', seed=42)
    r = replace(r, difficulty=r.difficulty | {'decision_analysis': analyse_fragility(r.market, r.initial_state)},
                metadata=r.metadata | {'example_family': 'goal_relevant_fragile'})
    Path('examples/markets/goal_relevant_fragile.json').write_text(dumps(r)+'\n')
    print(output)

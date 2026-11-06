"""Reproduce exact economic families; writes locally, no agents involved."""
from pathlib import Path
from hivemarket_generator import economic_family, analyse_fragility, dumps

if __name__ == '__main__':
    for name in ('robust', 'fragile', 'highly_constrained'):
        result = economic_family(name, seed=42)
        analysis = analyse_fragility(result.market, result.initial_state)
        Path(f'{name}.json').write_text(dumps({'result': result, 'fragility': analysis}))
        print(name, analysis['decision_fragility'])

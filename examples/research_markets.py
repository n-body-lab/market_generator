"""Export exact economic families and separately controlled structural presets."""
from dataclasses import replace
from pathlib import Path
from hivemarket_generator import MarketConfig, generate_market, economic_family, analyse_fragility, dumps


def write_examples(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for label, family in [('easy', 'robust'), ('medium', 'fragile'), ('hard', 'highly_constrained')]:
        r = economic_family(family, seed=42)
        r = replace(r, difficulty=r.difficulty | {'decision_analysis': analyse_fragility(r.market, r.initial_state)},
                    metadata=r.metadata | {'example_family': family})
        (output / f'{label}.json').write_text(dumps(r)+'\n')
        structural = generate_market(MarketConfig.preset(label, seed=42, exact_state_limit=0))
        (output / f'structural_{label}.json').write_text(dumps(structural)+'\n')


if __name__ == '__main__':
    write_examples(Path('examples/markets'))

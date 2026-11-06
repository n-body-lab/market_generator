"""Scientific regression checks using hand structures and archived measured cases."""
import gzip
import json
from pathlib import Path
from dataclasses import replace
import pytest
from hivemarket_generator import *

ROOT = Path(__file__).parents[1]


def test_hand_depth_constraints_and_incompatible_request():
    m = Market(((0, 20, 20), (1, 0, 20), (10, 1, 0)),
               (frozenset(), frozenset(), frozenset({0})), (0,))
    c = MarketConfig(n_agents=3, n_tokens=1, task_dependency_range=(0, 1),
                     structural_constraints={'mean_dependency_depth': (2, 2),
                                             'indirect_dependency_fraction': (1, 1)})
    r = prepare_market(m, c)
    assert r.metadata['realised_properties']['mean_dependency_depth'] == 2
    # By inspection: 0->1->2 costs 2, while the direct trade costs 10.
    assert r.market.prices[1][0] + r.market.prices[2][1] < r.market.prices[2][0]
    with pytest.raises(GenerationFailure):
        prepare_market(m, replace(c, structural_constraints={'mean_dependency_depth': (1, 1)}))


def test_archived_studies_keep_failures_pairing_and_unknowns_visible():
    data = json.loads(gzip.decompress((ROOT/'experiments/data/characterisation.json.gz').read_bytes()))
    assert len(data['presets']) == 300
    assert len(data['A']) == len(data['B']) == 300
    assert len(data['C']) == 600 and len(data['D']) == 400
    for row in data['A'] + data['C']:
        if row['success']:
            for metric, (lo, hi) in row['requested'].items():
                assert lo <= row['realised'][metric] <= hi
    assert any(not row['success'] for row in data['A'])
    assert all(not row['success'] for row in data['A_conflict'])
    for seed in range(100):
        pairs = [r for r in data['B'] if r['seed'] == seed]
        assert all(row['market'] == pairs[0]['market'] for row in pairs)
        assert pairs[0]['fragility']['decision_fragility'] == .5
        assert pairs[1]['fragility']['decision_fragility'] == 0
    assert any(r['fragility']['decision_fragility'] is None for r in data['C'])
    assert any(r['quality']['reference_is_optimal'] is False for r in data['D'])


def test_research_example_exports_are_replayable():
    for path in (ROOT/'examples/markets').glob('*.json'):
        r = decode_result(loads(path.read_text()))
        assert r.status in ('optimal', 'feasible')
    expected = {'easy': 0, 'medium': .5, 'hard': 5/6}
    for label, value in expected.items():
        r = decode_result(loads((ROOT/f'examples/markets/{label}.json').read_text()))
        assert analyse_fragility(r.market, r.initial_state)['decision_fragility'] == value

import importlib.util
from pathlib import Path


def test_reproducible_experiment_effects():
    spec = importlib.util.spec_from_file_location('experiments', Path(__file__).parents[1] / 'experiments/run.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    a = module.routing_experiment([0, 1])
    assert a == module.routing_experiment([0, 1])
    for offset in (0, 3):
        assert [r['routing']['maximum_token_walk_length'] for r in a[offset:offset+3]] == [1, 2, 3]
    b = module.resource_experiment([0, 1])
    assert b[0]['feasible_sequences'] == 1
    assert b[2]['feasible_sequences'] == 2
    c = module.joint_experiment([0, 1])
    assert all(r['optimality_status'] == 'optimal' and r['best_joint'] < r['independent_reference'] for r in c)

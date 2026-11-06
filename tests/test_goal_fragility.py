from dataclasses import replace
import pytest
from hivemarket_generator import *
from hivemarket_generator.models import complete
from hivemarket_generator.simulation import execute, replay
from hivemarket_generator.scheduling import verify_solution


@pytest.mark.parametrize('decoys', [1, 3, 5, 10, 20])
def test_decoys_inflate_full_space_not_goal_relevant_fragility(decoys):
    r = economic_family('highly_constrained', seed=42, decoys=decoys)
    f = analyse_fragility(r.market, r.initial_state)
    assert f['decision_fragility'] == f['full_affordable_action_fragility'] == decoys/(decoys+1)
    assert f['goal_relevant_fragility'] == 0
    assert f['goal_relevant_actions'] == f['goal_relevant_preserving_actions'] == 1
    assert f['irrelevant_actions'] == decoys
    assert f['goal_relevant_fragility_status'] == 'exact'


@pytest.mark.parametrize('seed', range(5))
def test_goal_relevant_choices_have_hand_verified_economic_consequences(seed):
    r = economic_family('goal_relevant_fragile', seed)
    m, initial = r.market, r.initial_state
    p = m.prices[0][1]
    assert initial.balances == (p+1, p+2)
    assert all(task - seen for task, seen in zip(m.tasks, initial.progress))
    f = analyse_fragility(m, initial)
    assert f['affordable_actions'] == f['goal_relevant_actions'] == 2
    assert f['goal_relevant_fragility'] == f['decision_fragility'] == .5
    assert f['goal_relevant_destructive_actions'] == f['goal_relevant_preserving_actions'] == 1
    # Independent arithmetic: buying first empties agent 0's balance. It then
    # owns both tokens but cannot pay the seller's one-credit message fee.
    bad = execute(m, initial, Transfer(1, 1, 0))
    assert bad.balances == (0, 2*p+1) and bad.owners == (0, 0)
    assert not complete(m, bad)
    for token in range(2):
        with pytest.raises(ValueError, match='unaffordable'):
            execute(m, bad, Transfer(token, 0, 1))
    good = replay(m, initial, (Transfer(0, 0, 1), Transfer(1, 1, 0)))
    assert complete(m, good) and good.balances == (p-1, p)
    verify_solution(m, initial, r.reference_solution)
    assert r.status == 'optimal'


def test_relevance_is_pre_action_and_includes_forwarding_not_only_correct_buyers():
    m = Market(((0, 2, 2), (2, 0, 2), (2, 2, 0)),
               (frozenset(), frozenset(), frozenset({0})), (0,))
    state = initial_state(m, (10, 10, 10))
    f = analyse_fragility(m, state)
    forwarded = next(a for a in f['actions'] if a['action'].buyer == 1)
    assert forwarded['goal_relevant']  # buyer has no task, but can forward token 0
    final = execute(m, state, Transfer(0, 0, 2))
    f2 = analyse_fragility(m, final)
    assert f2['goal_relevant_fragility'] is None
    assert f2['goal_relevant_fragility_status'] == 'no_goal_relevant_affordable_actions'


def test_goal_subset_handles_unknowns_independently():
    r = economic_family('highly_constrained', decoys=3)
    f = analyse_fragility(r.market, r.initial_state, state_limit=0)
    # A direct completion witness is recognised even at zero search expansions.
    assert f['decision_fragility'] is None
    assert f['goal_relevant_fragility'] == 0
    r = economic_family('goal_relevant_fragile')
    f = analyse_fragility(r.market, r.initial_state, state_limit=0)
    assert f['goal_relevant_fragility'] is None
    assert f['goal_relevant_unclassified_actions'] == 2

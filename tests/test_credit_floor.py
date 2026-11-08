from dataclasses import replace
from pathlib import Path
import pytest
from hivemarket_generator import *
from hivemarket_generator.credits import initial_endowments, add_leeway
from hivemarket_generator.scheduling import verify_solution


@pytest.mark.parametrize('reference,leeway,floor,expected', [
    ((0,5,10),.2,0,(0,6,12)), ((0,5,10),.2,3,(3,6,12)),
    ((0,),1.,3,(3,)), ((1,2,8),0,5,(5,5,8)),
])
def test_relative_floor_after_leeway(reference,leeway,floor,expected):
    assert initial_endowments(reference,leeway,'relative',floor) == expected


def test_absolute_and_per_agent_leeway_preserved():
    assert initial_endowments((0,1,5),.2,'absolute',3) == (3,3,6)
    assert initial_endowments((0,1,5),(0,2,.4),'absolute',3) == (3,3,6)
    assert initial_endowments((0,1,5),(1,.5,.2),'relative',0) == add_leeway((0,1,5),(1,.5,.2),'relative')


@pytest.mark.parametrize('value', [-1, 1., .5, True, False, '3', None])
def test_floor_requires_nonnegative_integer(value):
    with pytest.raises(ValueError, match='minimum_initial_credits'):
        MarketConfig(minimum_initial_credits=value)
    with pytest.raises(ValueError, match='minimum_initial_credits'):
        initial_endowments((0,),.2,'relative',value)


def test_zero_floor_preserves_entire_historical_seeded_result_except_new_fields():
    # Existing committed result from before this feature: a frozen compatibility oracle.
    path=Path(__file__).parents[1]/'examples/markets/offer_buy_market.json'
    historical=loads(path.read_text())
    assert 'minimum_initial_credits' not in historical['config']
    config=MarketConfig(**historical['config'])
    actual=loads(dumps(generate_market(config)))
    assert actual['config'].pop('minimum_initial_credits') == 0
    actual['metadata'].pop('credit_allocation')
    assert actual == historical
    restored=decode_result(historical)
    assert restored.config.minimum_initial_credits == 0


@pytest.mark.parametrize('mode', ['relative','absolute'])
def test_floor_only_changes_initial_endowments_not_structure_or_reference(mode):
    c=MarketConfig(n_agents=3,n_tokens=2,task_dependency_range=(1,2),seed=42,
                   leeway_mode=mode,exact_state_limit=0)
    baseline=generate_market(c)
    prior=baseline.initial_state.balances
    for floor in (0,1,3,5,20):
        r=generate_market(replace(c,minimum_initial_credits=floor))
        assert r.market == baseline.market
        assert r.reference_solution == baseline.reference_solution
        assert r.reference_budgets == baseline.reference_budgets
        assert r.token_routes == baseline.token_routes and r.candidates == baseline.candidates
        assert all(b>=old for b,old in zip(r.initial_state.balances,prior))
        assert r.initial_state.balances == tuple(max(floor,b) for b in baseline.initial_state.balances)
        verify_solution(r.market,r.initial_state,r.reference_solution)
        verify_protocol_solution(r.market,r.initial_state,r.reference_solution)
        assert dumps(decode_result(loads(dumps(r)))) == dumps(r)
        prior=r.initial_state.balances


def test_metadata_zero_agents_unfinished_tasks_and_actual_floor_effect():
    # Agent 0 starts with no budget, sells first to finance its required purchase.
    m=Market(((0,2),(2,0)),(frozenset({1}),frozenset({0})),(0,1),
             communication=ExecutionMessages(0,0),communication_protocol='legacy_fixed_messages')
    c=MarketConfig(n_agents=2,n_tokens=2,task_dependency_range=(1,1),budget_leeway=.2,
                   communication_protocol='legacy_fixed_messages',buyer_messages=0,exact_state_limit=0)
    r=prepare_market(m,c)
    assert r.reference_budgets == (0,2)
    assert r.initial_state.balances == (0,3)
    a=r.metadata['credit_allocation']
    assert a['zero_credit_agents'] == a['zero_credit_agents_with_unfinished_tasks'] == 1
    higher=prepare_market(m,replace(c,minimum_initial_credits=3))
    b=higher.metadata['credit_allocation']
    assert higher.reference_budgets == (0,2) and higher.initial_state.balances == (3,3)
    assert b['reference_budgets'] == (0,2) and b['initial_credits_before_floor'] == (0,3)
    assert b['initial_credits'] == (3,3) and b['minimum_initial_credits'] == 3
    assert b['agents_increased_by_floor'] == 1 and b['additional_credits_from_floor'] == 3
    assert b['zero_credit_agents'] == b['zero_credit_agents_with_unfinished_tasks'] == 0
    assert b['zero_credit_agents_before_floor_with_unfinished_tasks'] == 1


def test_import_enforces_floor_instead_of_accepting_old_formula_or_forged_reference():
    r=generate_market(MarketConfig(n_agents=3,n_tokens=2,task_dependency_range=(1,2),
                                 minimum_initial_credits=10,exact_state_limit=0))
    data=loads(dumps(r))
    data['initial_state']['balances'][0] += 1
    with pytest.raises(ValueError,match='reference budgets'):
        decode_result(data)
    data=loads(dumps(r))
    data['config']['minimum_initial_credits']=0
    with pytest.raises(ValueError,match='reference budgets'):
        decode_result(data)
    data=loads(dumps(r))
    data['reference_budgets'][0] += 1
    with pytest.raises(ValueError,match='reference budgets'):
        decode_result(data)

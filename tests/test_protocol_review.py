"""Adversarial review regressions, independent arithmetic and tiny exhaustive checks."""
from dataclasses import replace
from itertools import product
import pytest
from hivemarket_generator import *
from hivemarket_generator.models import complete
from hivemarket_generator.scheduling import Solution
from hivemarket_generator.offers import StandingOffer, uses_offer_protocol


def base_market(**kwargs):
    return Market(((0, 2), (2, 0)), (frozenset(), frozenset({0})), (0,), **kwargs)


def test_prepare_rejects_declared_offer_config_with_zero_fee_market():
    m = base_market(communication=ExecutionMessages(0, 0))
    config = MarketConfig(n_agents=2, n_tokens=1, task_dependency_range=(0, 1), exact_state_limit=0)
    with pytest.raises(ValueError, match='protocol mismatch'):
        prepare_market(m, config)
    explicit_legacy = replace(config, communication_protocol='legacy_fixed_messages', buyer_messages=0)
    assert prepare_market(m, explicit_legacy).metadata['communication_protocol'] == 'legacy_fixed_messages'


def test_equal_fee_numbers_do_not_override_explicit_legacy_identity():
    config = MarketConfig(n_agents=2, n_tokens=1, task_dependency_range=(1, 1),
                          communication_protocol='legacy_fixed_messages')
    r = generate_market(config)
    assert r.market.communication == ExecutionMessages(1, 0)
    assert not uses_offer_protocol(r.market)
    assert r.reference_solution.protocol_actions is None
    assert r.metadata['communication_protocol'] == config.communication_protocol
    assert decode_result(loads(dumps(r))).market == r.market
    current = prepare_market(replace(r.market, communication_protocol='offer_buy'),
                             replace(config, communication_protocol='offer_buy'))
    assert r.metadata['exact_search']['proof_scope'] != current.metadata['exact_search']['proof_scope']
    with pytest.raises(ValueError, match='protocol mismatch'):
        prepare_market(r.market, replace(config, communication_protocol='offer_buy'))


def test_fee_disagreement_rejected_even_when_both_select_legacy():
    m = base_market(communication=ExecutionMessages(0, 0))
    config = MarketConfig(n_agents=2, n_tokens=1, task_dependency_range=(1, 1),
                          communication_protocol='legacy_fixed_messages')
    with pytest.raises(ValueError, match='fee mismatch'):
        prepare_market(m, config)


def test_invalid_explicit_protocol_rejected_and_old_imports_supported():
    from hivemarket_generator.validation import validate_market
    m = base_market(communication=ExecutionMessages(0, 0), communication_protocol='offer_buy')
    with pytest.raises(ValueError, match='fee policy'):
        validate_market(m)
    old = {'prices': [[0,2],[2,0]], 'tasks': [[],[0]], 'initial_owners': [0],
           'communication': {'buyer': 0, 'seller': 0}}
    assert decode_market(old).communication_protocol == 'legacy_fixed_messages'
    r = generate_market(MarketConfig(n_agents=2,n_tokens=1,task_dependency_range=(1,1)))
    raw = loads(dumps(r))
    raw['market']['communication_protocol'] = 'legacy_fixed_messages'
    with pytest.raises(ValueError, match='protocol mismatch'):
        decode_result(raw)
    raw = loads(dumps(r))
    raw['market'].pop('communication_protocol')
    raw['config'].pop('communication_protocol')
    assert decode_result(raw).market.communication_protocol == 'offer_buy'


@pytest.mark.parametrize('change', ['progress', 'history', 'owner', 'negative', 'counter'])
def test_empty_protocol_verification_cannot_certify_malformed_state(change):
    m = base_market()
    initial = initial_state(m, (0,3))
    if change == 'progress': bad = replace(initial, progress=(frozenset(), frozenset({0})))
    elif change == 'history': bad = replace(initial, histories=((0,1,0),))
    elif change == 'owner': bad = replace(initial, owners=(1,))
    elif change == 'negative': bad = replace(initial, balances=(0,-1))
    else: bad = replace(initial, execution_messages=3)
    snapshot = OfferState(bad)
    with pytest.raises(ValueError):
        verify_protocol_solution(m, bad, Solution((), (0,0,0), ()))
    with pytest.raises(ValueError):
        validate_offer_execution(m, snapshot, snapshot, ())
    with pytest.raises(ValueError):
        replay_protocol(m, snapshot, ())


def test_empty_legacy_replay_and_invalid_offer_checkpoint_rejected():
    m = base_market(communication=ExecutionMessages(0, 0))
    with pytest.raises(ValueError, match='OFFER/BUY'):
        replay_protocol(m, initial_state(m), ())
    m = base_market()
    snapshot = OfferState(initial_state(m,(0,3)), (StandingOffer(Offer(0,0,0,1),'invalid'),), (), 1)
    with pytest.raises(ValueError):
        validate_offer_execution(m, snapshot, snapshot, ())
    duplicate = replace(snapshot, offers=(StandingOffer(Offer(0,0,0,1)),)*2, offer_messages=2)
    with pytest.raises(ValueError):
        replay_protocol(m, duplicate, ())
    with pytest.raises(ValueError):
        replay_protocol(m, replace(snapshot, offers=(), offer_messages=-1), ())


def test_downstream_demand_precedes_intermediary_acquisition():
    m = Market(((0,3,9),(4,0,2),(5,6,0)),
               (frozenset({0}), frozenset(), frozenset()), (2,))
    plan = (Offer(0,0,1,0), Offer(1,0,2,1), Buy(1,1), Buy(0,0))
    assert protocol_budgets(m,plan) == (4,3,0)
    initial = initial_state(m,(4,3,0))
    demanded = replay_protocol(m,initial,plan[:1])
    assert demanded.economy.owners == (2,) and demanded.offers[0].status == 'active'
    acquired = replay_protocol(m,demanded,plan[1:3])
    assert acquired.economy.owners == (1,) and acquired.offers[0].status == 'active'
    final = replay_protocol(m,acquired,plan[3:])
    validate_offer_execution(m,OfferState(initial),final,plan)
    assert final.economy.balances == (0,3,2)  # two credits consumed; payments 2 and 3 redistributed
    assert final.economy.histories == ((2,1,0),)
    solution = Solution((Transfer(0,2,1),Transfer(0,1,0)),(2,2,5),plan)
    assert verify_protocol_solution(m,initial,solution) == final
    assert complete(m,final.economy)


def test_obsolete_offer_never_forces_purchase_or_allows_seller_to_initiate_it():
    m = Market(((0,3,4),(2,0,3),(5,2,0)),
               (frozenset({0}),frozenset(),frozenset()),(2,))
    initial = OfferState(initial_state(m,(20,20,20)))
    first = (Offer(0,0,1,0), Offer(1,0,2,0), Buy(1,0))
    owned = replay_protocol(m,initial,first)
    assert complete(m,owned.economy) and owned.offers[0].status == 'active'
    second = (Offer(2,0,0,1), Buy(2,1))
    changed = replay_protocol(m,owned,second)
    assert changed.economy.owners == (1,)
    assert changed.offers[0].status == 'active' and changed.economy.progress[0] == frozenset({0})
    with pytest.raises(ValueError, match='buyer'):
        apply_protocol(m,changed,Buy(0,1))  # prospective seller cannot compel original buyer
    withdrawn = apply_protocol(m,changed,Withdraw(0,0))
    assert withdrawn.economy.balances == changed.economy.balances
    assert withdrawn.economy.owners == (1,)
    validate_offer_execution(m,initial,withdrawn,first+second+(Withdraw(0,0),))


@pytest.mark.parametrize('price', [1,2,3])
def test_fixed_plan_budget_minimum_against_exhaustive_endowments(price):
    m = Market(((0,price),(price+1,0)), (frozenset(),frozenset()), (0,1))
    plans = [
        (Offer(0,0,0,1),Buy(0,1)),
        (Offer(0,1,1,0),Offer(1,0,0,1),Buy(1,1),Buy(0,0)),
        (Offer(0,0,1,0),Withdraw(0,0)),
        (Offer(0,0,0,1),Buy(0,1),Offer(1,0,1,0),Buy(1,0)),
    ]
    for plan in plans:
        required = protocol_budgets(m,plan)
        for balances in product(range(max(required)+2), repeat=2):
            try:
                final = replay_protocol(m,initial_state(m,balances),plan)
                validate_offer_execution(m,OfferState(initial_state(m,balances)),final,plan)
                feasible = True
            except ValueError:
                feasible = False
            assert feasible == all(b>=r for b,r in zip(balances,required))


def test_prepaid_pending_offer_is_not_an_empty_offer_solver_state():
    m = base_market()
    pending = replay_protocol(m,initial_state(m,(0,3)),(Offer(0,0,0,1),))
    assert pending.economy.balances == (0,2)
    assert complete(m,apply_protocol(m,pending,Buy(0,1)).economy)
    # Projecting away the already-paid offer changes the problem: a new OFFER
    # plus BUY costs three, while the pending BUY costs only two.
    assert solve_exact(m,pending.economy).conclusion == 'infeasible'
    with pytest.raises(ValueError, match='empty initial offers'):
        solve_exact(m,pending)


def test_per_agent_leeway_tuple_length_fails_at_configuration_boundary():
    with pytest.raises(ValueError, match='leeway'):
        MarketConfig(n_agents=2, budget_leeway=(.2,))
    # Scalar broadcasting and an actual two-agent vector are both supported.
    assert MarketConfig(n_agents=2, budget_leeway=.2).budget_leeway == .2
    r = generate_market(MarketConfig(n_agents=2,n_tokens=1,task_dependency_range=(1,1),
                                     budget_leeway=(0,1),leeway_mode='absolute'))
    assert r.initial_state.balances == tuple(b+x for b,x in zip(r.reference_budgets,(0,1)))

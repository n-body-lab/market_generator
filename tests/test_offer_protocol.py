from dataclasses import replace
import pytest
from hivemarket_generator import *
from hivemarket_generator.models import complete
from hivemarket_generator.scheduling import Solution, verify_solution
from hivemarket_generator.offers import reference_protocol
from hivemarket_generator.validation import audit_solution


def market():
    # buyer-major asymmetric prices
    return Market(((0, 3, 4), (2, 0, 3), (5, 2, 0)),
                  (frozenset({0}), frozenset({0}), frozenset({0})), (2,))


def step(m, state, action):
    after = apply_protocol(m, state, action)
    validate_offer_execution(m, state, after, (action,))
    return after


def test_offer_cost_no_reservation_and_free_withdraw_no_refund():
    m = market()
    initial = OfferState(initial_state(m, (1, 0, 0)))
    # Seller 1 does NOT own token, price 3 exceeds available credits, both legal.
    after = step(m, initial, Offer(0, 0, 1, 0))
    assert after.economy.balances == (0, 0, 0)
    assert after.economy.owners == initial.economy.owners
    assert after.offer_messages == 1
    final = step(m, after, Withdraw(0, 0))
    assert final.economy.balances == after.economy.balances
    assert final.offer_messages == 1 and final.offers[0].status == 'withdrawn'
    with pytest.raises(ValueError, match='inactive'):
        apply_protocol(m, final, Buy(0, 0))
    with pytest.raises(ValueError, match='already issued'):
        apply_protocol(m, final, Offer(0, 0, 2, 0))


def test_buy_is_untaxed_and_trade_conserves_after_offer():
    m = market()
    initial = OfferState(initial_state(m, (5, 0, 0)))
    offered = step(m, initial, Offer(1, 0, 2, 0))
    assert offered.economy.balances == (4, 0, 0)
    settled = step(m, offered, Buy(1, 0))
    assert settled.economy.balances == (0, 0, 4)
    assert sum(offered.economy.balances) == sum(settled.economy.balances)
    assert settled.offer_messages == offered.offer_messages == 1
    assert settled.economy.events[-1].buyer_messages == settled.economy.events[-1].seller_messages == 0
    with pytest.raises(ValueError):
        apply_protocol(m, settled, Buy(1, 0))


def test_persistent_offers_cycles_multiple_demands_and_completed_agent_trading():
    m = market()
    initial = OfferState(initial_state(m, (40, 40, 40)))
    plan = (
        Offer(0, 0, 2, 0),   # A asks C for T
        Offer(1, 0, 2, 1), Buy(1, 1),  # C sells T to B, A's offer remains
        Offer(2, 0, 2, 0),   # Another offer for same token/seller/buyer
        Offer(3, 0, 1, 2), Buy(3, 2),  # C reacquires after already completing task
        Buy(0, 0),           # A's ORIGINAL offer still executable
    )
    final = replay_protocol(m, initial, plan)
    validate_offer_execution(m, initial, final, plan)
    assert final.economy.histories == ((2, 1, 2, 0),)
    assert complete(m, final.economy)
    assert final.offers[0].status == 'fulfilled'
    assert final.offers[2].status == 'active'  # only associated offer closed
    assert final.offer_messages == 4
    assert sum(final.economy.balances) == 120-4
    # Even now A may sell again; historical task completion remains permanent.
    last = (Offer(4, 0, 0, 1), Buy(4, 1), Withdraw(2, 0))
    extended = replay_protocol(m, final, last)
    validate_offer_execution(m, final, extended, last)
    assert complete(m, extended.economy)
    assert extended.economy.histories == ((2, 1, 2, 0, 1),)
    assert extended.offers[2].status == 'withdrawn'


def test_failed_buy_preserves_offer_and_atomic_settlement_prevents_conflicts():
    m = market()
    initial = OfferState(initial_state(m, (20, 20, 20)))
    waiting = replay_protocol(m, initial, (Offer(0, 0, 1, 0), Offer(1, 0, 2, 0), Offer(2, 0, 2, 1)))
    with pytest.raises(ValueError, match='seller does not own'):
        apply_protocol(m, waiting, Buy(0, 0))
    assert waiting.offers[0].status == 'active'
    sold = step(m, waiting, Buy(1, 0))
    with pytest.raises(ValueError, match='seller does not own'):
        apply_protocol(m, sold, Buy(2, 1))
    assert sold.offers[2].status == 'active'
    with pytest.raises(ValueError):
        apply_protocol(m, sold, Buy(999, 0))
    with pytest.raises(ValueError):
        apply_protocol(m, waiting, Withdraw(1, 1))


def test_offer_does_not_guarantee_settlement_and_credit_can_be_spent_elsewhere():
    m = market()
    initial = OfferState(initial_state(m, (5, 0, 0)))
    offered = replay_protocol(m, initial, (Offer(0, 0, 2, 0), Offer(1, 0, 1, 0)))
    assert offered.economy.balances[0] == 3
    with pytest.raises(ValueError, match='unaffordable BUY'):
        apply_protocol(m, offered, Buy(0, 0))
    assert offered.offers[0].status == 'active'


def test_protocol_budget_uses_earlier_sales_and_handles_early_standing_offers():
    m = Market(((0, 2), (2, 0)), (frozenset({1}), frozenset({0})), (0, 1))
    plan = (Offer(0, 1, 1, 0), Offer(1, 0, 0, 1), Buy(1, 1), Buy(0, 0))
    # Agent 0 first pays its OFFER and later uses sale revenue to pay its BUY.
    budgets = protocol_budgets(m, plan)
    assert budgets == (1, 3)
    initial = OfferState(initial_state(m, budgets))
    final = replay_protocol(m, initial, plan)
    validate_offer_execution(m, initial, final, plan)
    assert complete(m, final.economy)
    assert final.economy.balances == (0, 2)
    for i in range(2):
        short = list(budgets); short[i] -= 1
        with pytest.raises(ValueError):
            replay_protocol(m, initial_state(m, tuple(short)), plan)


@pytest.mark.parametrize('leeway', [0, .2, 2])
def test_generated_reference_plan_feasible_serializable_and_balanced(leeway):
    r = generate_market(MarketConfig(n_agents=3, n_tokens=3, task_dependency_range=(1, 3),
                                     budget_leeway=leeway, seed=42))
    plan = r.reference_solution.protocol_actions
    assert plan is not None
    assert sum(isinstance(a, Offer) for a in plan) == sum(isinstance(a, Buy) for a in plan) == len(r.reference_solution.actions)
    assert not any(isinstance(a, Withdraw) for a in plan)
    assert protocol_budgets(r.market, plan) == r.reference_budgets
    explicit = verify_protocol_solution(r.market, r.initial_state, r.reference_solution)
    compact = verify_solution(r.market, r.initial_state, r.reference_solution)
    assert explicit.economy.balances == compact.balances
    assert sum(compact.balances) == sum(r.initial_state.balances)-r.reference_solution.objective[0]
    assert r.metadata['reference_accounting']['final_balances'] == compact.balances
    assert r.metadata['communication_protocol'] == 'offer_buy'
    assert complete(r.market, explicit.economy)
    assert not any(o.status == 'active' for o in explicit.offers)
    assert decode_protocol(loads(dumps(plan))) == plan
    assert dumps(decode_result(loads(dumps(r)))) == dumps(r)


def test_verifier_rejects_invalid_closed_or_wrong_projected_offers():
    r = generate_market(MarketConfig(n_agents=2, n_tokens=1, task_dependency_range=(1, 1)))
    plan = r.reference_solution.protocol_actions
    assert plan
    with pytest.raises(ValueError):
        verify_solution(r.market, r.initial_state, replace(r.reference_solution, protocol_actions=()))
    with pytest.raises(ValueError):
        audit_solution(r.market, r.initial_state, replace(r.reference_solution, protocol_actions=()))
    with pytest.raises(ValueError):
        verify_solution(r.market, r.initial_state, replace(r.reference_solution, protocol_actions=plan + (plan[-1],)))
    with pytest.raises(ValueError):
        verify_solution(r.market, r.initial_state, replace(r.reference_solution, protocol_actions=(Buy(55, 0),)))


def test_strict_ledger_detects_protocol_credit_and_offer_status_corruption():
    m = market()
    initial = OfferState(initial_state(m, (5, 0, 0)))
    plan = (Offer(1, 0, 2, 0), Buy(1, 0))
    final = replay_protocol(m, initial, plan)
    corrupt = replace(final, economy=replace(final.economy, balances=(1, 0, 4)))
    with pytest.raises(ValueError, match='reconcile'):
        validate_offer_execution(m, initial, corrupt, plan)
    corrupt = replace(final, offers=(replace(final.offers[0], status='active'),))
    with pytest.raises(ValueError):
        validate_offer_execution(m, initial, corrupt, plan)
    with pytest.raises(ValueError):
        validate_offer_execution(m, initial, final, tuple(reversed(plan)))


def test_nonstandard_old_fees_require_explicit_historical_configuration():
    with pytest.raises(ValueError, match='legacy_fixed_messages'):
        MarketConfig(seller_messages=1)
    c = MarketConfig(n_agents=2, n_tokens=2, task_dependency_range=(1, 2),
                     buyer_messages=0, communication_protocol='legacy_fixed_messages')
    r = generate_market(c)
    assert r.metadata['communication_protocol'] == 'legacy_fixed_messages'
    assert r.reference_solution.protocol_actions is None
    with pytest.raises(ValueError):
        apply_protocol(r.market, OfferState(r.initial_state), Offer(0, 0, 1, 0))


def test_explicit_plan_with_free_withdrawal_counts_only_offers_not_buys():
    m = market()
    plan = (Offer(0, 0, 2, 0), Withdraw(0, 0), Offer(1, 0, 2, 1), Buy(1, 1),
            Offer(2, 0, 1, 0), Buy(2, 0))
    budgets = protocol_budgets(m, plan)
    assert budgets == (5, 4, 0)
    solution = Solution((Transfer(0, 2, 1), Transfer(0, 1, 0)), (3, 2, 6), plan)
    final = verify_protocol_solution(m, initial_state(m, budgets), solution)
    assert final.economy.balances == (0, 3, 3)
    assert final.offer_messages == 3
    assert final.offers[0].status == 'withdrawn'

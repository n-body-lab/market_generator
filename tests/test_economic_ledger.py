from dataclasses import replace
import pytest
from hivemarket_generator import *
from hivemarket_generator.models import Event
from hivemarket_generator.simulation import execute, replay, send_exploratory_message
from hivemarket_generator.validation import validate_state
from hivemarket_generator.scheduling import verify_solution


def fixture():
    m = Market(((0, 2, 3), (2, 0, 2), (3, 2, 0)),
               (frozenset({1}), frozenset({0}), frozenset({0, 1})), (0, 2), ExecutionMessages(1, 1))
    initial = initial_state(m, (20, 20, 20))
    return m, initial


def test_multi_token_revisits_and_interleaved_communication_reconcile():
    m, initial = fixture()
    state = initial
    ledger = []
    for item in [Transfer(0, 0, 1), CommunicationEvent(1, 2), Transfer(1, 2, 0),
                 Transfer(0, 1, 0), CommunicationEvent(0, 2), Transfer(0, 0, 2), Transfer(1, 0, 2)]:
        if isinstance(item, CommunicationEvent):
            state = send_exploratory_message(m, state, item.sender, item.recipient)
            ledger.append(item)
        else:
            state = execute(m, state, item)
            ledger.append(state.events[-1])
    assert state.histories[0] == (0, 1, 0, 2)
    assert state.balances == (17, 17, 14)  # 60 - 5*2 execution - 2 exploration = 48
    assert sum(state.balances) == 48
    validate_economic_state(m, initial, state, ledger)
    decoded = decode_ledger(loads(dumps(ledger)))
    assert decoded == tuple(ledger)
    validate_economic_state(m, initial, state, decoded)


def test_structural_validation_cannot_detect_injection_but_strict_validation_does():
    m, initial = fixture()
    final = execute(m, initial, Transfer(0, 0, 1))
    injected = replace(final, balances=tuple(b+100 for b in final.balances))
    validate_state(m, injected)  # intentionally remains structural, API preserved
    with pytest.raises(ValueError, match='reconstructed balances'):
        validate_economic_state(m, initial, injected, final.events)


@pytest.mark.parametrize('corruption', ['seller_payment', 'buyer_payment', 'missing_buyer_message',
                                       'missing_seller_message', 'destroy_credit'])
def test_per_agent_accounting_rejects_wrong_final_balances(corruption):
    m, initial = fixture()
    final = execute(m, initial, Transfer(0, 0, 1))
    balances = list(final.balances)
    if corruption == 'seller_payment':
        balances[0] += 2
        balances[1] -= 2  # conserved aggregate still wrong per-agent payment
    elif corruption == 'buyer_payment':
        balances[1] += 2
        balances[0] -= 2
    elif corruption == 'missing_buyer_message':
        balances[1] += 1
    elif corruption == 'missing_seller_message':
        balances[0] += 1
    else:
        balances[2] -= 1
    with pytest.raises(ValueError, match='reconstructed balances'):
        validate_economic_state(m, initial, replace(final, balances=tuple(balances)), final.events)


def test_price_sequence_and_message_metadata_are_checked_against_trusted_rules():
    m, initial = fixture()
    final = execute(m, initial, Transfer(0, 0, 1))
    e = final.events[0]
    for damaged in [replace(e, price=99), replace(e, buyer_messages=0),
                    replace(e, seller_messages=0), replace(e, sequence=3)]:
        with pytest.raises(ValueError):
            validate_economic_state(m, initial, final, [damaged])


def test_negative_intermediate_balance_cannot_be_hidden_by_later_receipts():
    m = Market(((0, 2), (2, 0)), (frozenset({1}), frozenset({0})), (0, 1), ExecutionMessages(0, 0))
    initial = initial_state(m, (0, 2))
    # Forged reverse order gives balanced final books but agent 0 spends two
    # credits before receiving them. Provenance remains structurally consistent.
    events = (Event(0, Transfer(1, 1, 0), 2, 0, 0), Event(1, Transfer(0, 0, 1), 2, 0, 0))
    final = State((1, 0), (0, 2), (frozenset({1}), frozenset({0})), ((0, 1), (1, 0)), events)
    validate_state(m, final)
    with pytest.raises(ValueError, match='intermediate'):
        validate_economic_state(m, initial, final, events)
    valid = replay(m, initial, (Transfer(0, 0, 1), Transfer(1, 1, 0)))
    validate_economic_state(m, initial, valid, valid.events)


def test_seller_cannot_use_incoming_payment_to_fund_execution_message():
    m = Market(((0, 2), (2, 0)), (frozenset(), frozenset({0})), (0,), ExecutionMessages(0, 1))
    initial = initial_state(m, (0, 2))
    event = Event(0, Transfer(0, 0, 1), 2, 0, 1)
    final = State((1,), (1, 0), (frozenset(), frozenset({0})), ((0, 1),), (event,), 1)
    validate_state(m, final)
    with pytest.raises(ValueError, match='intermediate'):
        validate_economic_state(m, initial, final, [event])


def test_communication_ordering_omissions_and_endpoint_corruption():
    m = Market(((0, 2), (2, 0)), (frozenset(), frozenset({0})), (0,), ExecutionMessages(0, 0))
    initial = initial_state(m, (0, 2))
    sold = execute(m, initial, Transfer(0, 0, 1))
    final = send_exploratory_message(m, sold, 0, 1)
    message = CommunicationEvent(0, 1)
    validate_economic_state(m, initial, final, [sold.events[0], message])
    with pytest.raises(ValueError, match='unaffordable exploratory'):
        validate_economic_state(m, initial, final, [message, sold.events[0]])
    for ledger in ([sold.events[0]], [sold.events[0], message, message],
                   [sold.events[0], CommunicationEvent(0, 0)], [sold.events[0], CommunicationEvent(-1, 1)]):
        with pytest.raises(ValueError):
            validate_economic_state(m, initial, final, ledger)
    # Crediting back an exploratory charge is a mismatch even if its counter is right.
    with pytest.raises(ValueError, match='reconstructed balances'):
        validate_economic_state(m, initial, replace(final, balances=sold.balances), [sold.events[0], message])


def test_continuation_anchor_prefix_histories_and_counter_corruption():
    m, initial = fixture()
    first = execute(m, initial, Transfer(0, 0, 1))
    anchor = send_exploratory_message(m, first, 2, 0)
    final = execute(m, anchor, Transfer(0, 1, 0))
    validate_economic_state(m, anchor, final, final.events[len(anchor.events):])
    with pytest.raises(ValueError):
        validate_economic_state(m, anchor, replace(final, histories=((0,), (2,))), final.events[-1:])
    with pytest.raises(ValueError):
        validate_economic_state(m, anchor, replace(final, exploratory_messages=0), final.events[-1:])
    with pytest.raises(ValueError):
        validate_economic_state(m, anchor, final, final.events)  # includes past, not continuation
    with pytest.raises(ValueError):
        validate_economic_state(m, anchor, final, [])


@pytest.mark.parametrize('level', ['easy', 'medium', 'hard'])
def test_generated_reference_schedules_and_exports_reconcile(level):
    r = generate_market(MarketConfig.preset(level, seed=42, exact_state_limit=1000))
    decoded = decode_result(loads(dumps(r)))
    final = verify_solution(decoded.market, decoded.initial_state, decoded.reference_solution)
    validate_economic_state(decoded.market, decoded.initial_state, final, final.events)

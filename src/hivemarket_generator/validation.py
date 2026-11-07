from collections.abc import Sequence
from .models import Market, State, Event, CommunicationEvent


def validate_market(market: Market) -> None:
    n = market.n_agents
    if n < 1 or len(market.prices) != n or any(len(row) != n for row in market.prices):
        raise ValueError('invalid price matrix dimensions')
    for i, row in enumerate(market.prices):
        for j, price in enumerate(row):
            if type(price) is not int or (price != 0 if i == j else price <= 0):
                raise ValueError('prices require zero diagonal and positive integral off-diagonal')
    if any(type(o) is not int or not 0 <= o < n for o in market.initial_owners):
        raise ValueError('invalid owner')
    if any(type(t) is not int or not 0 <= t < market.n_tokens for task in market.tasks for t in task):
        raise ValueError('invalid task token')


def validate_state(market: Market, state: State) -> None:
    validate_market(market)
    if (len(state.owners) != market.n_tokens or len(state.histories) != market.n_tokens
            or len(state.balances) != market.n_agents or len(state.progress) != market.n_agents):
        raise ValueError('invalid state dimensions')
    if any(type(b) is not int or b < 0 for b in state.balances):
        raise ValueError('negative/noninteger balance')
    if any(type(o) is not int or not 0 <= o < market.n_agents for o in state.owners):
        raise ValueError('invalid current owner')
    if type(state.execution_messages) is not int or state.execution_messages < 0:
        raise ValueError('invalid execution messages')
    for t, history in enumerate(state.histories):
        if (not history or history[0] != market.initial_owners[t] or history[-1] != state.owners[t]
                or any(type(o) is not int or not 0 <= o < market.n_agents for o in history)):
            raise ValueError('invalid history')
    for i, task in enumerate(market.tasks):
        if state.progress[i] != frozenset(t for t in task if i in state.histories[t]):
            raise ValueError('progress inconsistent with provenance')
    histories = [(o,) for o in market.initial_owners]
    messages = 0
    for index, event in enumerate(state.events):
        action = event.transfer
        if not 0 <= action.token < market.n_tokens or not 0 <= action.buyer < market.n_agents:
            raise ValueError('invalid event IDs')
        if (type(event.sequence) is not int or event.sequence != index
                or histories[action.token][-1] != action.seller
                or action.buyer == action.seller or event.price != market.prices[action.buyer][action.seller]
                or (event.buyer_messages, event.seller_messages) != market.communication.counts(
                    action.token, action.seller, action.buyer)):
            raise ValueError('invalid transfer event')
        histories[action.token] += (action.buyer,)
        messages += event.buyer_messages + event.seller_messages
    if tuple(histories) != state.histories or messages != state.execution_messages:
        raise ValueError('history/events mismatch')
    if type(state.exploratory_messages) is not int or state.exploratory_messages < 0:
        raise ValueError('invalid exploratory messages')


def audit_solution(market: Market, initial: State, solution: 'Solution') -> None:
    """Independent arithmetic/ownership audit; does not call simulation.execute.

    Validates a continuation from any structurally valid state, including historic
    progress. Message balances are checked before incoming sale proceeds.
    """
    validate_state(market, initial)
    if solution.protocol_actions is not None:
        from .scheduling import verify_protocol_solution
        verify_protocol_solution(market, initial, solution)
    balances = list(initial.balances)
    owners = list(initial.owners)
    seen = [set(p) for p in initial.progress]
    gross = messages = 0
    for a in solution.actions:
        if (not 0 <= a.token < market.n_tokens or not 0 <= a.seller < market.n_agents
                or not 0 <= a.buyer < market.n_agents or a.buyer == a.seller or owners[a.token] != a.seller):
            raise ValueError('audit: invalid ownership')
        price = market.prices[a.buyer][a.seller]
        mb, ms = market.communication.counts(a.token, a.seller, a.buyer)
        if balances[a.buyer] < price + mb or balances[a.seller] < ms:
            raise ValueError('audit: insufficient credits')
        balances[a.buyer] -= price + mb
        balances[a.seller] += price - ms
        owners[a.token] = a.buyer
        if a.token in market.tasks[a.buyer]:
            seen[a.buyer].add(a.token)
        gross += price
        messages += mb + ms
    if any(not task <= progress for task, progress in zip(market.tasks, seen)):
        raise ValueError('audit: unsatisfied tasks')
    if solution.objective != (messages, len(solution.actions), gross):
        raise ValueError('audit: objective mismatch')
    if sum(balances) != sum(initial.balances) - messages:
        raise ValueError('audit: accounting failure')


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .scheduling import Solution


def validate_economic_state(market: Market, trusted_initial: State, final: State,
                            ledger: Sequence[Event | CommunicationEvent]) -> None:
    """Reconcile a continuation from a trusted balance anchor and ordered ledger.

    Does not call simulation.execute/replay. Transfer sequence numbers continue
    trusted_initial.events; communication ordering comes from the ledger sequence.
    Every new transfer and exploratory message must be supplied, in actual order.
    Execution messages are charged in their transfer Event, never as separate
    CommunicationEvents. The trusted anchor's earlier economics are not re-proven.
    No signature authenticity or external event-source authentication is implied.
    """
    validate_state(market, trusted_initial)
    validate_state(market, final)
    balances = list(trusted_initial.balances)
    owners = list(trusted_initial.owners)
    histories = list(trusted_initial.histories)
    progress = list(trusted_initial.progress)
    transfers = list(trusted_initial.events)
    execution_messages = trusted_initial.execution_messages
    exploratory_messages = trusted_initial.exploratory_messages
    n = market.n_agents
    for record in ledger:
        if isinstance(record, CommunicationEvent):
            sender, recipient = record.sender, record.recipient
            if (type(sender) is not int or type(recipient) is not int
                    or not 0 <= sender < n or not 0 <= recipient < n or sender == recipient):
                raise ValueError('ledger: invalid communication endpoints')
            if balances[sender] < 1:
                raise ValueError('ledger: unaffordable exploratory message')
            balances[sender] -= 1
            exploratory_messages += 1
        elif isinstance(record, Event):
            action = record.transfer
            t, seller, buyer = action.token, action.seller, action.buyer
            if (any(type(i) is not int for i in (t, seller, buyer)) or not 0 <= t < market.n_tokens
                    or not 0 <= seller < n or not 0 <= buyer < n or seller == buyer or owners[t] != seller):
                raise ValueError('ledger: invalid transfer or ownership')
            price = market.prices[buyer][seller]
            mb, ms = market.communication.counts(t, seller, buyer)
            if (type(record.sequence) is not int or record.sequence != len(transfers)
                    or type(record.price) is not int or record.price != price
                    or type(record.buyer_messages) is not int or type(record.seller_messages) is not int
                    or (record.buyer_messages, record.seller_messages) != (mb, ms)):
                raise ValueError('ledger: incorrect sequence, transaction price or execution-message charge')
            # Both message fees must be affordable BEFORE incoming sale proceeds.
            if balances[buyer] < price + mb or balances[seller] < ms:
                raise ValueError('ledger: unaffordable transfer at an intermediate state')
            balances[buyer] -= price
            balances[seller] += price  # trading conserves credits
            balances[buyer] -= mb
            balances[seller] -= ms     # execution communication consumes credits
            execution_messages += mb + ms
            owners[t] = buyer
            histories[t] += (buyer,)
            if t in market.tasks[buyer]:
                progress[buyer] = progress[buyer] | {t}
            transfers.append(record)
        else:
            raise ValueError('ledger: unsupported event type')
    if tuple(balances) != final.balances:
        raise ValueError('ledger: reconstructed balances do not match final state')
    reconstructed = State(tuple(owners), tuple(balances), tuple(progress), tuple(histories),
                          tuple(transfers), execution_messages, exploratory_messages)
    if reconstructed != final:
        raise ValueError('ledger: final ownership, histories, progress, events or message counts do not match')

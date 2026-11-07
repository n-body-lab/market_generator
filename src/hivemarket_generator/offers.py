"""Deterministic OFFER/WITHDRAW/BUY execution; no broker or asynchronous runtime.

The existing State/Transfer interface remains the compact just-in-time reference
projection. OfferState is the explicit protocol snapshot: its economy contains
untaxed transfer events; offer_messages separately counts the OFFER expenditure.
Do not reconcile that economy alone with the historical fixed-message validator.
"""
from dataclasses import dataclass, field, replace
from typing import TypeAlias
from .models import Market, State, Transfer, Event


@dataclass(frozen=True)
class Offer:
    offer_id: int
    token: int
    seller: int
    buyer: int
    kind: str = field(default='OFFER', init=False)


@dataclass(frozen=True)
class Withdraw:
    offer_id: int
    buyer: int
    kind: str = field(default='WITHDRAW', init=False)


@dataclass(frozen=True)
class Buy:
    offer_id: int
    buyer: int
    kind: str = field(default='BUY', init=False)


ProtocolAction: TypeAlias = Offer | Withdraw | Buy


@dataclass(frozen=True)
class StandingOffer:
    request: Offer
    status: str = 'active'


@dataclass(frozen=True)
class OfferState:
    economy: State
    offers: tuple[StandingOffer, ...] = ()
    ledger: tuple[ProtocolAction, ...] = ()
    offer_messages: int = 0


def uses_offer_protocol(market: Market) -> bool:
    """Use the declared identity; equal prices/fees do not identify a protocol."""
    return market.communication_protocol == 'offer_buy'


def reference_protocol(actions: tuple[Transfer, ...]) -> tuple[ProtocolAction, ...]:
    return tuple(step for i, a in enumerate(actions)
                 for step in (Offer(i, a.token, a.seller, a.buyer), Buy(i, a.buyer)))


def _valid_ids(market: Market, action: ProtocolAction) -> None:
    if type(action.offer_id) is not int or action.offer_id < 0:
        raise ValueError('invalid offer ID')
    if type(action.buyer) is not int or not 0 <= action.buyer < market.n_agents:
        raise ValueError('invalid buyer')
    if isinstance(action, Offer) and (
            type(action.token) is not int or not 0 <= action.token < market.n_tokens
            or type(action.seller) is not int or not 0 <= action.seller < market.n_agents
            or action.seller == action.buyer):
        raise ValueError('invalid offer endpoints or token')


def _validate_snapshot(market: Market, snapshot: OfferState) -> None:
    from .validation import validate_state
    if not isinstance(snapshot, OfferState):
        raise ValueError('expected an OfferState snapshot')
    # Explicit BUY events are untaxed; a trusted compact prefix may coexist.
    validate_state(market, snapshot.economy, allow_settlement_events=True)
    if type(snapshot.offer_messages) is not int or snapshot.offer_messages != len(snapshot.offers):
        raise ValueError('offer expenditure inconsistent with retained issued offers')
    seen: set[int] = set()
    for item in snapshot.offers:
        if not isinstance(item, StandingOffer) or not isinstance(item.request, Offer):
            raise ValueError('invalid standing offer')
        _valid_ids(market, item.request)
        if item.request.offer_id in seen or item.status not in ('active', 'withdrawn', 'fulfilled'):
            raise ValueError('duplicate offer ID or invalid status')
        seen.add(item.request.offer_id)


def apply_protocol(market: Market, state: OfferState, action: ProtocolAction) -> OfferState:
    """Sequential reference action; BUY includes assumed free seller SELL consent.

    This is a cooperative economic witness, not unilateral purchase permission.
    The buyer must freshly invoke BUY; an old OFFER never triggers settlement.
    Failed BUY leaves its offer active and the immutable snapshot intact.
    """
    from .validation import validate_market
    validate_market(market)
    if not uses_offer_protocol(market):
        raise ValueError('explicit protocol requires one-credit OFFER and untaxed BUY policy')
    if not isinstance(action, (Offer, Withdraw, Buy)):
        raise ValueError('unsupported protocol action')
    _validate_snapshot(market, state)
    _valid_ids(market, action)
    economy = state.economy
    offers = list(state.offers)
    matches = [i for i, item in enumerate(offers) if item.request.offer_id == action.offer_id]
    balances = list(economy.balances)
    messages = state.offer_messages
    if isinstance(action, Offer):
        if matches:
            raise ValueError('offer ID already issued')
        if balances[action.buyer] < 1:
            raise ValueError('unaffordable OFFER')
        balances[action.buyer] -= 1
        messages += 1
        offers.append(StandingOffer(action))  # ownership and price affordability are irrelevant here
        economy = replace(economy, balances=tuple(balances))
    else:
        if not matches:
            raise ValueError('unknown offer')
        index = matches[0]
        item = offers[index]
        request = item.request
        if item.status != 'active' or request.buyer != action.buyer:
            raise ValueError('inactive offer or wrong buyer')
        if isinstance(action, Withdraw):
            offers[index] = replace(item, status='withdrawn')  # no fee and no refund
        else:
            if economy.owners[request.token] != request.seller:
                raise ValueError('seller does not own token; offer remains active')
            price = market.prices[request.buyer][request.seller]
            if balances[request.buyer] < price:
                raise ValueError('unaffordable BUY; offer remains active')
            balances[request.buyer] -= price
            balances[request.seller] += price
            owners, progress, histories = list(economy.owners), list(economy.progress), list(economy.histories)
            owners[request.token] = request.buyer
            if request.token in market.tasks[request.buyer]:
                progress[request.buyer] = progress[request.buyer] | {request.token}
            histories[request.token] += (request.buyer,)
            event = Event(len(economy.events), Transfer(request.token, request.seller, request.buyer), price, 0, 0)
            economy = replace(economy, owners=tuple(owners), balances=tuple(balances),
                              progress=tuple(progress), histories=tuple(histories), events=economy.events + (event,))
            offers[index] = replace(item, status='fulfilled')
    return OfferState(economy, tuple(offers), state.ledger + (action,), messages)


def replay_protocol(market: Market, initial: State | OfferState,
                    actions: tuple[ProtocolAction, ...]) -> OfferState:
    from .validation import validate_market, validate_state
    validate_market(market)
    if not uses_offer_protocol(market):
        raise ValueError('not an OFFER/BUY market')
    if isinstance(initial, State):
        validate_state(market, initial)
    state = initial if isinstance(initial, OfferState) else OfferState(initial)
    _validate_snapshot(market, state)
    for action in actions:
        state = apply_protocol(market, state, action)
    return state


def validate_offer_execution(market: Market, initial: OfferState, final: OfferState,
                             ledger: tuple[ProtocolAction, ...]) -> None:
    """Independent ordered ledger reconciliation; initial snapshot is trusted.

    No call to apply_protocol/replay_protocol or legacy execute. Checks every
    balance prefix, offer lifetime, transfer, provenance entry and final field.
    """
    from .validation import validate_market
    validate_market(market)
    if not uses_offer_protocol(market):
        raise ValueError('not an OFFER/BUY market')
    _validate_snapshot(market, initial)
    _validate_snapshot(market, final)
    anchor = initial.economy
    balances, owners = list(anchor.balances), list(anchor.owners)
    if len(balances) != market.n_agents or any(type(b) is not int or b < 0 for b in balances):
        raise ValueError('invalid trusted balances')
    histories, progress, events = list(anchor.histories), list(anchor.progress), list(anchor.events)
    offers = {item.request.offer_id: (item.request, item.status) for item in initial.offers}
    if len(offers) != len(initial.offers):
        raise ValueError('duplicate anchor offers')
    messages = initial.offer_messages
    for step in ledger:
        if not isinstance(step, (Offer, Withdraw, Buy)):
            raise ValueError('invalid protocol ledger record')
        _valid_ids(market, step)
        if isinstance(step, Offer):
            if step.offer_id in offers or balances[step.buyer] < 1:
                raise ValueError('duplicate or unaffordable OFFER')
            balances[step.buyer] -= 1
            messages += 1
            offers[step.offer_id] = (step, 'active')
        else:
            if step.offer_id not in offers:
                raise ValueError('unknown offer')
            request, status = offers[step.offer_id]
            if status != 'active' or request.buyer != step.buyer:
                raise ValueError('invalid offer lifetime or buyer')
            if isinstance(step, Withdraw):
                offers[step.offer_id] = (request, 'withdrawn')
                continue
            t, s, b = request.token, request.seller, request.buyer
            price = market.prices[b][s]
            if owners[t] != s or balances[b] < price:
                raise ValueError('ownership or affordability failure at BUY')
            balances[b] -= price
            balances[s] += price
            owners[t] = b
            histories[t] += (b,)
            if t in market.tasks[b]:
                progress[b] = progress[b] | {t}
            events.append(Event(len(events), Transfer(t, s, b), price, 0, 0))
            offers[step.offer_id] = (request, 'fulfilled')
    expected_economy = replace(anchor, owners=tuple(owners), balances=tuple(balances),
                               progress=tuple(progress), histories=tuple(histories), events=tuple(events))
    expected = OfferState(expected_economy,
                          tuple(StandingOffer(request, status) for request, status in offers.values()),
                          initial.ledger + tuple(ledger), messages)
    if expected != final:
        raise ValueError('protocol ledger does not reconcile with final state')


def protocol_budgets(market: Market, ledger: tuple[ProtocolAction, ...]) -> tuple[int, ...]:
    """Minimum endowment for this ordered sequential protocol, not global minimum."""
    from .validation import validate_market
    validate_market(market)
    if not uses_offer_protocol(market):
        raise ValueError('not an OFFER/BUY market')
    spent = [0] * market.n_agents
    required = [0] * market.n_agents
    offers: dict[int, Offer] = {}
    used: set[int] = set()
    owners = list(market.initial_owners)
    for step in ledger:
        if not isinstance(step, (Offer, Withdraw, Buy)):
            raise ValueError('invalid protocol action')
        _valid_ids(market, step)
        if isinstance(step, Offer):
            if step.offer_id in used:
                raise ValueError('duplicate offer')
            used.add(step.offer_id)
            offers[step.offer_id] = step
            required[step.buyer] = max(required[step.buyer], spent[step.buyer] + 1)
            spent[step.buyer] += 1
        else:
            if step.offer_id not in offers or offers[step.offer_id].buyer != step.buyer:
                raise ValueError('invalid offer')
            request = offers.pop(step.offer_id)
            if isinstance(step, Buy):
                if owners[request.token] != request.seller:
                    raise ValueError('seller lacks token')
                price = market.prices[request.buyer][request.seller]
                required[request.buyer] = max(required[request.buyer], spent[request.buyer] + price)
                spent[request.buyer] += price
                spent[request.seller] -= price
                owners[request.token] = request.buyer
    return tuple(required)


def protocol_summary(market: Market, initial: State, final: OfferState) -> dict:
    new_events = final.economy.events[len(initial.events):]
    return {'communication_expenditure': final.offer_messages,
            'gross_trading_expenditure': sum(e.price for e in new_events),
            'transactions': len(new_events), 'initial_balances': initial.balances,
            'final_balances': final.economy.balances,
            'active_offers': sum(o.status == 'active' for o in final.offers)}

"""Immutable full-information models and deliberately restricted local snapshots."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionMessages:
    buyer: int = 1
    seller: int = 0

    def __post_init__(self) -> None:
        if any(type(x) is not int or x < 0 for x in (self.buyer, self.seller)):
            raise ValueError('message counts must be nonnegative integers')

    def counts(self, token: int, seller: int, buyer: int) -> tuple[int, int]:
        """Compact transfer-plan expenditure: default buyer count is its OFFER.

        Other counts are historical fixed-message compatibility policies.
        Explicit BUY settlement in offers.py never charges these counts.
        """
        return self.buyer, self.seller


@dataclass(frozen=True)
class Market:
    prices: tuple[tuple[int, ...], ...]
    tasks: tuple[frozenset[int], ...]
    initial_owners: tuple[int, ...]
    communication: ExecutionMessages = ExecutionMessages()

    @property
    def n_agents(self) -> int:
        return len(self.tasks)

    @property
    def n_tokens(self) -> int:
        return len(self.initial_owners)


@dataclass(frozen=True)
class Transfer:
    token: int
    seller: int
    buyer: int


@dataclass(frozen=True)
class Event:
    sequence: int
    transfer: Transfer
    price: int
    buyer_messages: int
    seller_messages: int
    signature: str | None = None


@dataclass(frozen=True)
class CommunicationEvent:
    """One exploratory message; cost is fixed at one credit by V0.1 semantics.

    Interleave these records with transfer Events in an external ordered ledger.
    State.events remains the existing transfer-only provenance log.
    """
    sender: int
    recipient: int


@dataclass(frozen=True)
class State:
    owners: tuple[int, ...]
    balances: tuple[int, ...]
    progress: tuple[frozenset[int], ...]
    histories: tuple[tuple[int, ...], ...]
    events: tuple[Event, ...] = ()
    execution_messages: int = 0
    exploratory_messages: int = 0


@dataclass(frozen=True)
class LocalView:
    agent: int
    n_agents: int
    balance: int
    inventory: frozenset[int]
    task: frozenset[int]
    progress: frozenset[int]
    buying_prices: tuple[int, ...]
    selling_prices: tuple[int, ...]


def initial_state(market: Market, balances: tuple[int, ...] | None = None) -> State:
    credits = balances if balances is not None else (0,) * market.n_agents
    if len(credits) != market.n_agents or any(type(x) is not int or x < 0 for x in credits):
        raise ValueError('invalid initial balances')
    return State(market.initial_owners, credits,
                 tuple(frozenset(t for t in task if market.initial_owners[t] == i)
                       for i, task in enumerate(market.tasks)),
                 tuple((owner,) for owner in market.initial_owners))


def local_view(market: Market, state: State, agent: int) -> LocalView:
    if not 0 <= agent < market.n_agents:
        raise ValueError('invalid agent')
    return LocalView(agent, market.n_agents, state.balances[agent],
                     frozenset(t for t, owner in enumerate(state.owners) if owner == agent),
                     market.tasks[agent], state.progress[agent], market.prices[agent],
                     tuple(row[agent] for row in market.prices))


def complete(market: Market, state: State) -> bool:
    return all(task <= seen for task, seen in zip(market.tasks, state.progress))

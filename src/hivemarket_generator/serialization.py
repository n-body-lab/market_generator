"""Versioned JSON envelope; explicit typed decoder with invariant validation."""
from dataclasses import asdict, is_dataclass
import json
from typing import Any
from .models import Market, State, ExecutionMessages, Event, Transfer
from .validation import validate_market, validate_state


def primitive(value: Any) -> Any:
    if is_dataclass(value):
        return primitive(asdict(value))
    if isinstance(value, dict):
        return {str(k): primitive(v) for k, v in value.items()}
    if isinstance(value, (set, frozenset)):
        return [primitive(v) for v in sorted(value)]
    if isinstance(value, (tuple, list)):
        return [primitive(v) for v in value]
    return value


def dumps(value: Any) -> str:
    return json.dumps({'schema_version': 'hivemarket/0.1', 'data': primitive(value)}, sort_keys=True,
                      indent=2, allow_nan=False)


def loads(text: str) -> Any:
    envelope = json.loads(text)
    if envelope['schema_version'] != 'hivemarket/0.1':
        raise ValueError('unsupported schema')
    return envelope['data']


def decode_market(data: dict[str, Any]) -> Market:
    market = Market(tuple(tuple(row) for row in data['prices']),
                    tuple(frozenset(task) for task in data['tasks']), tuple(data['initial_owners']),
                    ExecutionMessages(**data['communication']))
    validate_market(market)
    return market


def decode_state(market: Market, data: dict[str, Any]) -> State:
    events = tuple(Event(e['sequence'], Transfer(**e['transfer']), e['price'], e['buyer_messages'],
                         e['seller_messages'], e.get('signature')) for e in data['events'])
    state = State(tuple(data['owners']), tuple(data['balances']), tuple(frozenset(p) for p in data['progress']),
                  tuple(tuple(h) for h in data['histories']), events,
                  data['execution_messages'], data['exploratory_messages'])
    validate_state(market, state)
    return state

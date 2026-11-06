"""Interpretable structural measurements, not a calibrated difficulty score."""
from collections import Counter
from statistics import mean
from typing import TYPE_CHECKING
from .models import Market, State, Transfer, complete
from .simulation import replay, execute, send_exploratory_message

if TYPE_CHECKING:
    from .generation import GenerationResult


def analyse_difficulty(result: 'GenerationResult', limited_slack_threshold: float = 0.1) -> dict:
    m, state, routes = result.market, result.initial_state, result.token_routes
    demand = Counter(t for task in m.tasks for t in task)
    participants = Counter(i for route in routes if len(route) > 1 for i in set(route))
    intermediaries = Counter(i for route in routes for i in set(route[1:-1]))
    required_lengths = [routes[t].index(i) for i, task in enumerate(m.tasks) for t in task]
    unknown_prices = sum(1 for i, task in enumerate(m.tasks) for t in task
                         for a, b in zip(routes[t], routes[t][1:]) if i not in (a, b))
    absolute = [b - r for b, r in zip(state.balances, result.reference_budgets)]
    relative = [slack / ref if ref else None for slack, ref in zip(absolute, result.reference_budgets)]
    removals = {'invalid_ownership_or_credit': 0, 'incomplete_tasks': 0, 'still_complete': 0}
    for idx in range(len(result.reference_solution.actions)):
        actions = result.reference_solution.actions[:idx] + result.reference_solution.actions[idx + 1:]
        try:
            final = replay(m, state, actions)
            removals['still_complete' if complete(m, final) else 'incomplete_tasks'] += 1
        except ValueError:
            removals['invalid_ownership_or_credit'] += 1
    overlap = {f'{i},{j}': len(m.tasks[i] & m.tasks[j])
               for i in range(m.n_agents) for j in range(i + 1, m.n_agents)}
    lengths = [len(r) - 1 for r in routes]
    unknown_locations = sum(t not in state.progress[i] for i, task in enumerate(m.tasks) for t in task)
    return {
        'routing': {
            'average_required_first_visit_hops': mean(required_lengths) if required_lengths else 0,
            'maximum_required_first_visit_hops': max(required_lengths, default=0),
            'token_walk_lengths': lengths,
            'average_token_walk_length': mean(lengths) if lengths else 0,
            'maximum_token_walk_length': max(lengths, default=0),
            'retained_alternatives_per_pair': {f'{a},{b}': max(0, len(paths)-1)
                                                for (a, b), paths in result.candidates.items()},
            'candidate_count_is_capped': True,
            'legal_branching_factor_per_token': max(0, m.n_agents - 1),
            'candidate_first_hop_branching': {f'{a},{b}': len({p[1] for p in paths})
                                              for (a, b), paths in result.candidates.items()},
            'revisits_and_cycle_closures': sum(len(r) - len(set(r)) for r in routes),
            'shared_intermediary_route_counts': dict(intermediaries),
        },
        'discovery_proxies': {
            'unknown_required_token_locations': unknown_locations,
            'unknown_route_price_occurrences_from_demanders': unknown_prices,
            'plausible_intermediaries_per_pair': max(0, m.n_agents - 2),
            'location_assignment_search_space': m.n_agents ** unknown_locations,
            'assumptions': 'Each unmet requirement independently considers every agent as owner; '
                           'overlaps ignored. Counts are proxies, not minimum messages.',
        },
        'resources': {
            'initial_budgets': state.balances, 'reference_budgets': result.reference_budgets,
            'absolute_slack': absolute, 'relative_slack': relative,
            'relative_slack_zero_reference': 'null; see absolute slack',
            'limited_slack_threshold': limited_slack_threshold,
            'fraction_limited_slack': sum((v <= limited_slack_threshold if v is not None else a == 0)
                                         for v, a in zip(relative, absolute)) / m.n_agents,
            'execution_communication_expenditure': result.reference_solution.objective[0],
            'exploratory_communication_expenditure': 0,
            'gross_trade_payments': result.reference_solution.objective[2],
        },
        'strategic_proxies': {
            'token_demand_counts': dict(demand),
            'shared_demand_tokens': sum(v > 1 for v in demand.values()),
            'pairwise_task_dependency_overlap': overlap,
            'agent_token_route_participation': dict(participants),
            'reference_intermediary_dependence': dict(intermediaries),
            'single_transaction_removal_without_replanning': removals,
            'interpretation': 'Reference-route dependencies; not indispensable graph vertices, collusion or misalignment.',
        },
    }


def analyse_fragility(market: Market, state: State, state_limit: int = 5000) -> dict:
    """Optional one-step exact reachability. Unknown cases remain unclassified."""
    from .optimization import solve_exact
    baseline = solve_exact(market, state, state_limit)
    actions = []
    for token, seller in enumerate(state.owners):
        for buyer in range(market.n_agents):
            if buyer == seller:
                continue
            action = Transfer(token, seller, buyer)
            try:
                nxt = execute(market, state, action)
            except ValueError:
                continue
            outcome = solve_exact(market, nxt, state_limit)
            penalty = None
            if baseline.status == outcome.status == 'optimal':
                from .scheduling import objective
                edge = objective(market, (action,))
                penalty = tuple(e + v - b for e, v, b in zip(
                    edge, outcome.best_solution.objective, baseline.best_solution.objective))
            actions.append({'action': action, 'status': outcome.status,
                            'preserves_feasibility': True if outcome.best_solution else (
                                False if outcome.status == 'infeasible' else None),
                            'objective_difference_from_optimum': penalty})
    sensitivity = []
    for sender, balance in enumerate(state.balances):
        if balance and market.n_agents > 1:
            depleted = send_exploratory_message(market, state, sender, (sender + 1) % market.n_agents)
            outcome = solve_exact(market, depleted, state_limit)
            sensitivity.append({'sender': sender, 'credits_consumed': 1, 'status': outcome.status,
                                'best_objective': outcome.best_solution.objective if outcome.best_solution else None})
    return {'baseline_status': baseline.status, 'affordable_actions': len(actions),
            'preserving_actions': sum(a['preserves_feasibility'] is True for a in actions),
            'destructive_actions': sum(a['preserves_feasibility'] is False for a in actions),
            'unclassified_actions': sum(a['preserves_feasibility'] is None for a in actions),
            'actions': actions, 'one_credit_expenditure_sensitivity': sensitivity}

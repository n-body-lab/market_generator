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
    # Pre-action unmet requirements only: independent of optimal plans and outcomes.
    pending_tokens = frozenset(t for task, progress in zip(market.tasks, state.progress)
                               for t in task - progress)
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
                            'goal_relevant': token in pending_tokens,
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
    destructive = sum(a['preserves_feasibility'] is False for a in actions)
    unknown = sum(a['preserves_feasibility'] is None for a in actions)
    total = len(actions)
    fragility = destructive / total if total and not unknown else None
    relevant = [a for a in actions if a['goal_relevant']]
    relevant_destructive = sum(a['preserves_feasibility'] is False for a in relevant)
    relevant_unknown = sum(a['preserves_feasibility'] is None for a in relevant)
    relevant_count = len(relevant)
    goal_fragility = relevant_destructive / relevant_count if relevant_count and not relevant_unknown else None
    return {'decision_fragility': fragility,  # compatibility: full affordable action space
            'full_affordable_action_fragility': fragility,
            'full_fragility_interpretation': 'Economic fragility over all affordable token transfers; sensitive to irrelevant action counts.',
            'goal_relevant_fragility': goal_fragility,
            'goal_relevance_criterion': 'Transferred token has at least one unmet agent-token requirement in the pre-action state.',
            'goal_relevant_actions': relevant_count,
            'goal_relevant_preserving_actions': sum(a['preserves_feasibility'] is True for a in relevant),
            'goal_relevant_destructive_actions': relevant_destructive,
            'goal_relevant_unclassified_actions': relevant_unknown,
            'irrelevant_actions': total - relevant_count,
            'goal_relevant_fragility_status': ('no_goal_relevant_affordable_actions' if not relevant_count else
                                              ('unavailable_search_limit' if relevant_unknown else 'exact')),
            'goal_relevant_fragility_bounds': (relevant_destructive / relevant_count,
                (relevant_destructive + relevant_unknown) / relevant_count) if relevant_count else None,
            'fragility_status': 'no_affordable_actions' if not total else ('unavailable_search_limit' if unknown else 'exact'),
            'fragility_bounds': (destructive / total, (destructive + unknown) / total) if total else None,
            'communication_affordability': {
                'agents_affording_one_message': sum(b >= 1 for b in state.balances),
                'total_credits': sum(state.balances)},
            'baseline_status': baseline.status, 'affordable_actions': len(actions),
            'preserving_actions': sum(a['preserves_feasibility'] is True for a in actions),
            'destructive_actions': sum(a['preserves_feasibility'] is False for a in actions),
            'unclassified_actions': sum(a['preserves_feasibility'] is None for a in actions),
            'actions': actions, 'one_credit_expenditure_sensitivity': sensitivity}


def count_feasible_sequences(market: Market, state: State, max_transactions: int,
                             node_limit: int = 100000) -> dict:
    """Enumerate action sequences completing for the first time within a horizon.

    Distinct token transfers count as distinct sequences. Completion stops a path;
    no claim about all arbitrary-length schedules is made. A cap returns only a
    lower bound, never an exact count. Cycles are permitted within the horizon.
    """
    if max_transactions < 0 or node_limit < 0:
        raise ValueError('negative enumeration bound')
    stack = [(state, 0)]
    visited = winners = 0
    while stack:
        if visited >= node_limit:
            return {'count': None, 'lower_bound': winners, 'status': 'limit_reached',
                    'horizon': max_transactions, 'visited_nodes': visited}
        current, depth = stack.pop()
        visited += 1
        if complete(market, current):
            winners += 1
        elif depth < max_transactions:
            for t, seller in enumerate(current.owners):
                for buyer in range(market.n_agents):
                    if buyer == seller:
                        continue
                    try:
                        stack.append((execute(market, current, Transfer(t, seller, buyer)), depth + 1))
                    except ValueError:
                        pass
    return {'count': winners, 'lower_bound': winners, 'status': 'exhausted_horizon',
            'horizon': max_transactions, 'visited_nodes': visited}


def financing_dependence(result: 'GenerationResult') -> dict:
    """Reference purchases unaffordable from initial balance minus earlier spending.

    Counterfactual removes ALL prior sale receipts, retaining actual spending.
    This is schedule dependence, not a claim no alternative schedule exists.
    """
    m = result.market
    spending = [0] * m.n_agents
    dependent = []
    for index, a in enumerate(result.reference_solution.actions):
        mb, ms = m.communication.counts(a.token, a.seller, a.buyer)
        amount = m.prices[a.buyer][a.seller] + mb
        if result.initial_state.balances[a.buyer] - spending[a.buyer] < amount:
            dependent.append(index)
        spending[a.buyer] += amount
        spending[a.seller] += ms
    return {'purchases_requiring_prior_sale_receipts': len(dependent), 'action_indices': dependent,
            'definition': 'Remove previous receipts, retaining spending, in the fixed reference schedule.'}

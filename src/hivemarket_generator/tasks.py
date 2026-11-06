import numpy as np


def generate_tasks(n_agents: int, n_tokens: int, bounds: tuple[int, int],
                   rng: np.random.Generator, owners: tuple[int, ...],
                   candidates: dict[tuple[int, int], tuple[tuple[int, ...], ...]]) -> tuple[frozenset[int], ...]:
    """Mix target path lengths within each market, sampling without replacement.

    Initially owned tokens remain eligible. Route bias is probabilistic, so labels
    never guarantee a particular realised difficulty; metrics report the outcome.
    """
    tasks = []
    for agent in range(n_agents):
        depth = max((len(paths[0]) - 1 for paths in candidates.values()), default=0)
        desired_depth = int(rng.integers(0, depth + 1))
        lengths = [0 if owner == agent else len(candidates[owner, agent][0]) - 1 for owner in owners]
        weights = np.array([1 / (1 + abs(length - desired_depth)) for length in lengths])
        count = int(rng.integers(bounds[0], bounds[1] + 1))
        chosen = rng.choice(n_tokens, count, replace=False, p=weights / weights.sum() if n_tokens else None)
        tasks.append(frozenset(int(t) for t in chosen))
    return tuple(tasks)

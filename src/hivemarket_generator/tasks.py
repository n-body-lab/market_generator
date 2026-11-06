import numpy as np


def generate_tasks(n_agents: int, n_tokens: int, bounds: tuple[int, int],
                   rng: np.random.Generator) -> tuple[frozenset[int], ...]:
    """Independent variable-size subsets allow shared and initially met demands."""
    return tuple(frozenset(int(t) for t in rng.choice(n_tokens, int(rng.integers(bounds[0], bounds[1]+1)),
                                                   replace=False)) for _ in range(n_agents))

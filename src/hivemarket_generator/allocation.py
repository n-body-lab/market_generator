import numpy as np


def allocate_tokens(n_agents: int, n_tokens: int, concentration: float,
                    rng: np.random.Generator) -> tuple[int, ...]:
    weights = rng.dirichlet(np.full(n_agents, concentration))
    return tuple(int(x) for x in rng.choice(n_agents, n_tokens, p=weights))

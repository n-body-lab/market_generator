from pathlib import Path
from hivemarket_generator import MarketConfig, generate_market, dumps

config = MarketConfig(n_agents=6, n_tokens=12, max_candidate_depth=3,
                      ownership_concentration=0.5, task_dependency_range=(1, 4),
                      budget_leeway=0.2, seed=42)
result = generate_market(config)
Path('market.json').write_text(dumps(result))
print(result.feasibility_status, result.optimality_status)

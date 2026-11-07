"""Generate and verify a current-rule market; no agents or broker required."""
import argparse
from pathlib import Path
from hivemarket_generator import (MarketConfig, generate_market, verify_protocol_solution,
                                 protocol_summary, dumps)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('examples/markets/offer_buy_market.json'))
    args = parser.parse_args()
    config = MarketConfig(n_agents=3, n_tokens=3, task_dependency_range=(1, 3),
                          budget_leeway=.2, seed=42, exact_state_limit=2000)
    result = generate_market(config)
    final = verify_protocol_solution(result.market, result.initial_state, result.reference_solution)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(dumps(result)+'\n')
    print(dumps(protocol_summary(result.market, result.initial_state, final)))
    print('Feasibility:', result.feasibility_status, 'optimality:', result.status)


if __name__ == '__main__':
    main()

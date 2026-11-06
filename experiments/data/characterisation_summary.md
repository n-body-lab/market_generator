# Controlled market studies: measured summary

See difficulty_validation.md for definitions, configurations and limitations.

## presets

| Condition | Returned / requested | Mean attempts | Mean generation ms | Mean depth | Mean HHI | Mean F (available n) | Proven optima | Reference optimal |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| easy | 100/100 | 1.52 | 5.31 | 1.037 | 0.421 | — (0) | 0 | 0 |
| medium | 100/100 | 1.57 | 6.96 | 1.391 | 0.407 | — (0) | 0 | 0 |
| hard | 100/100 | 1.74 | 10.36 | 1.969 | 0.685 | — (0) | 0 | 0 |

## A

| Condition | Returned / requested | Mean attempts | Mean generation ms | Mean depth | Mean HHI | Mean F (available n) | Proven optima | Reference optimal |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| [1, 1] | 100/100 | 2.46 | 5.03 | 1.000 | 0.724 | — (0) | 100 | 84 |
| [1.5, 2] | 100/100 | 4.41 | 8.77 | 1.661 | 0.640 | — (0) | 100 | 69 |
| [2, 3] | 99/100 | 28.29 | 54.35 | 2.056 | 0.746 | — (0) | 99 | 60 |

## A_conflict

| Condition | Returned / requested | Mean attempts | Mean generation ms | Mean depth | Mean HHI | Mean F (available n) | Proven optima | Reference optimal |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| [1, 1] | 0/100 | 100.00 | 224.63 | — | — | — (0) | 0 | 0 |

## B

| Condition | Returned / requested | Mean attempts | Mean generation ms | Mean depth | Mean HHI | Mean F (available n) | Proven optima | Reference optimal |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 100/100 | 1.00 | — | — | — | 0.500 (100) | 0 | 0 |
| 1 | 100/100 | 1.00 | — | — | — | 0.000 (100) | 0 | 0 |
| 4 | 100/100 | 1.00 | — | — | — | 0.000 (100) | 0 | 0 |

## C

| Condition | Returned / requested | Mean attempts | Mean generation ms | Mean depth | Mean HHI | Mean F (available n) | Proven optima | Reference optimal |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| (0.1, [0, 0.5]) | 100/100 | 4.56 | 7.78 | 1.133 | 0.904 | 0.243 (100) | 100 | 98 |
| (0.1, [0.8, 1.0]) | 100/100 | 1.83 | 3.91 | 1.109 | 0.893 | 0.133 (100) | 100 | 98 |
| (1.0, [0, 0.5]) | 100/100 | 4.40 | 9.16 | 1.149 | 0.684 | 0.261 (100) | 100 | 98 |
| (1.0, [0.8, 1.0]) | 100/100 | 1.95 | 3.33 | 1.102 | 0.671 | 0.152 (100) | 100 | 99 |
| (5.0, [0, 0.5]) | 100/100 | 4.13 | 8.56 | 1.104 | 0.591 | 0.243 (99) | 100 | 99 |
| (5.0, [0.8, 1.0]) | 100/100 | 2.03 | 4.81 | 1.083 | 0.584 | 0.162 (99) | 100 | 95 |

## D

| Condition | Returned / requested | Mean attempts | Mean generation ms | Mean depth | Mean HHI | Mean F (available n) | Proven optima | Reference optimal |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| (2, 2) | 100/100 | 1.00 | 1.86 | 0.990 | 0.870 | — (0) | 100 | 100 |
| (3, 2) | 100/100 | 1.00 | 2.43 | 1.097 | 0.805 | — (0) | 100 | 96 |
| (3, 3) | 100/100 | 1.00 | 2.00 | 1.107 | 0.738 | — (0) | 100 | 94 |
| (4, 3) | 100/100 | 1.00 | 3.55 | 1.205 | 0.680 | — (0) | 100 | 73 |

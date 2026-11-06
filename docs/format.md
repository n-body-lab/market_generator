# HIVEMARKET JSON 0.1

Every export is `{ "schema_version": "hivemarket/0.1", "data": ... }`.
`dumps` accepts any model, solution, result or experiment. The accompanying schema
specifies a complete **generation-result** export. `loads` returns plain JSON
values and rejects unknown schema versions. Typed decoders are explicit.

Agent/token IDs are zero-based dense integers. Prices are buyer-major matrices;
zero diagonal is unused. Credit and message amounts are integral. Tasks and
progress export as sorted arrays representing sets; token owner arrays are indexed
by token. Histories include the initial and current owner. Transfer events contain
sequence, action, quoted price, buyer/seller messages, nullable future signature.
Exploratory message counters account for expenditure but do not certify who sent
which message; the V0.1 event log certifies token transfers only.

A solution stores `actions` and objective `[execution_messages, transfers,
gross_payments]`. Reference budgets are before leeway. `candidates` maps `"s,b"`
to retained walks `[source,...,buyer]`. Dictionary keys in metrics are strings
in JSON. `config` stores the complete seed/configuration; optional metrics can
be null when constructing results manually. Reproducibility assumes the same
package/NumPy/NetworkX versions; dependency upgrades may change random sampling
or equally good route choices. JSON stores integers exactly, but JavaScript
consumers must use BigInt-aware decoding for large search-space proxies.

`decode_result` validates the market, state and all supplied solution schedules.
It checks budgets, route/candidate consistency and re-runs exact search to confirm
a claimed optimum; inability to reproduce a proof rejects the import. Signatures
are not authenticated. JSON Schema checks shape, while typed Python validators
check semantic constraints. This is an integration format, not a signed proof
certificate. Whole generator exports reveal private tasks and inventories; use
`local_view` for per-agent payloads.

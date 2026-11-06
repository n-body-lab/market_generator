# Mathematical specification (V0.1)

Agents A={0,...,n-1}, tokens T={0,...,k-1}. Prices P[i,j] are the
integer credits buyer i pays seller j; off-diagonal entries are finite positive
integers and the unused diagonal is zero. Integral credit units are a deliberate,
reversible restriction: scale monetary quantities before constructing a market.
There is exactly one owner o(t). A task R_i is a set, and progress S_i records
all required tokens ever possessed. Initially S_i=R_i intersect o^-1(i).

A transfer (t,s,b) requires o(t)=s and b!=s. The communication policy assigns
nonnegative integer message counts (m_b,m_s). All messages cost one credit.
The buyer must hold P[b,s]+m_b and seller m_s **before** the atomic transfer.
Balances change by (-P[b,s]-m_b,+P[b,s]-m_s); total credits decrease only
by m_b+m_s. Progress adds t to S_b if required, permanently. Histories append
b even for repeat visits. Events are ordered, contain the quoted price and message
counts, and admit an optional signature field; V0.1 verifies by replay, not
cryptography. Simulation is trusted enforcement, not a distributed ledger.
Exploratory messages consume the sender's credits, transfer no token and add no
information in this model. The protocol exposes their accounting but neither
reference construction nor exact search assumes they are necessary.

Only the generator sees (P,o,R) jointly. Local snapshots contain the agent's
inventory, progress, task, balance, incident incoming/outgoing prices and n.
They expose neither other tasks/inventories nor reference solutions. Snapshot
construction is an API boundary, not isolation against hostile Python code.

For a selected ordered schedule let d_i be cumulative net expenditure before an
action. Its minimum initial balance is max(0, max_action(d_i + q_i)), where q_i
is that agent's pre-action affordability requirement (buyer price plus messages,
seller messages). This includes earlier sales financing later purchases, and is
componentwise necessary and sufficient for this fixed schedule. Relative leeway
adds ceil(lambda_i B_i^ref); absolute leeway adds ceil(lambda_i). This is not
a globally minimum endowment theorem.

Objective is lexicographic (execution messages, transfers, gross payments).
With a fixed messages-per-transfer policy, the first two coordinates are redundant.
No claim about minimum discovery communication is made. All transfers on the
complete directed graph remain legal, regardless of candidate-route depth.
Candidate paths are bounded walks (positive prices make cycles unnecessary
for the cheapest source–destination path); complete token walks can revisit agents without a
length bound. Routing costs P[next,current] follow ownership direction.

Exact optimisation uses uniform-cost search over (owners, progress, balances).
Histories do not affect future legal actions and can be omitted from search keys.
With fixed integer initial credits, balances are bounded by total initial credits;
ownership and progress are finite. Each edge increases transfers, so nonnegative
lexicographic edge costs permit label-setting Dijkstra. Popping a goal proves
global optimality among all feasible token-transfer schedules under this policy.
Exhaustion proves infeasibility; a state cap proves neither. Exploratory messages
are omitted because removing them preserves feasibility and improves messages;
this argument applies only to the documented information-free V0.1 semantics.
A reference incumbent gives a valid lexicographic upper bound. Exact search is
optional and capped, with status and proof scope exported explicitly.

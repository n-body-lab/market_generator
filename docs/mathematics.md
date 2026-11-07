# Mathematical specification (V0.1)

Agents A={0,...,n-1}, tokens T={0,...,k-1}. Prices P[i,j] are the
integer credits buyer i pays seller j; off-diagonal entries are finite positive
integers and the unused diagonal is zero. Integral credit units are a deliberate,
reversible restriction: scale monetary quantities before constructing a market.
There is exactly one owner o(t). A task R_i is a set, and progress S_i records
all required tokens ever possessed. Initially S_i=R_i intersect o^-1(i).

An OFFER identifies (id,t,s,b), with b!=s, and consumes one credit from b.
It does not require o(t)=s or reserve purchase money. It remains active across
ownership changes. WITHDRAW by b closes only that offer for free, without a refund.
BUY requires that matching offer active, o(t)=s, and balance_b>=P[b,s]. It atomically
transfers price P[b,s] from b to s and ownership to b, with no communication charge.
Only its offer closes. Progress adds t to S_b permanently; histories append b,
including repeat visits. Messages consume credits; trade payments conserve them.
Independent exploratory messages retain their separate one-credit accounting.
Provenance is verified by replay, not authenticated cryptographically.

For the reference normal form each transfer has exactly one immediately preceding
OFFER. Its combined delta is (-P[b,s]-1, +P[b,s]); the compact State event's message
allocation denotes that OFFER rather than a BUY tax. Historical nonstandard
fixed-message policies are retained only as labelled compatibility models.

Only the generator sees (P,o,R) jointly. Local snapshots contain the agent's
inventory, progress, task, balance, incident incoming/outgoing prices and n.
They expose neither other tasks/inventories nor reference solutions. Snapshot
construction is an API boundary, not isolation against hostile Python code.

For a selected ordered schedule let d_i be cumulative net expenditure before an
action. Its minimum initial balance is max(0, max_action(d_i + q_i)), where q_i
is that agent's pre-action affordability requirement (one credit for OFFER, matrix price for BUY, zero for WITHDRAW). This includes earlier sales financing later purchases, and is
componentwise necessary and sufficient for this fixed schedule. Relative leeway
adds ceil(lambda_i B_i^ref); absolute leeway adds ceil(lambda_i). This is not
a globally minimum endowment theorem.

Objective is lexicographic (OFFER communication expenditure, transfers, gross payments).
In the reference normal form M=X, so the first two coordinates are redundant.
No claim about minimum discovery communication is made. All transfers on the
complete directed graph remain legal, regardless of candidate-route depth.
Candidate paths are bounded walks (positive prices make cycles unnecessary
for the cheapest source–destination path); complete token walks can revisit agents without a
length bound. Routing costs P[next,current] follow ownership direction.

Exact optimisation uses admissible-bound A* (or optional uniform-cost search) over (owners, progress, balances).
Histories do not affect future legal actions and can be omitted from search keys.
With fixed integer initial credits, balances are bounded by total initial credits;
ownership and progress are finite. Each edge increases transfers, so nonnegative
lexicographic edge costs and a consistent lower bound permit label-setting A*.
The bound counts remaining agent-token requirements K, qK messages, and minimum
incoming prices per requirement; each transfer can satisfy at most one. Popping a goal proves
global optimality among all feasible token-transfer schedules under this policy.
Exhaustion proves infeasibility; a state cap proves neither. Exploratory messages
are omitted because removing them preserves feasibility and improves messages;
this argument applies only to the documented information-free V0.1 semantics.
A reference incumbent gives a valid lexicographic upper bound. Exact search is
optional and capped, with status and proof scope exported explicitly.


For empty initial offers, omit unused offers/withdrawals and postpone every used
OFFER to just before its BUY. Balances before that point weakly increase, and the
retained credit funds the postponed OFFER. Thus the exact search on compact
transfer states remains globally valid under the revised rules in this normal
form. It does not optimise from an arbitrary state containing pending offers.
See `offer_protocol.md` for the full scope and historical-model distinction.

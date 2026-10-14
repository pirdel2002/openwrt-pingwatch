# Validation record

Release 0.3.0-3: 23 local tests passed, including direct-only report isolation, successful mocked direct-probe evidence, real WAN-route change rejection, irrelevant counter/set changes versus output-hook changes, and route cache normalization. User-supplied 0.3.0-2 output reached direct probes but both timed out and the broad evidence comparison reported path_changed. The corrected comparison and DNS/connect/TLS timing diagnostics still require router acceptance; healthy direct connectivity has not been demonstrated.

Release 0.3.0-2: 19 local tests passed. New regression fixtures cover native JSON null verdicts while preserving quoted text, safe inline conntrack verdict maps, and rejection of unsafe/dynamic maps. User output shows nftables 1.1.1 JSON/stateless support and output GID 9912 matches; actual direct-path verification still awaits the corrected parser on the router.

Release 0.3.0-1: 17 local Lua/Python tests and mocked LuCI rendering passed. New coverage includes conservative direct-firewall recognition, rejection of unknown output NAT, WAN validation, three-round median ranking, minimum spacing, history expiry/config reset, and direct fallback blocked by unknown errors or unverified direct health. Native nft/ubus/curl/group-changing child execution still requires router acceptance. No active route changes or deployments were performed by the agent.

Release 0.2.0-1: 14 local Lua/Python tests and mocked LuCI rendering passed. New coverage includes exact plan scope, protected rules, inactive shunt, stale/incomplete results, deleted candidates, unchanged defaults and small-gain suppression. Probe details and stale-plan display are exercised by the UI mock. No live router writes were performed. Direct fallback, recurring monitoring and automatic apply are not implemented in this release.

2026-10-14: local Windows execution only; no router connection or deployment.

- 8 Python/Lua 5.1 tests passed: dynamic inventory/redaction, protected shunt rules, guarded direct fallback, healthy-node ranking, generator mutation blocking and mark, mocked worker execution and cleanup, Lua syntax, package contents/modes.
- LuCI JavaScript rendered under DOM mocks; RTL, polling, read-only controls and empty JSON tables passed. This is not a browser screenshot or real LuCI verification.
- Shell service syntax check passed with Git Bash `-n`.
- IPK generated reproducibly from this source; outer archive, control/data members and executable modes inspected. Not installed using router opkg or an OpenWrt SDK.

Not validated: actual Passwall2 26.10.1-r2 generator/core execution, installed bypass rules for mark 255, socket-port race under router load, forced-kill cleanup, exact UCI rule IDs, real node/subscription counts, native LuCI page appearance and direct reachability. These are manual router acceptance checks; automatic switching is absent.

Release 0.1.0-6: local tests additionally cover fixed diagnostic labels, redacted config shape and config-only operation preserving prior health results without probes/core launches. User-supplied router output for 0.1.0-5 reports 34 Nodes: 10 healthy, 16 unsuccessful probes, 8 core validation errors; three subscriptions, unchanged config snapshot and shunt guard passing. Independent firewall/bypass verification remains outstanding.

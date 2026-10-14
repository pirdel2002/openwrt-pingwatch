# Validation record

2026-10-14: local Windows execution only; no router connection or deployment.

- 8 Python/Lua 5.1 tests passed: dynamic inventory/redaction, protected shunt rules, guarded direct fallback, healthy-node ranking, generator mutation blocking and mark, mocked worker execution and cleanup, Lua syntax, package contents/modes.
- LuCI JavaScript rendered under DOM mocks; RTL, polling, read-only controls and empty JSON tables passed. This is not a browser screenshot or real LuCI verification.
- Shell service syntax check passed with Git Bash `-n`.
- IPK generated reproducibly from this source; outer archive, control/data members and executable modes inspected. Not installed using router opkg or an OpenWrt SDK.

Not validated: actual Passwall2 26.10.1-r2 generator/core execution, installed bypass rules for mark 255, socket-port race under router load, forced-kill cleanup, exact UCI rule IDs, real node/subscription counts, native LuCI page appearance and direct reachability. These are manual router acceptance checks; automatic switching is absent.

Release 0.1.0-6: local tests additionally cover fixed diagnostic labels, redacted config shape and config-only operation preserving prior health results without probes/core launches. User-supplied router output for 0.1.0-5 reports 34 Nodes: 10 healthy, 16 unsuccessful probes, 8 core validation errors; three subscriptions, unchanged config snapshot and shunt guard passing. Independent firewall/bypass verification remains outstanding.

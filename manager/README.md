# PingWatch Passwall Manager — advisory manager

Version 0.3.0-1. A separate package beside PingWatch 1.5.3; does not replace its SMS/LED service.

## Safety and scope

- Observation only. No UCI writes, route changes, firewall mutations, subscription updates or Passwall restarts.
- Only a future phase may manage `passwall2.rulenode.default_node`. PrivateIP, Iran and Devices must remain `_direct`; a missing/mismatched rule blocks recommendations.
- Node and `subscribe_list` inventory is freshly read each run. Add/remove subscriptions through Passwall2; rerun after subscription refresh completes. No hard-coded 36/3 counts.
- Sequential tests use native installed Passwall generators, a copied UCI snapshot, an isolated loopback SOCKS core and two HTTPS 204 endpoints. TLS is verified. Latency is total HTTP transaction time, not ICMP ping.
- No shell calls to native `app.sh` or `test.sh`; no broad process kills. Generated config and snapshot are private RAM files, removed after tests. Public results omit URLs, addresses, remarks, UUIDs and credentials.
- Direct tests require conservative evidence of firewall bypass, an up physical WAN, and its route. Unsupported or changing evidence leaves direct **unverified**. Only three verified successful rounds with no usable Node permit an advisory `_direct` plan. Transient/unknown errors still block fallback; deterministic core rejection (exit 23) counts as unusable.
- Native core outbound mark 255 is applied as used by upstream Passwall2. Installed firewall bypass behavior still needs verification on the actual router. Health here is advisory until that verification.
- Chained/interface/plugin/endpoint configurations are unsupported in phase 1. Their tests do not trigger fallback. A config rejected by the installed core reports an error.
- Results are atomic under `/tmp/pingwatch-manager`; LuCI refreshes every five seconds. Tests are manual, one run at a time; no scheduled loop or boot enablement.

## Install (manual, after router approval)

Keep a local backup of `/etc/config/passwall2` and existing PingWatch config. Do not share either file. Copy only the IPK to the router, then:

```sh
opkg install /root/luci-app-pingwatch-manager_0.3.0-1_all.ipk
/etc/init.d/rpcd restart
```

Open **Services → PingWatch Passwall Manager**. Run one batch manually:

```sh
/etc/init.d/pingwatch-manager start
```

Wait until the page shows completion. A batch of 36 nodes can take several minutes. To cancel:

```sh
/etc/init.d/pingwatch-manager stop
```

No enable command is needed. After cancellation, a forced kill or power interruption, RAM state may be stale; temporary cores are bounded by a 25-second timeout plus a 2-second kill grace period; reboot clears it. If a lock remains, verify the worker and its test core have exited before manually removing the lock and private work directory. Never remove a live worker's lock.

For a repeat run after completion: ` /etc/init.d/pingwatch-manager restart `. This restarts only the separate test service.

Uninstall:

```sh
/etc/init.d/pingwatch-manager stop
opkg remove luci-app-pingwatch-manager
/etc/init.d/rpcd restart
```

## Build and validation

### Advisory plan

Each completed health batch now records a plan for **only** `passwall2.rulenode.default_node`, including its current value and the proposed Node. This plan never writes UCI or restarts Passwall. It requires the active global Node to be `rulenode`, the protected rules to stay direct, a current snapshot and fresh results (five minutes). A working default is retained unless improvement exceeds both 20 percent and 100 milliseconds. A missing/deleted candidate blocks the plan.

Plans describe the snapshot at batch completion; the page marks them expired after five minutes. Any future apply operation must independently revalidate the current full config, Node identity and health before writing. There is no apply command in this release. Automatic switching and recurring monitoring remain pending.

Each HTTPS probe now reports its fixed endpoint number, HTTP status, curl exit code, measured duration and a fixed failure category. Failed/informational Nodes stay in the inventory and are naturally excluded from healthy candidates. No manual informational-node exclusion list is maintained.

`python manager/build.py` produces IPK, source archive and SHA256SUMS under `dist/`. For SDK builds, place `manager/` under `package/pingwatch-manager` and build `package/pingwatch-manager/compile`.

Local tests: `python manager/tests/test_manager.py` (test-only `lupa` Lua 5.1 runtime), `node manager/tests/test_view.js`. Native LuCI, nixio, OpenWrt opkg, installed Passwall generators, Xray/sing-box and physical-router behavior are **not** validated locally. No router deployment was performed.

## Follow-up acceptance on router

Before automatic management: verify exact installed generator signatures, mark bypass, core PID cleanup, unchanged config/firewall/active default, two-endpoint results, cancellation, and inventory after adding/removing a subscription. Verify direct connectivity independently before implementing fallback. Any live step requires explicit router authorization.

## Stability and direct path in 0.3.0

Run three full batches, leaving at least 30 seconds between completion times. History is RAM-only and holds three rounds from the last 15 minutes. A SHA-256 fingerprint of the full config scopes the history; any config/subscription change, reboot, unavailable hash or backward clock change resets confidence. A Node must pass both endpoints in all three rounds. Ranking uses the median of its three worst-endpoint times, then the existing improvement threshold. A single-batch recommendation is separate from the stable `plan`.

Direct tests use separate curl child processes with GID 9912, proxy environment cleared, curl config disabled, IPv4, WAN interface binding, HTTPS certificate verification and numeric-bootstrap DoH at `https://1.1.1.1/dns-query`. This changes only the test child's socket behavior and group, not router configuration. The probe targets remain Google and Cloudflare HTTPS 204 endpoints.

Before and after the tests, the worker inspects stateless nft JSON and the WAN device/protocol/route. All IPv4/inet output chains must either be safe to traverse or have the exact GID 9912 return before modification statements. Unknown NAT/mark/proxy actions, unsupported nft JSON, legacy iptables rules, unavailable WAN evidence or changed evidence prevent path verification. The WAN logical interface must be named `wan` with DHCP/static/PPPoE; custom WAN names, VPN uplinks and other backends are conservatively unsupported. These checks prove the observed router-output path for the probes; they do not guarantee all destinations or future client DNS behavior after a default change.

Dependencies used for evidence are `nft` with JSON/stateless output, `ubus`, `ip`, `sha256sum`, and curl with DoH/interface support. Missing capabilities fail closed and do not require replacing firewall packages. Runtime firewall rules, device names, route addresses and the config fingerprint are never published in result JSON.

Sources: [Passwall2 output bypass](https://github.com/Openwrt-Passwall/openwrt-passwall2/blob/492309ea672c9c40725e2a72cb4d4f1625d9ee53/luci-app-passwall2/root/usr/share/passwall2/nftables.sh), [curl DoH options](https://curl.se/docs/manpage.html), [DoH verification behavior](https://curl.se/libcurl/c/CURLOPT_DOH_URL.html).

## Config validation diagnosis

Run `/usr/sbin/pingwatch-manager-worker --check-configs`, then `/usr/sbin/pingwatch-manager-results --configs`.
This generates and validates configs without starting test cores or running HTTPS probes. Results are stored separately in `/tmp/pingwatch-manager/config-checks.json`; prior health results remain available. `config_valid` means only that the core accepted the config, not that the Node is reachable.

Validation output is captured privately, classified into fixed labels, and removed. No raw error body is returned. Diagnostics include an exit code and allowlisted protocol/transport/security labels. `unclassified_core_error` means the error is not yet recognized; do not publish raw logs or configs. Categories are diagnostic hints, not proof of a specific bad credential or server defect.

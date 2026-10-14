# PingWatch Passwall Manager — phase 1

Version 0.1.0-4. A separate package beside PingWatch 1.5.3; does not replace its SMS/LED service.

## Safety and scope

- Observation only. No UCI writes, route changes, firewall mutations, subscription updates or Passwall restarts.
- Only a future phase may manage `passwall2.rulenode.default_node`. PrivateIP, Iran and Devices must remain `_direct`; a missing/mismatched rule blocks recommendations.
- Node and `subscribe_list` inventory is freshly read each run. Add/remove subscriptions through Passwall2; rerun after subscription refresh completes. No hard-coded 36/3 counts.
- Sequential tests use native installed Passwall generators, a copied UCI snapshot, an isolated loopback SOCKS core and two HTTPS 204 endpoints. TLS is verified. Latency is total HTTP transaction time, not ICMP ping.
- No shell calls to native `app.sh` or `test.sh`; no broad process kills. Generated config and snapshot are private RAM files, removed after tests. Public results omit URLs, addresses, remarks, UUIDs and credentials.
- Direct health is explicitly **unverified**. The worker never recommends `_direct`. Future failover requires a separately verified direct test and complete negative Node results. Unsupported/error tests remain unknown.
- Native core outbound mark 255 is applied as used by upstream Passwall2. Installed firewall bypass behavior still needs verification on the actual router. Health here is advisory until that verification.
- Chained/interface/plugin/endpoint configurations are unsupported in phase 1. Their tests do not trigger fallback. A config rejected by the installed core reports an error.
- Results are atomic under `/tmp/pingwatch-manager`; LuCI refreshes every five seconds. Tests are manual, one run at a time; no scheduled loop or boot enablement.

## Install (manual, after router approval)

Keep a local backup of `/etc/config/passwall2` and existing PingWatch config. Do not share either file. Copy only the IPK to the router, then:

```sh
opkg install /root/luci-app-pingwatch-manager_0.1.0-4_all.ipk
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

`python manager/build.py` produces IPK, source archive and SHA256SUMS under `dist/`. For SDK builds, place `manager/` under `package/pingwatch-manager` and build `package/pingwatch-manager/compile`.

Local tests: `python manager/tests/test_manager.py` (test-only `lupa` Lua 5.1 runtime), `node manager/tests/test_view.js`. Native LuCI, nixio, OpenWrt opkg, installed Passwall generators, Xray/sing-box and physical-router behavior are **not** validated locally. No router deployment was performed.

## Follow-up acceptance on router

Before automatic management: verify exact installed generator signatures, mark bypass, core PID cleanup, unchanged config/firewall/active default, two-endpoint results, cancellation, and inventory after adding/removing a subscription. Verify direct connectivity independently before implementing fallback. Any live step requires explicit router authorization.

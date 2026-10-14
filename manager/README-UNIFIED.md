# PingWatch 1.6.0-1 — one application

The package is now `luci-app-pingwatch`, upgrading PingWatch 1.5.3. Services has one **PingWatch** entry. Existing Status, Settings and Targets remain, with a **مدیریت Passwall** tab containing the on/off control and test results. Existing `/etc/config/pingwatch` is an opkg conffile and is not reset. SMS and LED helpers are retained.

## Install from an existing 0.3.x separate Manager

Copy `dist/luci-app-pingwatch_1.6.0-1_all.ipk` to `/root/`, then:

```sh
cp -p /etc/config/pingwatch /root/pingwatch-before-1.6.0.conf &&
opkg remove luci-app-pingwatch-manager &&
opkg install /root/luci-app-pingwatch_1.6.0-1_all.ipk
```

Only remove the separate Manager package. Do not remove the original PingWatch package. Reload LuCI with Ctrl+F5. The installer clears menu cache and restarts rpcd, but never enables the new manager. Keep the backup private.

## On/off behavior

Management is **off by default** in `/etc/config/pingwatch_manager`. Turning on the tab's checkbox explicitly allows automatic changes to `passwall2.rulenode.default_node` after checks. It also enables the manager service at boot. Turning it off prevents new writes and disables manager boot startup; an in-flight test finishes safely, and the last active default stays in place. SMS and LED switches retain their previous meanings. A rollback already needed by an in-flight apply can still finish after switching off.

CLI equivalents:

```sh
/usr/sbin/pingwatch-manager-control enable
/usr/sbin/pingwatch-manager-control disable
/usr/sbin/pingwatch-manager-control
```

The daemon performs a sequential full batch, considers an apply, then waits 60 seconds. Three fresh rounds within 15 minutes and unchanged full config are required. WAN direct verification uses DNS advertised by WAN and does not change router DNS settings. Informational nodes are not specially classified; they remain in the normal test results.

## Guarded apply

Only `rulenode.default_node` may differ semantically. The active global Node must remain `rulenode`; PrivateIP, Iran and Devices must be `_direct`. Pending UCI edits, stale results, config fingerprint changes, deleted Nodes and failed fresh candidate checks block writes. Normal changes require a stable candidate; `_direct` requires three verified direct-success rounds and no usable Node in those rounds.

Before writing, the worker re-tests the candidate and checks that the switch is still on and the full source file is unchanged. A private RAM backup is retained under `/tmp/pingwatch-manager/passwall2.before`. UCI editing occurs in a private directory; the installed file is replaced atomically after comparison. The controller restarts Passwall2 and probes two HTTPS endpoints through the native active shunt SOCKS listener, with TLS verification.

Failure disables automatic management and attempts to restore only the previous default, preserving unrelated concurrent edits. If the default or protected shunt has changed concurrently, rollback refuses to overwrite it and records `rollback_conflict` for manual attention. Successful restore is distinguished from a restore whose connectivity cannot be verified. Restarting Passwall2 may briefly interrupt active connections. A 5-minute cooldown follows a verified change.

Results: `/usr/sbin/pingwatch-manager-results`; control status includes `last_action`. Raw configs, credentials, IPs, subscription URLs and logs are never returned by these helpers. Private backups contain secrets; do not share them. Force-killing a worker/controller can leave a lock requiring inspection; do not delete a live lock.

## Validation and build

Run `python manager/build.py` to produce unified IPK, complete source archive and SHA256SUMS. The build merges the frozen original source and the manager module, embeds its view as a tab and merges the ACL. The archive includes both source directories. For SDK builds keep `manager/` and `openwrt-pingwatch-1.5.3/` as siblings under the SDK package directory; Python 3 is needed for Build/Prepare.

Local tests cover default-off packaging, one menu, preserved config conffiles/SMS helpers, toggle dispatch, transaction gating, scope checks, re-test failure, compare-before-write, rollback and concurrent-edit protection. Native LuCI rendering, native UCI transaction execution, actual apply and rollback have **not yet been validated on the router**. Earlier user-provided output did verify the isolated direct-WAN test and normal Node health checks.


## 1.6.1 UI update

Compact RTL status cards, accessible on/off switch, responsive striped results table, Persian failure labels, and healthy nodes sorted by response time. Node remarks replace IDs in the table, recommendation and proposed route. Existing reports resolve remarks locally without another test round. No routing policy changes.

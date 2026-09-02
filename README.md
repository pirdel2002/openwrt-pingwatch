# OpenWrt PingWatch

PingWatch is a LuCI application for OpenWrt that monitors network targets, controls an RGB status LED, and sends IPPanel SMS notifications on outages and recoveries.

Current version: **1.5.3-1**

## Features

- ICMP, TCP, HTTP(S), and DNS target checks
- Per-target fail/recovery thresholds
- Per-target notification mode: both, down only, recovery only, or disabled
- Global and per-target SMS recipients
- IPPanel SMS integration
- RAM-based smart SMS queue for temporary IPPanel/WAN outages
- Recovery summary messages using 24-hour outage windows, e.g. `14:23–14:31`
- Internet outage aggregation via reference targets
- RGB LED status with target priority and per-target colors
- LuCI status page showing the active LED color and source
- Transient runtime state under `/tmp/pingwatch` to avoid flash wear

## Install

Copy the IPK to the router, then run:

```sh
opkg install /root/luci-app-pingwatch_1.5.3-1_all.ipk
/etc/init.d/pingwatch restart
```

For LuCI cache refresh when upgrading:

```sh
rm -f /tmp/luci-indexcache
rm -rf /tmp/luci-modulecache
/etc/init.d/rpcd restart
/etc/init.d/uhttpd restart
/etc/init.d/pingwatch restart
```

## Package

The installable package is available in `releases/luci-app-pingwatch_1.5.3-1_all.ipk`.

## Source layout

The `package/` directory mirrors the installed OpenWrt filesystem plus package control files.

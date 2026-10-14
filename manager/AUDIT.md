# Source review

Reviewed repository main at `9284df88ca5f7e63ca173d33b5e64cb3dcc7f681`.
The tracked repository contains README and two release files; its README refers to `package/`, which is absent. Extracted `releases/openwrt-pingwatch-1.5.3-source.tar.gz` into `openwrt-pingwatch-1.5.3/` unchanged. The package has a shell worker, UCI config, SMS/LED helpers and a modern LuCI JS view using `file.exec`; existing ACL permits PingWatch operations, not Passwall management.

Upstream Passwall2 inspected at main `492309ea672c9c40725e2a72cb4d4f1625d9ee53`:

- [test.sh](https://github.com/Openwrt-Passwall/openwrt-passwall2/blob/492309ea672c9c40725e2a72cb4d4f1625d9ee53/luci-app-passwall2/root/usr/share/passwall2/test.sh): temporary `run_socks`, `socks5h`, port allocation; TLS disabled and pattern-based process cleanup.
- [app.sh](https://github.com/Openwrt-Passwall/openwrt-passwall2/blob/492309ea672c9c40725e2a72cb4d4f1625d9ee53/luci-app-passwall2/root/usr/share/passwall2/app.sh): run_socks/core validation, shared runtime/cache, separate Xray and sing-box generators. Full start/stop includes firewall, DNS, UCI and scheduled tasks; unsuitable for observation worker.
- [util_xray.lua](https://github.com/Openwrt-Passwall/openwrt-passwall2/blob/492309ea672c9c40725e2a72cb4d4f1625d9ee53/luci-app-passwall2/luasrc/passwall2/util_xray.lua) and [util_sing-box.lua](https://github.com/Openwrt-Passwall/openwrt-passwall2/blob/492309ea672c9c40725e2a72cb4d4f1625d9ee53/luci-app-passwall2/luasrc/passwall2/util_sing-box.lua): gen_config accepts node/local SOCKS options; side effects can include nested cores, interface bookkeeping, direct-node list and firewall set flushing. Adapter blocks mutation calls and rejects unsupported layouts.
- [api.lua](https://github.com/Openwrt-Passwall/openwrt-passwall2/blob/492309ea672c9c40725e2a72cb4d4f1625d9ee53/luci-app-passwall2/luasrc/passwall2/api.lua): UCI cursor and shared filesystem/system interfaces used by generators. Worker redirects runtime paths and supplies a read-only snapshot cursor.
- [nixio socket API](https://github.com/openwrt/luci/blob/master/libs/luci-lib-nixio/docsrc/nixio.Socket.lua): getsockname returns address and port for private test listener selection.

Upstream main is a reference, not proof of installed Passwall2 26.10.1-r2 compatibility. Versions and 36 Nodes/3 subscriptions were supplied by the user; live values were not inspected. Cached prior conversation omitted assistant bodies and attachment contents; no sensitive attachment was used or published.

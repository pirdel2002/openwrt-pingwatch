include $(TOPDIR)/rules.mk
PKG_NAME:=luci-app-pingwatch
PKG_VERSION:=1.6.1
PKG_RELEASE:=1
include $(INCLUDE_DIR)/package.mk
define Package/luci-app-pingwatch
  SECTION:=luci
  CATEGORY:=LuCI
  SUBMENU:=3. Applications
  TITLE:=PingWatch with integrated Passwall Manager
  DEPENDS:=+luci-base +luci-compat +luci-lib-jsonc +lua +libuci-lua +curl +ca-bundle +uclient-fetch +rpcd +luci-app-passwall2
  CONFLICTS:=luci-app-pingwatch-manager
  PKGARCH:=all
endef
define Build/Compile
endef
define Build/Prepare
	$(MKDIR) $(PKG_BUILD_DIR)
	python3 ./build.py --stage-dir $(PKG_BUILD_DIR)
endef
define Package/luci-app-pingwatch/conffiles
/etc/config/pingwatch
/etc/config/pingwatch_manager
endef
define Package/luci-app-pingwatch/postinst
#!/bin/sh
[ -n "$$IPKG_INSTROOT" ] && exit 0
for f in /tmp/luci-indexcache*; do [ -f "$$f" ] && rm -f "$$f"; done
/etc/init.d/rpcd restart >/dev/null 2>&1 || true
exit 0
endef
define Package/luci-app-pingwatch/install
	$(CP) $(PKG_BUILD_DIR)/root/* $(1)/
	chmod 0755 $(1)/usr/sbin/pingwatch-manager-* $(1)/etc/init.d/pingwatch-manager
endef
$(eval $(call BuildPackage,luci-app-pingwatch))

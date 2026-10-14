include $(TOPDIR)/rules.mk
PKG_NAME:=luci-app-pingwatch-manager
PKG_VERSION:=0.1.0
PKG_RELEASE:=2
include $(INCLUDE_DIR)/package.mk
define Package/luci-app-pingwatch-manager
  SECTION:=luci
  CATEGORY:=LuCI
  SUBMENU:=3. Applications
  TITLE:=PingWatch Passwall Manager (observe only)
  DEPENDS:=+luci-base +luci-compat +luci-lib-jsonc +lua +libuci-lua +curl +ca-bundle +luci-app-passwall2
  PKGARCH:=all
endef
define Build/Compile
endef
define Package/luci-app-pingwatch-manager/install
	$(CP) ./root/* $(1)/
	chmod 0755 $(1)/usr/sbin/pingwatch-manager-* $(1)/etc/init.d/pingwatch-manager
endef
$(eval $(call BuildPackage,luci-app-pingwatch-manager))

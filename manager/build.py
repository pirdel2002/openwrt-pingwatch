"""Build architecture-independent IPK and a reproducible source archive."""
import gzip, hashlib, io, tarfile, json, argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'dist'
OUT.mkdir(exist_ok=True)
VERSION='1.6.1-1'
PACKAGE='luci-app-pingwatch'
control=f'''Package: {PACKAGE}
Version: {VERSION}
Architecture: all
Depends: libc, luci-base, luci-compat, luci-lib-jsonc, lua, libuci-lua, curl, ca-bundle, rpcd, uclient-fetch, luci-app-passwall2
Section: luci
Priority: optional
Description: PingWatch monitoring with integrated guarded Passwall management
Conflicts: luci-app-pingwatch-manager
Replaces: luci-app-pingwatch-manager
'''.encode()
def archive(entries):
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w',format=tarfile.USTAR_FORMAT) as t:
        directories=set()
        for name,_,_ in entries:
            parent=Path(name).parent
            while parent.as_posix()!='.':
                directories.add(parent.as_posix())
                parent=parent.parent
        for name in sorted(directories, key=lambda n:(n.count('/'),n)):
            h=tarfile.TarInfo('./'+name+'/'); h.type=tarfile.DIRTYPE
            h.mode=0o755; h.mtime=0
            t.addfile(h)
        for name,data,mode in sorted(entries):
            h=tarfile.TarInfo(name); h.size=len(data); h.mode=mode; h.mtime=0
            t.addfile(h,io.BytesIO(data))
    return gzip.compress(buf.getvalue(),mtime=0)
files={}
original=ROOT.parent/'openwrt-pingwatch-1.5.3'
for p in original.rglob('*'):
    if p.is_file() and 'CONTROL' not in p.relative_to(original).parts:
        files[p.relative_to(original).as_posix()]=p.read_bytes().replace(b'\r\n',b'\n')
for p in (ROOT/'root').rglob('*'):
    if p.is_file():
        rel=p.relative_to(ROOT/'root').as_posix()
        if rel in ('usr/share/luci/menu.d/luci-app-pingwatch-manager.json','usr/share/rpcd/acl.d/luci-app-pingwatch-manager.json'): continue
        files[rel]=p.read_bytes().replace(b'\r\n',b'\n')
main_path='www/luci-static/resources/view/pingwatch/main.js'
main=files[main_path].decode()
for old,new in [
    ("'require network';", "'require network';\n'require view.pingwatch.manager as managerView';"),
    ('[settingsMap.render(), targetsMap.render()]','[settingsMap.render(), targetsMap.render(), managerView.render()]'),
    ("var buttons = [", "var managerPane = E('div', { 'data-pane': 'manager', 'style': 'display:none' }, [nodes[2]]);\n\t\t\tvar buttons = ["),
    ("tabButton(_('Targets'), 'targets', false)","tabButton(_('Targets'), 'targets', false),\n\t\t\t\ttabButton('مدیریت Passwall', 'manager', false)"),
    ('\t\t\t\ttargetsPane\n','\t\t\t\ttargetsPane,\n\t\t\t\tmanagerPane\n')]:
    assert main.count(old)==1,old
    main=main.replace(old,new)
files[main_path]=main.encode()
acl_path='usr/share/rpcd/acl.d/luci-app-pingwatch.json'
acl=json.loads(files[acl_path])
group=acl['luci-app-pingwatch']
group['read']['file']['/usr/sbin/pingwatch-manager-results']=['exec']
group['read']['file']['/usr/sbin/pingwatch-manager-control']=['exec']
for action in ('enable','disable'):
    group['write']['file']['/usr/sbin/pingwatch-manager-control '+action]=['exec']
files[acl_path]=json.dumps(acl,ensure_ascii=False,indent=2).encode()
data=[]
for rel,content in files.items():
    data.append(('./'+rel,content,0o755 if rel.startswith(('usr/sbin/','etc/init.d/')) else 0o644))
args=argparse.ArgumentParser(); args.add_argument('--stage-dir'); options=args.parse_args()
if options.stage_dir:
    for rel,content in files.items():
        dest=Path(options.stage_dir)/'root'/rel
        dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(content)
        dest.chmod(0o755 if rel.startswith(('usr/sbin/','etc/init.d/')) else 0o644)
postinst=b'''#!/bin/sh
[ -n "$IPKG_INSTROOT" ] && exit 0
for f in /tmp/luci-indexcache*; do [ -f "$f" ] && rm -f "$f"; done
/etc/init.d/rpcd restart >/dev/null 2>&1 || true
exit 0
'''
ipk=OUT/f'{PACKAGE}_{VERSION}_all.ipk'
# OpenWrt opkg accepts the standard outer gzip tar containing these members.
ipk.write_bytes(archive([('./debian-binary',b'2.0\n',0o644),('./control.tar.gz',archive([('./control',control,0o644),('./conffiles',b'/etc/config/pingwatch\n/etc/config/pingwatch_manager\n',0o644),('./postinst',postinst,0o755)]),0o644),('./data.tar.gz',archive(data),0o644)]))
source=OUT/f'openwrt-pingwatch-{VERSION}-source.tar.gz'
source.write_bytes(archive([(p.relative_to(ROOT.parent).as_posix(),p.read_bytes(),0o644) for base in (ROOT,original) for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts]))
(OUT/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in (ipk,source)))
print(ipk); print(source)

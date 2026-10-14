"""Build architecture-independent IPK and a reproducible source archive."""
import gzip, hashlib, io, tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'dist'
OUT.mkdir(exist_ok=True)
VERSION='0.1.0-1'
control=f'''Package: luci-app-pingwatch-manager
Version: {VERSION}
Architecture: all
Depends: luci-base, luci-compat, luci-lib-jsonc, lua, libuci-lua, curl, ca-bundle, luci-app-passwall2
Section: luci
Priority: optional
Description: PingWatch Passwall Manager observe-only test worker
'''.encode()
def archive(entries):
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w',format=tarfile.USTAR_FORMAT) as t:
        for name,data,mode in sorted(entries):
            h=tarfile.TarInfo(name); h.size=len(data); h.mode=mode; h.mtime=0
            t.addfile(h,io.BytesIO(data))
    return gzip.compress(buf.getvalue(),mtime=0)
data=[]
for p in (ROOT/'root').rglob('*'):
    if p.is_file():
        rel=p.relative_to(ROOT/'root').as_posix()
        data.append(('./'+rel,p.read_bytes(),0o755 if rel.startswith(('usr/sbin/','etc/init.d/')) else 0o644))
ipk=OUT/f'luci-app-pingwatch-manager_{VERSION}_all.ipk'
# OpenWrt opkg accepts the standard outer gzip tar containing these members.
ipk.write_bytes(archive([('./debian-binary',b'2.0\n',0o644),('./control.tar.gz',archive([('./control',control,0o644)]),0o644),('./data.tar.gz',archive(data),0o644)]))
source=OUT/f'pingwatch-manager-{VERSION}-source.tar.gz'
source.write_bytes(archive([(p.relative_to(ROOT.parent).as_posix(),p.read_bytes(),0o644) for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts]))
(OUT/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in (ipk,source)))
print(ipk); print(source)

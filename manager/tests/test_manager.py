import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / '.test-deps'))
from lupa.lua51 import LuaRuntime
ROOT = Path(__file__).resolve().parents[1]

class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('''
          sections={
            {['.name']='rulenode',['.type']='nodes',protocol='_shunt',PrivateIP='_direct',Iran='_direct',Devices='_direct'},
            {['.name']='node1',['.type']='nodes',protocol='vless',type='Xray',password='SECRET'},
            {['.name']='sub1',['.type']='subscribe_list',url='SECRET_URL'}
          }
          cursor={}
          function cursor:foreach(config,kind,fn) for _,s in ipairs(sections) do if s['.type']==kind then fn(s) end end end
          function cursor:get(config,id,key) for _,s in ipairs(sections) do if s['.name']==id then return s[key] end end end
        ''')
        self.lua.globals().policy = self.lua.execute((ROOT/'root/usr/share/pingwatch-manager/policy.lua').read_text())

    def test_dynamic_inventory_and_redaction(self):
        self.lua.execute('''
          local n,s=policy.inventory(cursor); assert(#n==1 and #s==1 and n[1].password==nil and s[1].url==nil)
          table.remove(sections,2); table.remove(sections,2)
          sections[#sections+1]={['.name']='newnode',['.type']='nodes',protocol='trojan',type='Sing-Box'}
          local n,s=policy.inventory(cursor); assert(#n==1 and n[1].id=='newnode' and #s==0)
        ''')

    def test_guard_all_protected_rules(self):
        self.lua.execute('''
          assert(policy.guard(cursor))
          for _,k in ipairs({'PrivateIP','Iran','Devices','protocol'}) do
            local old=sections[1][k]; sections[1][k]='wrong'; assert(not policy.guard(cursor)); sections[1][k]=old
          end
        ''')

    def test_fallback_requires_direct_confirmation(self):
        self.lua.execute('''
          local rows={{id='a',state='unhealthy'}}
          assert(policy.recommend(rows,true,false).node==nil)
          assert(policy.recommend(rows,true,true).node=='_direct')
          assert(policy.recommend({},true,false).node==nil)
          assert(policy.recommend(rows,false,true).state=='blocked')
          rows[2]={id='b',state='unsupported'}; assert(policy.recommend(rows,true,true).node==nil)
          rows[2].state='error'; assert(policy.recommend(rows,true,true).node==nil)
        ''')

    def test_rank_only_healthy(self):
        self.lua.execute('''
          local rows={{id='a',state='healthy',latency_ms=300},{id='b',state='healthy',latency_ms=90},{id='c',state='unhealthy',latency_ms=1}}
          assert(policy.recommend(rows,true,false).node=='b')
        ''')

    def test_worker_mock_end_to_end(self):
        code=(ROOT/'root/usr/sbin/pingwatch-manager-worker').read_text().split('\n',1)[1]
        self.lua.execute('''
          files={['/etc/config/passwall2']='SECRET_CONFIG'}; directories={}; published={}; calls={}; killed={}
          local fs={}
          function fs.mkdir(p,mode) assert(mode=='0700'); if directories[p] then return false end; directories[p]=true; return true end
          function fs.lstat(p) return directories[p] end
          function fs.readfile(p) return files[p] end
          function fs.writefile(p,v) files[p]=v; return true end
          function fs.rename(a,b) files[b]=files[a]; files[a]=nil; return true end
          function fs.unlink(p) files[p]=nil; return true end
          function fs.rmdir(p) directories[p]=nil; return true end
          package.preload['nixio.fs']=function() return fs end
          package.preload['nixio']=function() return {
            umask=function(mode) assert(mode=='0077') end,
            signal=function(_,mode) assert(mode=='ign' or mode=='dfl') end, nanosleep=function() end,
            fork=function() return 123 end, kill=function(p) killed[#killed+1]=p end, waitpid=function() end,
            socket=function() return {bind=function() return true end,getsockname=function() return '127.0.0.1',49000 end,
              close=function() end,connect=function() return true end} end
          } end
          package.preload['luci.jsonc']=function() return {stringify=function(s) published[#published+1]=s; return 'REDACTED' end} end
          package.preload['luci.model.uci']=function() return {cursor=function() return cursor end} end
          package.preload['luci.sys']=function() return {call=function(cmd)
            calls[#calls+1]=cmd
            if cmd:find('curl',1,true) then files['/tmp/pingwatch-manager/work/probe.txt']='204:0.120' end
            return 0
          end} end
          dofile=function() return policy end
        ''')
        self.lua.execute(code)
        self.lua.execute('''
          local s=published[#published]; assert(s.complete and not s.running and not s.route_changed)
          assert(s.rows[1].state=='healthy' and s.rows[1].latency_ms==120)
          assert(s.recommendation.node=='node1')
          assert(files['/etc/config/passwall2']=='SECRET_CONFIG')
          assert(files['/tmp/pingwatch-manager/work/config/passwall2']==nil)
          assert(files['/tmp/pingwatch-manager/work/core.json']==nil)
          assert(not directories['/tmp/pingwatch-manager/lock'])
          assert(#killed==1 and killed[1]==123)
          for _,cmd in ipairs(calls) do assert(not cmd:find('uci set',1,true) and not cmd:find('restart',1,true)) end
        ''')

    def test_lua51_syntax(self):
        for p in (ROOT/'root').rglob('*'):
            if p.is_file() and (p.suffix=='.lua' or p.name.startswith('pingwatch-manager-')):
                code=p.read_text()
                if code.startswith('#!'): code=code.split('\n',1)[1]
                result=self.lua.eval('loadstring')(code)
                self.assertFalse(isinstance(result,tuple),str(p))

    def test_generator_isolates_snapshot_and_mark(self):
        self.lua.execute('''
          arg={'/tmp/pingwatch-manager/work/config','node1','49000'}
          local reader={get_all=function() return {['.type']='nodes',protocol='vless',type='Xray'} end}
          package.preload['luci.model.uci']=function() return {cursor=function(p)
            assert(p=='/tmp/pingwatch-manager/work/config'); return reader end} end
          config={inbounds={{listen='127.0.0.1',port=49000,protocol='socks'}},outbounds={{protocol='vless'}}}
          api={sys={exec=function() return 'Xray 26.10.10' end},jsonc={parse=function() return config end,stringify=function() return 'SAFE_OUTPUT' end}}
          package.preload['luci.passwall2.api']=function() return api end
          package.preload['luci.passwall2.util_xray']=function() return {gen_config=function(v)
            assert(v.node=='node1' and v.local_socks_address=='127.0.0.1')
            assert(not pcall(function() api.uci:set('passwall2','rulenode','default_node','wrong') end))
            assert(not pcall(function() api.sys.call('nft flush ruleset') end))
            assert(api.get_app_version('xray')=='26.10.10')
            return 'CONFIG'
          end} end
          print=function(s) output=s end
        ''')
        self.lua.execute((ROOT/'root/usr/share/pingwatch-manager/generate.lua').read_text())
        self.lua.execute("assert(output=='SAFE_OUTPUT' and config.outbounds[1].streamSettings.sockopt.mark==255)")

    def test_package_contents(self):
        import subprocess, tarfile, io
        subprocess.run([sys.executable,str(ROOT/'build.py')],check=True,capture_output=True)
        ipk=ROOT.parent/'dist/luci-app-pingwatch-manager_0.1.0-3_all.ipk'
        with tarfile.open(ipk,'r:gz') as outer:
            with tarfile.open(fileobj=io.BytesIO(outer.extractfile('./data.tar.gz').read()),mode='r:gz') as data:
                names=data.getnames()
                self.assertFalse(any('etc/config/' in n for n in names))
                self.assertEqual(data.getmember('./usr/sbin/pingwatch-manager-worker').mode,0o755)
                self.assertIn('./www/luci-static/resources/view/pingwatch/manager.js',names)
                self.assertTrue(data.getmember('./usr/share/pingwatch-manager').isdir())
                # Emulate opkg: unlike tarfile.extractall(), file creation does
                # not create missing parent directories implicitly.
                created={'.'}
                for member in data.getmembers():
                    parent=Path(member.name).parent.as_posix()
                    self.assertIn(parent,created,member.name)
                    if member.isdir(): created.add(Path(member.name).as_posix())

if __name__ == '__main__': unittest.main(verbosity=2)

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
          function cursor:get(config,id,key) for _,s in ipairs(sections) do if s['.name']==id then return key and s[key] or s['.type'] end end end
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

    def test_plan_scope_and_freshness(self):
        self.lua.execute('''
          sections[#sections+1]={['.name']='@global[0]',['.type']='global',node='rulenode'}
          sections[1].default_node='old'
          local report={mode='observe_only',complete=true,running=false,finished_at=1000,snapshot_current=true,
            rows={{id='node1',state='healthy',latency_ms=100}}}
          local plan=policy.plan(report,cursor,1100)
          assert(plan.state=='awaiting_approval' and plan.config=='passwall2' and plan.section=='rulenode')
          assert(plan.option=='default_node' and plan.expected=='old' and plan.node=='node1' and plan.applied==false)
          assert(sections[1].default_node=='old' and sections[1].Iran=='_direct')
          assert(policy.plan(report,cursor,1301).reason=='results_stale')
          assert(policy.plan(report,cursor,999).reason=='results_stale')
          report.running=true; assert(policy.plan(report,cursor,1100).state=='blocked'); report.running=false
          report.mode='config_check_only'; assert(policy.plan(report,cursor,1100).state=='blocked'); report.mode='observe_only'
          report.snapshot_current=false; assert(policy.plan(report,cursor,1100).state=='blocked'); report.snapshot_current=true
          sections[1].Devices='node1'; assert(policy.plan(report,cursor,1100).state=='blocked'); sections[1].Devices='_direct'
          sections[#sections].node='other'; assert(policy.plan(report,cursor,1100).reason=='active_node_is_not_rulenode')
          sections[#sections].node='rulenode'; table.remove(sections,2)
          assert(policy.plan(report,cursor,1100).reason=='candidate_missing')
        ''')

    def test_plan_avoids_small_changes_and_unverified_direct(self):
        self.lua.execute('''
          sections[#sections+1]={['.name']='@global[0]',['.type']='global',node='rulenode'}
          sections[1].default_node='old'
          local report={mode='observe_only',complete=true,finished_at=1000,snapshot_current=true,
            rows={{id='node1',state='healthy',latency_ms=900},{id='old',state='healthy',latency_ms=1000}}}
          assert(policy.plan(report,cursor,1000).reason=='gain_too_small')
          report.rows[1].latency_ms=500; assert(policy.plan(report,cursor,1000).reason=='faster_candidate')
          sections[1].default_node='node1'; assert(policy.plan(report,cursor,1000).reason=='current_is_best')
          report.rows={{id='node1',state='unhealthy'}}; report.direct={state='healthy'}
          assert(policy.plan(report,cursor,1000).reason=='direct_unverified')
        ''')

    def test_worker_mock_end_to_end(self,check_only=False,invalid=False):
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
          package.preload['luci.jsonc']=function() return {parse=function() return {outbounds={{protocol='vless'}}} end,
            stringify=function(s) published[#published+1]=s; return 'REDACTED' end} end
          package.preload['luci.model.uci']=function() return {cursor=function() return cursor end} end
          package.preload['luci.sys']=function() return {call=function(cmd)
            calls[#calls+1]=cmd
            if invalid and cmd:find('run -test',1,true) then
              files['/tmp/pingwatch-manager/work/core.err']='REALITY invalid public key SECRET_VALUE'; return 1
            end
            if cmd:find('curl',1,true) then files['/tmp/pingwatch-manager/work/probe.txt']='204:0.120' end
            return 0
          end} end
          arg={}
          dofile=function(p) if p:find('diagnostics',1,true) then return core_diag end; return policy end
        ''')
        self.lua.globals().core_diag=self.lua.execute((ROOT/'root/usr/share/pingwatch-manager/diagnostics.lua').read_text())
        self.lua.globals().invalid=invalid
        if check_only:
            self.lua.execute("arg={'--check-configs'}; files['/tmp/pingwatch-manager/results.json']='PREVIOUS_RESULTS'")
        self.lua.execute(code)
        self.lua.execute('''
          local s=published[#published]; assert(s.complete and not s.running and not s.route_changed)
          if invalid then
            assert(s.rows[1].state=='error' and s.rows[1].diagnostic.code=='reality_key_invalid')
            assert(s.rows[1].diagnostic.exit_code==1 and s.recommendation.node==nil)
            assert(files['/tmp/pingwatch-manager/work/core.err']==nil and #killed==0)
          elseif arg[1]=='--check-configs' then
            assert(s.rows[1].state=='config_valid' and s.rows[1].latency_ms==nil)
            assert(s.recommendation.node==nil and s.mode=='config_check_only')
            assert(files['/tmp/pingwatch-manager/results.json']=='PREVIOUS_RESULTS')
            assert(#killed==0)
            for _,cmd in ipairs(calls) do assert(not cmd:find('curl',1,true)) end
          else
            assert(s.rows[1].state=='healthy' and s.rows[1].latency_ms==120)
            assert(s.recommendation.node=='node1')
            assert(#killed==1 and killed[1]==123)
          end
          assert(files['/etc/config/passwall2']=='SECRET_CONFIG')
          assert(files['/tmp/pingwatch-manager/work/config/passwall2']==nil)
          assert(files['/tmp/pingwatch-manager/work/core.json']==nil)
          assert(not directories['/tmp/pingwatch-manager/lock'])
          for _,cmd in ipairs(calls) do assert(not cmd:find('uci set',1,true) and not cmd:find('restart',1,true)) end
        ''')

    def test_config_only_preserves_health_results(self):
        self.test_worker_mock_end_to_end(check_only=True)

    def test_core_error_is_classified_and_private_log_removed(self):
        self.test_worker_mock_end_to_end(check_only=True,invalid=True)

    def test_fixed_diagnostic_labels_and_shape(self):
        self.lua.globals().diag=self.lua.execute((ROOT/'root/usr/share/pingwatch-manager/diagnostics.lua').read_text())
        self.lua.execute('''
          assert(diag.classify('XHTTP mode invalid SECRET_UUID',1)=='xhttp_mode_invalid')
          assert(diag.classify('REALITY invalid public key SECRET_URL',1)=='reality_key_invalid')
          assert(diag.classify('SECRET_VALUE SECRET_LINK',1)=='unclassified_core_error')
          assert(diag.classify('SECRET_UUID',124)=='validation_timeout')
          local shape=diag.shape({outbounds={{protocol='vless',settings={uuid='SECRET'},streamSettings={network='xhttp',security='reality'}},
            {protocol='SECRET_URL',streamSettings={network='SECRET_URL',security='SECRET_UUID'}}}},'Xray')
          assert(shape[1].transport=='xhttp' and shape[1].security=='reality' and shape[1].settings==nil)
          assert(shape[2].protocol=='other' and shape[2].transport=='unspecified' and shape[2].security=='unspecified')
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
            local cache_file='cache_'..v.flag..'.txt'
            assert(cache_file=='cache_pingwatch_test.txt' and v.no_run==true)
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

    def test_diagnostic_never_prints_error_body(self):
        self.lua.execute('''
          arg={'/tmp/pingwatch-manager/work/config','node1','49000'}
          package.preload['luci.model.uci']=function() error('/private/util_xray.lua:123: SECRET_UUID SECRET_URL') end
          io.stderr={write=function(_,s) diagnostic=s end}
          os.exit=function(code) exit_code=code end
        ''')
        self.lua.execute((ROOT/'root/usr/share/pingwatch-manager/generate.lua').read_text())
        self.lua.execute("assert(exit_code==1 and diagnostic:find('PWDIAG:snapshot:',1,true) and not diagnostic:find('SECRET',1,true))")

    def test_package_contents(self):
        import subprocess, tarfile, io
        subprocess.run([sys.executable,str(ROOT/'build.py')],check=True,capture_output=True)
        ipk=ROOT.parent/'dist/luci-app-pingwatch-manager_0.2.0-1_all.ipk'
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

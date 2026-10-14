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
          report.stability={ready=true,rows=report.rows}
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
          report.stability={ready=true,rows=report.rows}
          assert(policy.plan(report,cursor,1000).reason=='gain_too_small')
          report.rows[1].latency_ms=500; assert(policy.plan(report,cursor,1000).reason=='faster_candidate')
          sections[1].default_node='node1'; assert(policy.plan(report,cursor,1000).reason=='current_is_best')
          report.rows={{id='node1',state='unhealthy'}}; report.direct={state='healthy'}
          report.stability.rows=report.rows
          assert(policy.plan(report,cursor,1000).reason=='direct_unverified')
        ''')

    def test_worker_mock_end_to_end(self,check_only=False,invalid=False,direct_only=False,direct_success=False,route_changed=False,target=False):
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
          dofile=function(p)
            if p:find('diagnostics',1,true) then return core_diag end
            if p:find('/direct.lua',1,true) then return direct_module end
            if p:find('/dns.lua',1,true) then return dns_module end
            if p:find('/stability.lua',1,true) then return stability_module end
            return policy
          end
        ''')
        self.lua.globals().core_diag=self.lua.execute((ROOT/'root/usr/share/pingwatch-manager/diagnostics.lua').read_text())
        self.lua.globals().direct_module=self.lua.execute((ROOT/'root/usr/share/pingwatch-manager/direct.lua').read_text())
        self.lua.globals().dns_module=self.lua.execute((ROOT/'root/usr/share/pingwatch-manager/dns.lua').read_text())
        self.lua.globals().stability_module=self.lua.execute((ROOT/'root/usr/share/pingwatch-manager/stability.lua').read_text())
        self.lua.globals().invalid=invalid
        if check_only:
            self.lua.execute("arg={'--check-configs'}; files['/tmp/pingwatch-manager/results.json']='PREVIOUS_RESULTS'")
        if direct_only:
            self.lua.execute("arg={'--check-direct'}; files['/tmp/pingwatch-manager/results.json']='PREVIOUS_RESULTS'")
        if target:
            self.lua.execute("arg={'--check-node','node1'}; files['/tmp/pingwatch-manager/results.json']='PREVIOUS_RESULTS'; sections[#sections+1]={['.name']='node2',['.type']='nodes',type='Xray',protocol='vless'}")
        self.lua.globals().direct_success=direct_success
        self.lua.globals().route_changed=route_changed
        if direct_success:
            self.lua.execute('''
              nft_payload={nftables={
                {chain={family='inet',table='passwall2',name='out',hook='output'}},
                {rule={family='inet',table='passwall2',chain='out',expr={
                  {match={op='==',left={meta={key='skgid'}},right=9912}},{['return']=true}}}}
              }}
              local get=cursor.get
              function cursor:get(config,id,key) if config=='network' then return 'dhcp' end; return get(self,config,id,key) end
              local j=require('luci.jsonc'); local parse=j.parse
              j.parse=function(raw) if raw=='NFT' then return nft_payload elseif raw=='WAN' then return {up=true,l3_device='eth0',['dns-server']={'9.9.9.9'}} end; return parse(raw) end
              local routes=0
              require('luci.sys').exec=function(cmd)
                if cmd:find('nft -s',1,true) then return 'NFT' end
                if cmd:find('ubus',1,true) then return 'WAN' end
                if cmd:find('route get',1,true) then routes=routes+1
                  return '1.1.1.1 via 10.0.0.1 dev eth0 src '..(route_changed and routes>1 and '10.0.0.3' or '10.0.0.2') end
                return ''
              end
              local nx=require('nixio')
              nx.fork=function()
                files['/tmp/pingwatch-manager/work/dns.txt']='Server: 9.9.9.9\\nAddress: 9.9.9.9#53\\nName: target\\nAddress: 142.250.1.1'
                files['/tmp/pingwatch-manager/work/probe.txt']='204:0.120:0.010:0.020:0.090'; return 123 end
              nx.waitpid=function() return 123,'exited',0 end
            ''')
        self.lua.execute(code)
        self.lua.execute('''
          local s=published[#published]; assert(s.complete and not s.running and not s.route_changed)
          if arg[1]=='--check-node' then
            assert(s.mode=='candidate_check_only' and #s.rows==1 and s.rows[1].id=='node1' and s.rows[1].state=='healthy')
            assert(s.plan==nil and s.stability==nil and files['/tmp/pingwatch-manager/results.json']=='PREVIOUS_RESULTS')
            assert(files['/tmp/pingwatch-manager/history.json']==nil)
          elseif arg[1]=='--check-direct' then
            assert(s.mode=='direct_check_only' and #s.rows==0 and s.plan==nil and s.stability==nil)
            assert(s.recommendation.node==nil)
            if direct_success and not route_changed then
              assert(s.direct.state=='healthy' and s.direct.path_verified==true)
              assert(s.direct.probes[1].dns_resolved and s.direct.probes[1].dns_source=='wan' and s.direct.probes[1].failure=='none')
            elseif route_changed then
              assert(s.direct.state=='unverified' and s.direct.reason=='wan_route_changed')
            else assert(s.direct.state=='unverified') end
            assert(files['/tmp/pingwatch-manager/results.json']=='PREVIOUS_RESULTS')
            assert(files['/tmp/pingwatch-manager/history.json']==nil and #killed==0)
            for _,cmd in ipairs(calls) do assert(not cmd:find('generate.lua',1,true)) end
          elseif invalid then
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

    def test_direct_only_preserves_health_and_history(self):
        self.test_worker_mock_end_to_end(direct_only=True)

    def test_candidate_retest_isolated_from_main_results(self):
        self.test_worker_mock_end_to_end(target=True)

    def test_wan_dns_parser_does_not_use_server_address_as_answer(self):
        self.lua.globals().dns=self.lua.execute((ROOT/'root/usr/share/pingwatch-manager/dns.lua').read_text())
        self.lua.execute('''
          assert(#dns.answers('Server: 9.9.9.9\\nAddress: 9.9.9.9#53\\nNXDOMAIN')==0)
          local a=dns.answers('Server: 9.9.9.9\\nAddress: 9.9.9.9#53\\nName: example\\nAddress 1: 142.250.1.1\\nAddress 2: 2001:db8::1')
          assert(#a==1 and a[1]=='142.250.1.1')
          assert(not dns.ipv4('127.0.0.1') and not dns.ipv4('999.1.1.1') and not dns.ipv4('1.1.1.1;bad'))
          local s=dns.servers({['dns-server']={'9.9.9.9','9.9.9.9','127.0.0.1','1.1.1.1'}})
          assert(#s==2)
        ''')

    def test_direct_only_success_with_verified_evidence(self):
        self.test_worker_mock_end_to_end(direct_only=True,direct_success=True)

    def test_direct_route_change_prevents_verification(self):
        self.test_worker_mock_end_to_end(direct_only=True,direct_success=True,route_changed=True)

    def test_direct_firewall_proof_fails_closed(self):
        self.lua.globals().direct=self.lua.execute((ROOT/'root/usr/share/pingwatch-manager/direct.lua').read_text())
        self.lua.execute('''
          local function chain(name) return {chain={family='inet',table='passwall2',name=name,hook='output'}} end
          local function rule(name,expr) return {rule={family='inet',table='passwall2',chain=name,expr=expr}} end
          local bypass={{match={op='==',left={meta={key='skgid'}},right=9912}},{counter={}},{['return']=true}}
          local rules={nftables={chain('nat_output'),rule('nat_output',bypass),rule('nat_output',{{redirect={port=1234}}})}}
          assert(direct.firewall(rules))
          bypass[1].match.right=0; assert(not direct.firewall(rules)); bypass[1].match.right=9912
          rules.nftables[#rules.nftables+1]={chain={family='ip',table='custom',name='out',hook='output'}}
          rules.nftables[#rules.nftables+1]={rule={family='ip',table='custom',chain='out',expr={{dnat={addr='SECRET_IP'}}}}}
          assert(not direct.firewall(rules))
          assert(not direct.firewall({nftables={}}))
          assert(direct.wan({up=true,l3_device='pppoe-wan'},'pppoe')=='pppoe-wan')
          assert(direct.wan({up=true,l3_device='wg0'},'wireguard')==nil)
          assert(direct.wan({up=false,l3_device='eth0'},'dhcp')==nil)
          assert(direct.wan({up=true,l3_device='eth0;SECRET'},'dhcp')==nil)
        ''')

    def test_three_round_stability_and_context_reset(self):
        self.lua.globals().stable=self.lua.execute((ROOT/'root/usr/share/pingwatch-manager/stability.lua').read_text())
        self.lua.execute('''
          local context=string.rep('a',64)
          local history,summary
          local report={complete=true,snapshot_current=true,direct={state='healthy',path_verified=true},rows={{id='node1',state='healthy',latency_ms=100}}}
          for i=1,3 do
            report.finished_at=1000+i*60; report.rows[1].latency_ms=({100,900,200})[i]
            history,summary=stable.update(history,report,context)
            assert(summary.ready==(i==3) and summary.rounds==i)
          end
          assert(summary.rows[1].latency_ms==200 and summary.direct_verified)
          history,summary=stable.update(history,report,context); assert(summary.rounds==3)
          report.finished_at=1250; report.rows[1].state='unhealthy'
          history,summary=stable.update(history,report,context); assert(summary.rows[1].state=='unstable')
          history,summary=stable.update(history,report,string.rep('b',64)); assert(not summary.ready and summary.rounds==1)
          report.finished_at=3000; history,summary=stable.update(history,report,string.rep('b',64)); assert(summary.rounds==1)
          history,summary=stable.update(history,report,nil); assert(not summary.ready)
        ''')

    def test_direct_proof_ignores_unrelated_state_but_detects_output_changes(self):
        self.lua.globals().direct=self.lua.execute((ROOT/'root/usr/share/pingwatch-manager/direct.lua').read_text())
        self.lua.execute('''
          local chain={chain={family='inet',table='passwall2',name='out',hook='output',prio=-1,policy='accept'}}
          local bypass={rule={family='inet',table='passwall2',chain='out',expr={
            {match={op='==',left={meta={key='skgid'}},right=9912}},{counter={packets=1}},{['return']={_null=true}}}}}
          local behind={rule={family='inet',table='passwall2',chain='out',expr={{redirect={port=1234}}}}}
          local data={nftables={chain,bypass,behind,{set={family='inet',table='passwall2',name='dynamic',elem={'SECRET_IP'}}}}}
          local ok,_,proof=direct.firewall(data); assert(ok)
          bypass.rule.handle=999; bypass.rule.expr[2].counter.packets=99
          data.nftables[4].set.elem={'OTHER_IP'}; behind.rule.expr[1].redirect.port=9000
          local ok2,_,proof2=direct.firewall(data); assert(ok2 and proof==proof2)
          chain.chain.prio=-2
          local _,_,changed=direct.firewall(data); assert(changed~=proof)
          chain.chain.prio=-1; bypass.rule.expr[1].match.right=1234; assert(not direct.firewall(data))
          local a=direct.route('1.1.1.1 via 10.0.0.1 dev eth0 src 10.0.0.2 uid 0\\n cache expires 10sec','eth0')
          local b=direct.route('1.1.1.1 via 10.0.0.1 dev eth0 src 10.0.0.2 uid 0\\n cache expires 9sec','eth0')
          assert(a==b and a~=direct.route('1.1.1.1 via 10.0.0.3 dev eth0 src 10.0.0.2','eth0'))
          assert(direct.route('1.1.1.1 dev wg0','eth0')==nil)
        ''')

    def test_nft_null_verdicts_preserved_without_rewriting_strings(self):
        import json
        direct=self.lua.execute((ROOT/'root/usr/share/pingwatch-manager/direct.lua').read_text())
        raw=json.dumps({'nftables':[
            {'chain':{'family':'inet','table':'passwall2','name':'nat_output','hook':'output'}},
            {'rule':{'family':'inet','table':'passwall2','chain':'nat_output','expr':[
                {'match':{'op':'==','left':{'meta':{'key':'skgid'}},'right':9912}},
                {'counter':None},{'return':None}], 'comment':'literal "return":null and escaped \\"null"'}},
            {'rule':{'family':'inet','table':'passwall2','chain':'nat_output','expr':[{'redirect':{'port':1234}}]}}
        ]})
        parse=lambda s:self.lua.table_from(json.loads(s),recursive=True)
        decoded=direct.decode(raw,parse)
        result=direct.firewall(decoded)
        self.assertTrue(result[0] if isinstance(result,tuple) else result)
        self.assertEqual(decoded['nftables'][2]['rule']['comment'],json.loads(raw)['nftables'][1]['rule']['comment'])
        self.assertTrue(decoded['nftables'][2]['rule']['expr'][3]['return']['_null'])

    def test_only_safe_inline_conntrack_verdict_maps_allowed(self):
        self.lua.globals().direct=self.lua.execute((ROOT/'root/usr/share/pingwatch-manager/direct.lua').read_text())
        self.lua.execute('''
          local map={key={ct={key='state'}},data={set={{'established',{accept={_null=true}}},{'related',{accept={_null=true}}}}}}
          local rules={nftables={
            {chain={family='inet',table='fw4',name='output',hook='output'}},
            {rule={family='inet',table='fw4',chain='output',expr={{vmap=map}}}},
            {chain={family='inet',table='passwall2',name='nat_output',hook='output'}},
            {rule={family='inet',table='passwall2',chain='nat_output',expr={
              {match={op='==',left={meta={key='skgid'}},right=9912}},{['return']={_null=true}}}}}
          }}
          assert(direct.firewall(rules))
          map.data.set[1][2]={jump={target='unsafe'}}; assert(not direct.firewall(rules))
          map.data='@dynamic_map'; assert(not direct.firewall(rules))
        ''')

    def test_direct_fallback_requires_stable_complete_failures(self):
        self.lua.execute('''
          sections[#sections+1]={['.name']='@global[0]',['.type']='global',node='rulenode'}
          sections[1].default_node='node1'
          local report={mode='observe_only',complete=true,snapshot_current=true,finished_at=1000,rows={}}
          assert(policy.plan(report,cursor,1000).reason=='stability_pending')
          report.stability={ready=true,direct_verified=true,rows={{id='node1',state='unhealthy'}}}
          local p=policy.plan(report,cursor,1000); assert(p.node=='_direct' and p.reason=='direct_fallback' and p.applied==false)
          report.stability.direct_verified=false; assert(policy.plan(report,cursor,1000).node==nil)
          report.stability.direct_verified=true; report.stability.rows[1]={id='node1',state='error',reason='adapter_failed'}
          assert(policy.plan(report,cursor,1000).node==nil)
          report.stability.rows[1]={id='node1',state='error',reason='core_config_invalid',diagnostic={exit_code=23}}
          assert(policy.plan(report,cursor,1000).node=='_direct')
        ''')

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
                if code.startswith('#!/bin/sh'): continue
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
        ipk=ROOT.parent/'dist/luci-app-pingwatch_1.6.0-1_all.ipk'
        with tarfile.open(ipk,'r:gz') as outer:
            with tarfile.open(fileobj=io.BytesIO(outer.extractfile('./control.tar.gz').read()),mode='r:gz') as control:
                self.assertIn(b'/etc/config/pingwatch\n',control.extractfile('./conffiles').read())
                self.assertNotIn(b'pingwatch-manager enable',control.extractfile('./postinst').read())
            with tarfile.open(fileobj=io.BytesIO(outer.extractfile('./data.tar.gz').read()),mode='r:gz') as data:
                names=data.getnames()
                self.assertNotIn('./etc/config/passwall2',names)
                self.assertEqual([n for n in names if n.endswith('.json') and '/menu.d/' in n],['./usr/share/luci/menu.d/luci-app-pingwatch.json'])
                self.assertIn(b"option enabled '0'",data.extractfile('./etc/config/pingwatch_manager').read())
                main=data.extractfile('./www/luci-static/resources/view/pingwatch/main.js').read()
                self.assertIn(b'managerView.render()',main)
                self.assertIn(b"'manager', false",main)
                self.assertIn('./usr/sbin/pingwatch-send-sms',names)
                import json
                acl=json.loads(data.extractfile('./usr/share/rpcd/acl.d/luci-app-pingwatch.json').read())['luci-app-pingwatch']
                self.assertNotIn('passwall2',acl['write']['uci'])
                self.assertIn('/usr/sbin/pingwatch-manager-control disable',acl['write']['file'])
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

    def transaction_fixture(self):
        self.lua.globals().transaction=self.lua.execute((ROOT/'root/usr/share/pingwatch-manager/transaction.lua').read_text())
        self.lua.execute('''
          state='OLD'; enabled=true; writes=0; restarts=0; rollback_health=true; active_health=true
          e={enabled=function() return enabled end, read=function() return state end,
            proposal=function() return {state='awaiting_approval',expected='old',node='new'} end,
            retest=function() return true end,prepare=function(before,id) return 'NEW' end,
            only_default=function() return true end,backup=function(before) backup=before end,
            replace=function(before,after) if state~=before then return false end; state=after; writes=writes+1; return true end,
            restart=function() restarts=restarts+1; return true end,
            active=function() return restarts==1 and active_health or restarts>1 and rollback_health end,
            disable=function() enabled=false end,
            rollback=function(old,new,original) if state~='NEW' then return false end; state=original; return true end}
        ''')

    def test_transaction_success_and_exact_scope(self):
        self.transaction_fixture()
        self.lua.execute("local r=transaction.run(e); assert(r.state=='applied_verified' and writes==1 and backup=='OLD' and restarts==1)")

    def test_transaction_blocks_disabled_and_failed_retest(self):
        self.transaction_fixture()
        self.lua.execute('''
          enabled=false; assert(transaction.run(e).reason=='disabled' and writes==0)
          enabled=true; e.retest=function() return false end
          assert(transaction.run(e).reason=='candidate_retest_failed' and writes==0)
          e.retest=function() enabled=false; return true end
          assert(transaction.run(e).reason=='disabled' and writes==0)
        ''')

    def test_transaction_config_conflict_and_scope_change(self):
        self.transaction_fixture()
        self.lua.execute('''
          e.retest=function() state='USER_EDIT'; return true end
          assert(transaction.run(e).reason=='config_changed' and writes==0 and state=='USER_EDIT')
          state='OLD'; e.retest=function() return true end; e.only_default=function() return false end
          assert(transaction.run(e).reason=='scope_verification_failed' and writes==0)
        ''')

    def test_transaction_rollback_after_active_path_failure(self):
        self.transaction_fixture()
        self.lua.execute("active_health=false; local r=transaction.run(e); assert(r.state=='rolled_back_verified' and state=='OLD' and not enabled and restarts==2)")

    def test_transaction_off_switch_checked_immediately_before_write(self):
        self.transaction_fixture()
        self.lua.execute("e.backup=function() enabled=false end; assert(transaction.run(e).reason=='disabled' and writes==0 and state=='OLD')")

    def test_transaction_reports_failed_rollback_health(self):
        self.transaction_fixture()
        self.lua.execute("active_health=false; rollback_health=false; local r=transaction.run(e); assert(r.state=='rolled_back_unverified' and state=='OLD' and not enabled)")

    def test_transaction_does_not_overwrite_concurrent_default_change(self):
        self.transaction_fixture()
        self.lua.execute('''
          e.active=function() state='USER_EDIT'; return false end
          local r=transaction.run(e)
          assert(r.state=='rollback_conflict' and state=='USER_EDIT' and r.requires_attention and not enabled)
        ''')

if __name__ == '__main__': unittest.main(verbosity=2)

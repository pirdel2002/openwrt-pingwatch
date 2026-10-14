const vm=require('node:vm'), fs=require('node:fs'), assert=require('node:assert');
let view, poll, empty=false, stale=false;
function E(tag,attrs,children){return {tag,attrs:attrs||{},children:children||[],replaceChildren(...r){this.children=r;}};}
vm.runInNewContext('(function(){'+fs.readFileSync('manager/root/www/luci-static/resources/view/pingwatch/manager.js','utf8')+'})()',{
  E, view:{extend(v){view=v;}},poll:{add(f){poll=f;}},fs:{exec(){return Promise.resolve({stdout:JSON.stringify(empty?{rows:{},subscriptions:{}}:{complete:true,guard_ok:true,
    finished_at:Date.now()/1000-(stale?301:0),plan:{state:'awaiting_approval',reason:'healthy_candidate',expected:'old',node:'n1'},
    subscriptions:[{id:'s1'}],rows:[{id:'n1',core:'Xray',protocol:'vless',state:'healthy',latency_ms:120,probes:[{ok:true},{ok:false,failure:'timeout'}]}]})});}},
});
view.render().then(async root=>{
  assert.equal(root.attrs.dir,'rtl'); assert.equal(view.handleSaveApply,null);
  assert(root.children[2].textContent.includes('تأیید نشده'));
  assert.equal(root.children[3].children.length,2); assert(poll);
  assert(root.children[4].textContent.includes('rulenode.default_node'));
  assert(root.children[3].children[1].children[6].children.includes('timeout'));
  stale=true; await poll(); assert(root.children[4].textContent.includes('منقضی'));
  empty=true; await poll(); assert.equal(root.children[3].children.length,1);
  console.log('LuCI view render/poll/read-only checks passed');
}).catch(e=>{console.error(e);process.exit(1);});

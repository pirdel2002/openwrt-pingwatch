const vm=require('node:vm'), fs=require('node:fs'), assert=require('node:assert');
let view, poll, empty=false, stale=false;
let enabled=false, actions=[];
function E(tag,attrs,children){return {tag,attrs:attrs||{},children:children||[],listeners:{},addEventListener(name,f){this.listeners[name]=f;},replaceChildren(...r){this.children=r;}};}
vm.runInNewContext('(function(){'+fs.readFileSync('manager/root/www/luci-static/resources/view/pingwatch/manager.js','utf8')+'})()',{
  E, view:{extend(v){view=v;}},poll:{add(f){poll=f;}},fs:{exec(path,args){
    if(path.endsWith('pingwatch-manager-control')){
      if(args){actions.push(args[0]);enabled=args[0]==='enable';}
      return Promise.resolve({code:0,stdout:JSON.stringify({enabled})});
    }
    return Promise.resolve({stdout:JSON.stringify(empty?{rows:{},subscriptions:{}}:{complete:true,guard_ok:true,
    recommendation:{node:'n1'},finished_at:Date.now()/1000-(stale?301:0),plan:{state:'awaiting_approval',reason:'healthy_candidate',expected:'old',node:'n1'},
    subscriptions:[{id:'s1'}],rows:[{id:'n1',remark:'نام آزمایشی',core:'Xray',protocol:'vless',state:'healthy',latency_ms:120,probes:[{ok:true},{ok:false,failure:'timeout'}]}]})});}},
});
view.render().then(async root=>{
  assert.equal(root.attrs.dir,'rtl'); assert.equal(view.handleSaveApply,null);
  var toggle=root.children[1].children[1].children[0];
  assert.equal(toggle.checked,false);
  toggle.checked=true; toggle.listeners.change(); await new Promise(resolve=>setImmediate(resolve));
  assert.equal(enabled,true); assert.equal(toggle.checked,true);
  toggle.checked=false; toggle.listeners.change(); await new Promise(resolve=>setImmediate(resolve));
  assert.equal(enabled,false); assert.deepEqual(actions,['enable','disable']);
  assert(JSON.stringify(root.children[2]).includes('تأیید نشده'));
  assert(JSON.stringify(root.children[2]).includes('نام آزمایشی'));
  assert.equal(root.children[3].children[0].children.length,2); assert(poll);
  assert(root.children[4].textContent.includes('نام آزمایشی'));
  assert(JSON.stringify(root.children[3]).includes('پایان مهلت'));
  assert(JSON.stringify(root.children[3]).includes('نام آزمایشی'));
  assert(!JSON.stringify(root.children[3]).includes('n1'));
  stale=true; await poll(); assert(root.children[4].textContent.includes('منقضی'));
  empty=true; await poll(); assert.equal(root.children[3].children[0].children.length,2);
  console.log('LuCI view render/poll/read-only checks passed');
}).catch(e=>{console.error(e);process.exit(1);});

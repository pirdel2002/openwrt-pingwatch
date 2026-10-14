'use strict';
'require view';
'require fs';
'require poll';
return view.extend({
  handleSave: null, handleSaveApply: null, handleReset: null,
  render: function() {
    var summary=E('p'), table=E('table', {'class':'table'}), plan=E('p');
    var toggle=E('input',{type:'checkbox',disabled:true});
    var controlStatus=E('span',{},'در حال خواندن وضعیت…');
    toggle.addEventListener('change',function(){
      toggle.disabled=true;
      fs.exec('/usr/sbin/pingwatch-manager-control',[toggle.checked?'enable':'disable']).then(function(r){
        if(r.code) throw new Error('control_failed');
        var s=JSON.parse(r.stdout||'{}'); toggle.checked=s.enabled===true;
        controlStatus.textContent=s.enabled?'روشن؛ پس از تأیید پایداری، default شانت خودکار مدیریت می‌شود.':'خاموش؛ تغییر خودکار مسیر متوقف است.';
      }).catch(function(){toggle.checked=!toggle.checked;controlStatus.textContent='تغییر وضعیت ناموفق بود.';})
        .finally(function(){toggle.disabled=false;});
    });
    var root=E('div', {dir:'rtl'}, [E('h2',{},'مدیریت Passwall'),
      E('div',{'class':'cbi-section'},[
        E('p',{},'این کلید فقط مدیریت خودکار Passwall را کنترل می‌کند. خاموش‌کردن، مسیر فعلی را حفظ می‌کند؛ SMS و LED تنظیمات قبلی خود را دارند.'),
        E('label',{'class':'cbi-value'},[toggle,' مدیریت خودکار Passwall — ',controlStatus])]),summary,table,plan]);
    function refresh() {
      fs.exec('/usr/sbin/pingwatch-manager-control').then(function(r){
        var s=JSON.parse(r.stdout||'{}'); toggle.checked=s.enabled===true; toggle.disabled=false;
        var states={applied_verified:'تغییر اعمال و مسیر فعال تأیید شد',rolled_back_verified:'بازگشت به مقدار قبلی تأیید شد',
          rolled_back_unverified:'تنظیم قبلی بازگردانده شد؛ سلامت مسیر تأیید نشد',rollback_conflict:'بازگشت متوقف شد؛ بررسی دستی لازم است',
          apply_error:'خطای اعمال؛ مدیریت خاموش شد',blocked:'در انتظار شرایط لازم'};
        controlStatus.textContent=(s.enabled?'روشن؛ اعمال خودکار مجاز است.':'خاموش؛ تغییر خودکار مسیر متوقف است.')+
          (s.last_action?' | '+(states[s.last_action.state]||s.last_action.state)+(s.last_action.reason?' ('+s.last_action.reason+')':''):'');
      }).catch(function(){controlStatus.textContent='خواندن وضعیت مدیریت ناموفق بود.';});
      return fs.exec('/usr/sbin/pingwatch-manager-results').then(function(r) {
        var s=JSON.parse(r.stdout || '{}');
        var nodes=Array.isArray(s.rows)?s.rows:[];
        var subscriptions=Array.isArray(s.subscriptions)?s.subscriptions:[];
        var counts={healthy:0,unhealthy:0,error:0,unsupported:0};
        nodes.forEach(function(n){if(n.state in counts) counts[n.state]++;});
        summary.textContent='وضعیت: '+(s.error || (s.running?'در حال آزمون':s.complete?'پایان آزمون':'ناقص'))+
          ' | سلامت قوانین شانت: '+(s.guard_ok?'تأیید':'تأیید نشده')+
          ' | اتصال مستقیم: '+(s.direct && s.direct.path_verified && s.direct.state==='healthy'?'سالم؛ مسیر تأیید شده':
          s.direct && s.direct.path_verified && s.direct.state==='unhealthy'?'ناموفق در مسیر مستقیم':'تأیید نشده')+
          ' | اشتراک‌ها: '+subscriptions.length.toLocaleString('fa-IR')+
          (s.recommendation?' | پیشنهاد: '+(s.recommendation.node || s.recommendation.reason):'');
        summary.textContent+=' | سالم: '+counts.healthy.toLocaleString('fa-IR')+' | ناموفق: '+counts.unhealthy.toLocaleString('fa-IR')+
          ' | خطا: '+counts.error.toLocaleString('fa-IR');
        var reasons={tests_incomplete:'آزمون ناقص است',results_stale:'نتایج قدیمی شده‌اند',shunt_or_snapshot_changed:'تنظیمات شانت تغییر کرده‌اند',
          active_node_is_not_rulenode:'شانت rulenode مسیر فعال نیست',candidate_missing:'گزینه حذف شده است',current_is_best:'default فعلی بهترین گزینه است',
          gain_too_small:'بهبود کافی نیست؛ default فعلی حفظ می‌شود',healthy_candidate:'گزینهٔ سالم موجود است',faster_candidate:'گزینهٔ سریع‌تر موجود است',
          incomplete_tests:'برخی آزمون‌ها قطعی نیستند',direct_unverified:'اتصال مستقیم تأیید نشده است',
          stability_pending:'در انتظار سه نوبت پایدار',direct_fallback:'هیچ گزینهٔ سالمی در سه نوبت نیست؛ اتصال مستقیم تأیید شده است'};
        if(s.stability) summary.textContent+=' | نوبت‌های پایداری: '+s.stability.rounds.toLocaleString('fa-IR')+' / ۳';
        var age=s.finished_at?(Date.now()/1000-s.finished_at):null;
        plan.textContent=age!=null && (age>300 || age<0)?'پیشنهاد منقضی شده؛ آزمون را دوباره اجرا کنید.':s.plan?
          'برنامه: '+(reasons[s.plan.reason]||s.plan.reason)+(s.plan.state==='awaiting_approval'?
          ' | فقط rulenode.default_node: '+(s.plan.expected||'—')+' ← '+s.plan.node+' | هنوز اعمال نشده':''):'هنوز برنامه‌ای ثبت نشده است.';
        var rows=[E('tr',{},['شناسه','هسته','پروتکل','نتیجه','زمان (میلی‌ثانیه)','تشخیص خطا','دو آزمون اتصال'].map(function(t){return E('th',{},t);} ))];
        var labels={healthy:'سالم',unhealthy:'ناموفق',unsupported:'پشتیبانی نشده',error:'خطای آزمون'};
        nodes.forEach(function(n){rows.push(E('tr',{},[n.id,n.core,n.protocol,labels[n.state]||n.state,
          n.latency_ms==null?'—':n.latency_ms.toLocaleString('fa-IR'),
          n.diagnostic?(n.diagnostic.code||n.diagnostic.stage||n.reason):n.reason,
          (Array.isArray(n.probes)?n.probes:[]).map(function(p){return p.ok?'موفق':p.failure;}).join(' / ')].map(function(t){return E('td',{},String(t||'—'));})));});
        table.replaceChildren.apply(table,rows);
      }).catch(function(){summary.textContent='خواندن نتیجه ناموفق بود.';});
    }
    poll.add(refresh,5); return refresh().then(function(){return root;});
  }
});

'use strict';
'require view';
'require fs';
'require poll';
return view.extend({
  handleSave: null, handleSaveApply: null, handleReset: null,
  render: function() {
    var summary=E('div',{'class':'pwm-summary'}), table=E('table', {'class':'pwm-table'}), plan=E('div',{'class':'pwm-plan'});
    var toggle=E('input',{type:'checkbox',disabled:true});
    var controlStatus=E('span',{'class':'pwm-control-status'},'در حال خواندن وضعیت…');
    toggle.addEventListener('change',function(){
      toggle.disabled=true;
      fs.exec('/usr/sbin/pingwatch-manager-control',[toggle.checked?'enable':'disable']).then(function(r){
        if(r.code) throw new Error('control_failed');
        var s=JSON.parse(r.stdout||'{}'); toggle.checked=s.enabled===true;
        controlStatus.textContent=s.enabled?'روشن؛ پس از تأیید پایداری، default شانت خودکار مدیریت می‌شود.':'خاموش؛ تغییر خودکار مسیر متوقف است.';
      }).catch(function(){toggle.checked=!toggle.checked;controlStatus.textContent='تغییر وضعیت ناموفق بود.';})
        .finally(function(){toggle.disabled=false;});
    });
    var root=E('div', {dir:'rtl','class':'pwm'}, [E('h2',{},'مدیریت Passwall'),
      E('div',{'class':'pwm-control'},[
        E('p',{},'این کلید فقط مدیریت خودکار Passwall را کنترل می‌کند. خاموش‌کردن، مسیر فعلی را حفظ می‌کند؛ SMS و LED تنظیمات قبلی خود را دارند.'),
        E('label',{'class':'pwm-switch'},[toggle,' مدیریت خودکار Passwall — ',controlStatus])]),summary,E('div',{'class':'pwm-table-wrap'},[table]),plan,E('style',{},`
.pwm{font-family:Tahoma,Arial,sans-serif;font-size:13px;color:#243247;line-height:1.8;max-width:1400px;margin:auto}.pwm h2{font:700 24px Tahoma,Arial,sans-serif;margin:12px 0 18px}.pwm-control{background:#f3f7fc;border:1px solid #dbe5f0;border-radius:14px;padding:18px 22px;margin-bottom:18px}.pwm-control p{margin:0 0 14px;color:#64748b;font-size:12px}.pwm-switch{display:flex;align-items:center;gap:12px;flex-wrap:wrap;font-weight:bold}.pwm-switch input{appearance:none;-webkit-appearance:none;width:46px!important;height:26px!important;border:0!important;border-radius:20px;background:#94a3b8;position:relative;cursor:pointer;flex-shrink:0;margin:0!important;transition:background .2s}.pwm-switch input:before{content:'';position:absolute;width:20px;height:20px;left:3px;top:3px;border-radius:50%;background:white;box-shadow:0 1px 4px #0003;transition:transform .2s}.pwm-switch input:checked{background:#16836a}.pwm-switch input:checked:before{transform:translateX(20px)}.pwm-switch input:focus-visible{outline:3px solid #93c5fd}.pwm-switch input:disabled{opacity:.5;cursor:wait}.pwm-control-status{font-weight:normal;color:#52647a}.pwm-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:18px 0}.pwm-card{border:1px solid #e2e8f0;border-radius:12px;background:#fff;padding:14px 18px}.pwm-card small{display:block;color:#64748b;font-size:12px}.pwm-card strong{display:block;font-size:19px;margin-top:4px;color:#233f60}.pwm-card.good strong{color:#148368}.pwm-card.bad strong{color:#b45309}.pwm-table-wrap{overflow:auto;border:1px solid #e2e8f0;border-radius:12px;background:white}.pwm .pwm-table{border-collapse:collapse;width:100%;margin:0;font-size:12px;text-align:right}.pwm-table th{background:#edf3f9;color:#52647a;font-weight:bold;padding:12px 16px;white-space:nowrap;border:0}.pwm-table td{padding:11px 16px;border:0;border-bottom:1px solid #edf1f5;vertical-align:middle}.pwm-table tr:last-child td{border-bottom:0}.pwm-table tr:nth-child(even){background:#f8fafc}.pwm-table tr:hover{background:#eef6ff}.pwm-name{min-width:220px;max-width:360px;overflow-wrap:anywhere;font-weight:bold;unicode-bidi:plaintext}.pwm-ltr{direction:ltr;unicode-bidi:isolate;text-align:right;white-space:nowrap}.pwm-badge{display:inline-block;padding:2px 10px;border-radius:20px;background:#f1f5f9;color:#64748b;white-space:nowrap}.pwm-badge.healthy{background:#e4f5ed;color:#127455}.pwm-badge.unhealthy{background:#fff1e4;color:#a65516}.pwm-badge.error{background:#feecef;color:#ad344c}.pwm-plan{background:#edf5ff;border-right:3px solid #4c8ed9;border-radius:8px;padding:14px 18px;margin-top:16px;color:#35577c;white-space:pre-line}@media(max-width:800px){.pwm-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.pwm-switch{display:block}.pwm-switch input{vertical-align:middle;margin-left:10px!important}.pwm-control-status{display:block;margin-top:10px}.pwm-card strong{font-size:16px}.pwm-control{padding:14px}.pwm-table td,.pwm-table th{padding:10px}}
`)]);
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
        function name(id){if(id==='_direct')return 'اتصال مستقیم';var n=nodes.filter(function(n){return n.id===id;})[0];return n&&n.remark?n.remark:'کانفیگ بدون نام';}
        function card(label,value,kind){return E('div',{'class':'pwm-card '+(kind||'')},[E('small',{},label),E('strong',{},value)]);}
        summary.replaceChildren(
          card('وضعیت آزمون',s.running?'در حال بررسی…':s.complete?'تکمیل شده':'در انتظار آزمون'),
          card('کانفیگ‌های سالم',counts.healthy.toLocaleString('fa-IR')+' از '+nodes.length.toLocaleString('fa-IR'),'good'),
          card('ناموفق / خطای آزمون',counts.unhealthy.toLocaleString('fa-IR')+' / '+counts.error.toLocaleString('fa-IR'),'bad'),
          card('اشتراک‌ها',subscriptions.length.toLocaleString('fa-IR')),
          card('قوانین شانت',s.guard_ok?'محافظت شده':'تأیید نشده',s.guard_ok?'good':''),
          card('اتصال مستقیم',s.direct&&s.direct.path_verified?(s.direct.state==='healthy'?'سالم':'ناموفق'):'تأیید نشده'),
          card('پایداری آزمون',((s.stability&&s.stability.rounds)||0).toLocaleString('fa-IR')+' از ۳ نوبت'),
          card('پیشنهاد',s.recommendation&&s.recommendation.node?name(s.recommendation.node):'در انتظار نتیجه'));
        var reasons={tests_incomplete:'آزمون ناقص است',results_stale:'نتایج قدیمی شده‌اند',shunt_or_snapshot_changed:'تنظیمات شانت تغییر کرده‌اند',
          active_node_is_not_rulenode:'شانت rulenode مسیر فعال نیست',candidate_missing:'گزینه حذف شده است',current_is_best:'default فعلی بهترین گزینه است',
          gain_too_small:'بهبود کافی نیست؛ default فعلی حفظ می‌شود',healthy_candidate:'گزینهٔ سالم موجود است',faster_candidate:'گزینهٔ سریع‌تر موجود است',
          incomplete_tests:'برخی آزمون‌ها قطعی نیستند',direct_unverified:'اتصال مستقیم تأیید نشده است',
          stability_pending:'در انتظار سه نوبت پایدار',direct_fallback:'هیچ گزینهٔ سالمی در سه نوبت نیست؛ اتصال مستقیم تأیید شده است'};
        var age=s.finished_at?(Date.now()/1000-s.finished_at):null;
        plan.textContent=age!=null && (age>300 || age<0)?'پیشنهاد منقضی شده؛ آزمون را دوباره اجرا کنید.':s.plan?
          'برنامه: '+(reasons[s.plan.reason]||s.plan.reason)+(s.plan.state==='awaiting_approval'?
          '\nمسیر پیشنهادی: '+name(s.plan.node)+' | هنوز اعمال نشده':''):'هنوز برنامه‌ای ثبت نشده است.';
        var rows=[E('tr',{},['نام کانفیگ','هسته / پروتکل','وضعیت','زمان پاسخ','جزئیات آزمون'].map(function(t){return E('th',{},t);} ))];
        var labels={healthy:'سالم',unhealthy:'ناموفق',unsupported:'پشتیبانی نشده',error:'خطای آزمون'};
        var failures={tls_error:'خطای اتصال امن',timeout:'پایان مهلت',dns_timeout:'پاسخ‌ندادن DNS',none:'موفق',encryption_invalid:'رد تنظیمات توسط هسته',core_config_invalid:'تنظیمات ناسازگار',adapter_not_supported:'پشتیبانی نشده'};
        nodes.slice().sort(function(a,b){var rank={healthy:0,unhealthy:1,error:2,unsupported:3};return (rank[a.state]||0)-(rank[b.state]||0)||(a.latency_ms||0)-(b.latency_ms||0);}).forEach(function(n){
          var detail=(Array.isArray(n.probes)?n.probes:[]).map(function(p){return p.ok?'موفق':(failures[p.failure]||'ناموفق');}).join(' / ');
          if(!detail)detail=failures[(n.diagnostic&&n.diagnostic.code)||n.reason]||'—';
          rows.push(E('tr',{},[
            E('td',{'class':'pwm-name'},n.remark||'کانفیگ بدون نام'),
            E('td',{'class':'pwm-ltr'},(n.core||'—')+' / '+(n.protocol||'—')),
            E('td',{},[E('span',{'class':'pwm-badge '+n.state},labels[n.state]||'نامشخص')]),
            E('td',{},n.latency_ms==null?'—':n.latency_ms.toLocaleString('fa-IR')+' ms'),
            E('td',{},detail)]));
        });
        if(!nodes.length)rows.push(E('tr',{},[E('td',{colspan:5},'هنوز نتیجه‌ای ثبت نشده است؛ پس از اجرای آزمون، کانفیگ‌ها اینجا نمایش داده می‌شوند.')]));
        table.replaceChildren.apply(table,rows);
      }).catch(function(){summary.textContent='خواندن نتیجه ناموفق بود.';});
    }
    poll.add(refresh,5); return refresh().then(function(){return root;});
  }
});

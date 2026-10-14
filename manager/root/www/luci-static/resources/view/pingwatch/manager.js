'use strict';
'require view';
'require fs';
'require poll';
return view.extend({
  handleSave: null, handleSaveApply: null, handleReset: null,
  render: function() {
    var summary=E('p'), table=E('table', {'class':'table'});
    var root=E('div', {dir:'rtl'}, [E('h2',{},'نتایج آزمون PingWatch'),
      E('p',{},'فاز اول: فقط بررسی سلامت؛ مسیر فعال و قوانین شانت تغییر نمی‌کنند.'),summary,table]);
    function refresh() {
      return fs.exec('/usr/sbin/pingwatch-manager-results').then(function(r) {
        var s=JSON.parse(r.stdout || '{}');
        var nodes=Array.isArray(s.rows)?s.rows:[];
        var subscriptions=Array.isArray(s.subscriptions)?s.subscriptions:[];
        summary.textContent='وضعیت: '+(s.error || (s.running?'در حال آزمون':s.complete?'پایان آزمون':'ناقص'))+
          ' | سلامت قوانین شانت: '+(s.guard_ok?'تأیید':'تأیید نشده')+
          ' | اتصال مستقیم: تأیید نشده | اشتراک‌ها: '+subscriptions.length.toLocaleString('fa-IR')+
          (s.recommendation?' | پیشنهاد: '+(s.recommendation.node || s.recommendation.reason):'');
        var rows=[E('tr',{},['شناسه','هسته','پروتکل','نتیجه','زمان (میلی‌ثانیه)'].map(function(t){return E('th',{},t);} ))];
        var labels={healthy:'سالم',unhealthy:'ناموفق',unsupported:'پشتیبانی نشده',error:'خطای آزمون'};
        nodes.forEach(function(n){rows.push(E('tr',{},[n.id,n.core,n.protocol,labels[n.state]||n.state,
          n.latency_ms==null?'—':n.latency_ms.toLocaleString('fa-IR')].map(function(t){return E('td',{},String(t||'—'));})));});
        table.replaceChildren.apply(table,rows);
      }).catch(function(){summary.textContent='خواندن نتیجه ناموفق بود.';});
    }
    poll.add(refresh,5); return refresh().then(function(){return root;});
  }
});

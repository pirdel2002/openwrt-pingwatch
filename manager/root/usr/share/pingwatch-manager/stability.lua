local M={}
function M.update(history,report,context)
  local now=report.finished_at
  if not context or not context:match('^%x+$') or #context~=64 or not report.complete or not report.snapshot_current then
    return {rounds={}},{ready=false,rounds=0,required=3,reason='context_unverified'}
  end
  local rounds={}
  if history and history.context==context then
    for _,r in ipairs(history.rounds or {}) do
      if r.finished_at and now>=r.finished_at and now-r.finished_at<=900 then rounds[#rounds+1]=r end
    end
  end
  local last=rounds[#rounds]
  if not last or now-last.finished_at>=30 then
    local rows={}
    for _,r in ipairs(report.rows or {}) do
      rows[#rows+1]={id=r.id,state=r.state,latency_ms=r.latency_ms,reason=r.reason,diagnostic=r.diagnostic and {exit_code=r.diagnostic.exit_code}}
    end
    rounds[#rounds+1]={finished_at=now,rows=rows,direct_verified=report.direct and report.direct.state=='healthy' and report.direct.path_verified==true}
  end
  while #rounds>3 do table.remove(rounds,1) end
  local result={ready=#rounds==3,rounds=#rounds,required=3,rows={},direct_verified=#rounds==3}
  for _,r in ipairs(rounds) do if not r.direct_verified then result.direct_verified=false end end
  for _,current in ipairs(report.rows or {}) do
    local samples,allhealthy,allunhealthy,allinvalid={},true,true,true
    for _,round in ipairs(rounds) do
      local row
      for _,v in ipairs(round.rows) do if v.id==current.id then row=v; break end end
      if not row or row.state~='healthy' or type(row.latency_ms)~='number' then allhealthy=false else samples[#samples+1]=row.latency_ms end
      if not row or row.state~='unhealthy' then allunhealthy=false end
      if not row or row.reason~='core_config_invalid' or not row.diagnostic or row.diagnostic.exit_code~=23 then allinvalid=false end
    end
    local item={id=current.id,state='unstable'}
    if result.ready and allhealthy then table.sort(samples); item.state='healthy'; item.latency_ms=samples[2]
    elseif result.ready and allunhealthy then item.state='unhealthy'
    elseif result.ready and allinvalid then item.state='error'; item.reason='core_config_invalid'; item.diagnostic={exit_code=23} end
    result.rows[#result.rows+1]=item
  end
  return {context=context,rounds=rounds},result
end
return M

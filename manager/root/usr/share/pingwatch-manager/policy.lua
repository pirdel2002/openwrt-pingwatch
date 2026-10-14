local M = {}
function M.inventory(cursor)
  local nodes, subscriptions = {}, {}
  cursor:foreach('passwall2', 'subscribe_list', function(s)
    subscriptions[#subscriptions+1] = {id=s['.name']}
  end)
  cursor:foreach('passwall2', 'nodes', function(s)
    if type(s.protocol)=='string' and s.protocol:sub(1,1)~='_' then
      nodes[#nodes+1] = {id=s['.name'], core=s.type, protocol=s.protocol, remark=type(s.remarks)=='string' and s.remarks or nil, subscription=type(s.group)=='string' and s.group or nil}
    end
  end)
  table.sort(nodes, function(a,b) return a.id<b.id end)
  return nodes, subscriptions
end
function M.guard(cursor)
  if cursor:get('passwall2','rulenode','protocol') ~= '_shunt' then return false end
  for _, key in ipairs({'PrivateIP','Iran','Devices'}) do
    if cursor:get('passwall2','rulenode',key) ~= '_direct' then return false end
  end
  return true
end
function M.recommend(rows, guard, direct_verified)
  if not guard then return {state='blocked', reason='shunt_guard'} end
  local best, uncertain
  for _, r in ipairs(rows) do
    if r.state=='healthy' and (not best or r.latency_ms<best.latency_ms) then best=r end
    local invalid=r.reason=='core_config_invalid' and r.diagnostic and r.diagnostic.exit_code==23
    if r.state~='healthy' and r.state~='unhealthy' and not invalid then uncertain=true end
  end
  if best then return {state='candidate', node=best.id} end
  if uncertain then return {state='unknown', reason='incomplete_tests'} end
  if direct_verified then return {state='candidate', node='_direct'} end
  return {state='unknown', reason='direct_unverified'}
end
-- Advisory only: describe exactly one possible future write. No mutations.
function M.plan(report,cursor,now)
  local function blocked(reason) return {state='blocked',reason=reason,applied=false} end
  if report.mode~='observe_only' or not report.complete or report.running then return blocked('tests_incomplete') end
  if not report.finished_at or now<report.finished_at or now-report.finished_at>300 then return blocked('results_stale') end
  if not report.snapshot_current or not M.guard(cursor) then return blocked('shunt_or_snapshot_changed') end
  if cursor:get('passwall2','@global[0]','node')~='rulenode' then return blocked('active_node_is_not_rulenode') end
  if not report.stability or not report.stability.ready then return blocked('stability_pending') end
  local stable_rows=report.stability.rows or {}
  local choice=M.recommend(stable_rows,true,report.stability.direct_verified==true)
  if not choice.node then return blocked(choice.reason or 'no_candidate') end
  local id=choice.node
  if id~='_direct' and (not id:match('^[%w_]+$') or cursor:get('passwall2',id)~='nodes') then return blocked('candidate_missing') end
  local current=cursor:get('passwall2','rulenode','default_node')
  if current==id then return {state='keep',reason='current_is_best',node=id,applied=false} end
  local selected,current_row
  for _,r in ipairs(stable_rows) do
    if r.id==id then selected=r end
    if r.id==current then current_row=r end
  end
  -- Keep a working default unless the gain exceeds 20% and 100 ms.
  if current_row and current_row.state=='healthy' and
    current_row.latency_ms-selected.latency_ms<=math.max(100,current_row.latency_ms*0.2) then
    return {state='keep',reason='gain_too_small',node=current,applied=false}
  end
  return {state='awaiting_approval',reason=id=='_direct' and 'direct_fallback' or current_row and current_row.state=='healthy' and 'faster_candidate' or 'healthy_candidate',
    config='passwall2',section='rulenode',option='default_node',expected=current,node=id,applied=false}
end
return M

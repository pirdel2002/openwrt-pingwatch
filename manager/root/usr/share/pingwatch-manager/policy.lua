local M = {}
function M.inventory(cursor)
  local nodes, subscriptions = {}, {}
  cursor:foreach('passwall2', 'subscribe_list', function(s)
    subscriptions[#subscriptions+1] = {id=s['.name']}
  end)
  cursor:foreach('passwall2', 'nodes', function(s)
    if type(s.protocol)=='string' and s.protocol:sub(1,1)~='_' then
      nodes[#nodes+1] = {id=s['.name'], core=s.type, protocol=s.protocol}
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
    if r.state~='healthy' and r.state~='unhealthy' then uncertain=true end
  end
  if best then return {state='candidate', node=best.id} end
  if uncertain then return {state='unknown', reason='incomplete_tests'} end
  if direct_verified then return {state='candidate', node='_direct'} end
  return {state='unknown', reason='direct_unverified'}
end
return M

-- Pure transaction orchestration; all operating-system effects are injected.
local M={}
function M.run(e)
  local function blocked(reason) return {state='blocked',reason=reason,applied=false} end
  if not e.enabled() then return blocked('disabled') end
  local before=e.read()
  local plan=e.proposal(before)
  if not plan or plan.state~='awaiting_approval' then return blocked(plan and plan.reason or 'no_plan') end
  if not e.retest(plan.node) then return blocked('candidate_retest_failed') end
  if not e.enabled() then return blocked('disabled') end
  if e.read()~=before then return blocked('config_changed') end
  local candidate=e.prepare(before,plan.node)
  if not candidate or not e.only_default(before,candidate,plan.node) then return blocked('scope_verification_failed') end
  e.backup(before)
  if not e.enabled() then return blocked('disabled') end
  if not e.replace(before,candidate) then return blocked('write_conflict') end
  local ok,restarted=pcall(e.restart)
  local healthy=false
  if ok and restarted then local checked,result=pcall(e.active); healthy=checked and result==true end
  if healthy then return {state='applied_verified',applied=true,previous=plan.expected,node=plan.node} end
  pcall(e.disable)
  local restored=false
  local rollback_ok,result=pcall(e.rollback,plan.expected,plan.node,before)
  if rollback_ok and result then
    local restart_ok,restart_result=pcall(e.restart)
    if restart_ok and restart_result then local checked,health=pcall(e.active); restored=checked and health==true end
    return {state=restored and 'rolled_back_verified' or 'rolled_back_unverified',applied=false,node=plan.expected,disabled=true}
  end
  return {state='rollback_conflict',applied=true,node=plan.node,disabled=true,requires_attention=true}
end
return M

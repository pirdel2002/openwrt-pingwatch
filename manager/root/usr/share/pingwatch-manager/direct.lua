-- Conservative nftables proof for a child whose socket GID is 9912.
-- Unknown output rules or unavailable evidence leave direct UNVERIFIED.
local M={}
function M.firewall(ruleset)
  if type(ruleset)~='table' or type(ruleset.nftables)~='table' then return false end
  local chains,roots={},{}
  local function key(s) return s.family..'/'..s.table..'/'..s.name end
  for _,entry in ipairs(ruleset.nftables) do
    local c=entry.chain
    if c and (c.family=='inet' or c.family=='ip') then
      chains[key(c)]={rules={}}
      if c.hook=='output' then roots[#roots+1]=key(c) end
    end
  end
  for _,entry in ipairs(ruleset.nftables) do
    local r=entry.rule
    if r and (r.family=='inet' or r.family=='ip') then
      if type(r.expr)~='table' then return false end
      local k=r.family..'/'..r.table..'/'..r.chain
      if not chains[k] then return false end
      chains[k].rules[#chains[k].rules+1]=r.expr
    end
  end
  local seen_bypass=false
  local function only(e,name)
    if type(e)~='table' then return false end
    local count=0
    for k in pairs(e) do if k~=name then return false end; count=count+1 end
    return count==1
  end
  local function bypass(expr)
    local filtered={}
    for _,e in ipairs(expr or {}) do if not only(e,'counter') then filtered[#filtered+1]=e end end
    if #filtered~=2 then return false end
    if not only(filtered[1],'match') or not only(filtered[2],'return') then return false end
    local m=filtered[1].match
    return m and m.op=='==' and m.left and m.left.meta and m.left.meta.key=='skgid' and
      (m.right==9912 or m.right=='9912') and filtered[2]['return']~=nil
  end
  local function safe(k,stack)
    if stack[k] or not chains[k] then return false end
    stack[k]=true
    for _,expr in ipairs(chains[k].rules) do
      if bypass(expr) then seen_bypass=true; stack[k]=nil; return true end
      for _,e in ipairs(expr or {}) do
        for name,v in pairs(e) do
          if name=='jump' or name=='goto' then
            if type(v)~='table' or not v.target or not safe(k:match('^(.-/.-/)')..v.target,stack) then return false end
          elseif not ({match=true,counter=true,log=true,accept=true,drop=true,reject=true,['return']=true})[name] then
            return false
          end
        end
      end
    end
    stack[k]=nil; return true
  end
  if #roots==0 then return false end
  for _,k in ipairs(roots) do if not safe(k,{}) then return false end end
  return seen_bypass
end
function M.wan(status,proto)
  if not ({dhcp=true,static=true,pppoe=true})[proto] or not status or status.up~=true then return nil end
  local dev=status.l3_device
  if type(dev)~='string' or not dev:match('^[%w_.:%-]+$') or dev=='lo' or dev:match('^wg') or dev:match('^tun') or dev:match('^tailscale') then return nil end
  return dev
end
return M

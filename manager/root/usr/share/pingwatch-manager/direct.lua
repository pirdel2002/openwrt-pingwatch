-- Conservative nftables proof for a child whose socket GID is 9912.
-- Unknown output rules or unavailable evidence leave direct UNVERIFIED.
local M={}
-- luci.jsonc may drop object members whose JSON value is null. Preserve null
-- tokens before decoding; never rewrite text inside JSON strings/comments.
function M.decode(raw,parse)
  if type(raw)~='string' then return nil end
  local out,inside,escaped={},false,false
  local i=1
  while i<=#raw do
    local c=raw:sub(i,i)
    if inside then
      out[#out+1]=c
      if escaped then escaped=false elseif c=='\\' then escaped=true elseif c=='"' then inside=false end
      i=i+1
    elseif c=='"' then inside=true; out[#out+1]=c; i=i+1
    elseif raw:sub(i,i+3)=='null' then out[#out+1]='{"_null":true}'; i=i+4
    else out[#out+1]=c; i=i+1 end
  end
  return parse(table.concat(out))
end
function M.firewall(ruleset)
  if type(ruleset)~='table' or type(ruleset.nftables)~='table' then return false,'ruleset_unreadable' end
  local chains,roots={},{}
  local function key(s) return s.family..'/'..s.table..'/'..s.name end
  for _,entry in ipairs(ruleset.nftables) do
    local c=entry.chain
    if c and (c.family=='inet' or c.family=='ip') then
      chains[key(c)]={rules={},definition={hook=c.hook,type=c.type,prio=c.prio,policy=c.policy,dev=c.dev}}
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
  local proof={}
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
  local function simple_vmap(v)
    if type(v)~='table' or not v.key or not v.key.ct or v.key.ct.key~='state' or
      not v.data or type(v.data.set)~='table' or #v.data.set==0 then return false end
    for _,pair in ipairs(v.data.set) do
      if type(pair)~='table' or #pair~=2 or not ({established=true,related=true,new=true,invalid=true,untracked=true})[pair[1]] then return false end
      local verdict=pair[2]
      if not (only(verdict,'accept') or only(verdict,'drop') or only(verdict,'return') or only(verdict,'continue')) then return false end
    end
    return true
  end
  local function safe(k,stack)
    if stack[k] or not chains[k] then return false,'chain_graph_unknown' end
    stack[k]=true
    proof[k]={definition=chains[k].definition,rules={}}
    for _,expr in ipairs(chains[k].rules) do
      local filtered={}
      for _,e in ipairs(expr) do if not only(e,'counter') then filtered[#filtered+1]=e end end
      proof[k].rules[#proof[k].rules+1]=filtered
      if bypass(expr) then seen_bypass=true; stack[k]=nil; return true end
      for _,e in ipairs(expr or {}) do
        for name,v in pairs(e) do
          if name=='jump' or name=='goto' then
            if type(v)~='table' or not v.target then return false,'chain_graph_unknown' end
            local ok,reason=safe(k:match('^(.-/.-/)')..v.target,stack)
            if not ok then return false,reason end
          elseif name=='vmap' then
            if not simple_vmap(v) then return false,'verdict_map_unsupported' end
          elseif not ({match=true,counter=true,log=true,accept=true,drop=true,reject=true,['return']=true})[name] then
            return false,'output_action_unknown'
          end
        end
      end
    end
    stack[k]=nil; return true
  end
  if #roots==0 then return false,'output_hooks_missing' end
  table.sort(roots)
  for _,k in ipairs(roots) do local ok,reason=safe(k,{}); if not ok then return false,reason end end
  local function canonical(v)
    if type(v)=='string' then return 'string:'..#v..':'..v end
    if type(v)~='table' then return type(v)..':'..tostring(v) end
    local keys,out={},{}
    for k in pairs(v) do keys[#keys+1]=k end
    table.sort(keys,function(a,b) return type(a)..tostring(a)<type(b)..tostring(b) end)
    for _,k in ipairs(keys) do out[#out+1]=canonical(k)..'='..canonical(v[k]) end
    return '{'..table.concat(out,';')..'}'
  end
  if seen_bypass then return true,nil,canonical(proof) end
  return false,'gid_bypass_missing'
end
function M.route(raw,dev)
  local first=(raw or ''):match('([^\n]+)') or ''
  if first:match('%f[%a]dev%s+([%w_.:%-]+)')~=dev then return nil end
  return table.concat({dev,first:match('%f[%a]via%s+([%d.]+)') or '',
    first:match('%f[%a]src%s+([%d.]+)') or '',first:match('%f[%a]table%s+([%w_%-]+)') or 'main'},'|')
end
function M.wan(status,proto)
  if not ({dhcp=true,static=true,pppoe=true})[proto] or not status or status.up~=true then return nil end
  local dev=status.l3_device
  if type(dev)~='string' or not dev:match('^[%w_.:%-]+$') or dev=='lo' or dev:match('^wg') or dev:match('^tun') or dev:match('^tailscale') then return nil end
  return dev
end
return M

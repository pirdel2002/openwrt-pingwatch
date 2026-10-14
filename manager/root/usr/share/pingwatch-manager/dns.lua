local M={}
function M.ipv4(value)
  if type(value)~='string' then return false end
  local a,b,c,d=value:match('^(%d+)%.(%d+)%.(%d+)%.(%d+)$')
  if not a then return false end
  for _,v in ipairs({a,b,c,d}) do if #v>3 or tonumber(v)>255 then return false end end
  a=tonumber(a)
  return a>0 and a<224 and a~=127
end
function M.servers(status)
  local result,seen={},{}
  for _,value in ipairs((status or {})['dns-server'] or {}) do
    if M.ipv4(value) and not seen[value] and #result<2 then seen[value]=true; result[#result+1]=value end
  end
  return result
end
function M.answers(text)
  local found,seen,result=false,{},{}
  for line in (text or ''):gmatch('[^\r\n]+') do
    if line:match('^%s*Name:%s*%S') then found=true end
    if found then
      local ip=line:match('^%s*Address%s*%d*:%s*([%d.]+)')
      if M.ipv4(ip) and not seen[ip] then seen[ip]=true; result[#result+1]=ip end
    end
  end
  return result
end
return M

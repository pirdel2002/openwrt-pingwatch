-- Return only fixed labels. Never return matched text or native error bodies.
local M={}
function M.classify(text,exit_code)
  if exit_code==124 or exit_code==137 then return 'validation_timeout' end
  local s=(text or ''):lower()
  local function has(v) return s:find(v,1,true)~=nil end
  if has('xhttp') and has('mode') then return 'xhttp_mode_invalid' end
  if has('reality') and (has('public') or has('password')) then return 'reality_key_invalid' end
  if has('reality') then return 'reality_config_invalid' end
  if has('uuid') or has('invalid user id') then return 'user_id_invalid' end
  if has('flow') then return 'flow_invalid' end
  if has('cipher') or has('encryption') then return 'encryption_invalid' end
  if has('certificate') or has('private key') then return 'tls_material_invalid' end
  if has('unknown transport') or has('unknown network') then return 'transport_unsupported' end
  if has('unknown field') then return 'config_field_unsupported' end
  if has('address already in use') then return 'port_in_use' end
  if has('permission denied') then return 'permission_denied' end
  if has('no such file') or has('not found') then return 'dependency_missing' end
  if has('invalid character') or has('unexpected end') then return 'json_invalid' end
  if has('failed to parse') or has('failed to build') then return 'config_parse_or_build_failed' end
  return 'unclassified_core_error'
end
function M.shape(c,core)
  local out={}
  local protocols={vless=true,vmess=true,trojan=true,shadowsocks=true,socks=true,freedom=true,blackhole=true,direct=true,block=true}
  local transports={tcp=true,raw=true,ws=true,grpc=true,xhttp=true,splithttp=true,httpupgrade=true,http=true,kcp=true,quic=true}
  local securities={none=true,tls=true,reality=true}
  for i,o in ipairs(c.outbounds or {}) do
    if i>8 then break end
    local stream=o.streamSettings or {}
    local p=o.protocol or o.type
    local t=stream.method or stream.network or (o.transport or {}).type
    local security=stream.security
    if core~='Xray' and o.tls then security=o.tls.reality and 'reality' or 'tls' end
    out[#out+1]={protocol=protocols[p] and p or 'other',transport=transports[t] and t or 'unspecified',security=securities[security] and security or 'unspecified'}
  end
  return out
end
return M

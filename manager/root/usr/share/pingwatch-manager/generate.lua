-- Run only in a private subprocess against a copied UCI configuration.
local dir, id, port = arg[1], arg[2], tonumber(arg[3])
assert(dir:match('^/tmp/pingwatch%-manager/work/config$'))
assert(id:match('^[%w_]+$') and port and port>=1024 and port<=65535)
local uci = require('luci.model.uci').cursor(dir)
local n = assert(uci:get_all('passwall2',id))
assert(n['.type']=='nodes' and n.protocol and n.protocol:sub(1,1)~='_')
-- Chained, interface and plugin nodes need a separate compatibility adapter.
for _, k in ipairs({'preproxy_node','to_node','outbound_node','outbound_node_iface','iface'}) do
  assert(not n[k] or n[k]=='' or n[k]=='nil')
end
assert(not n.plugin or n.plugin=='' or n.plugin=='none')
local api = require('luci.passwall2.api')
local reader=uci
uci=setmetatable({}, {__index=function(_,key)
  return function(_,...) return reader[key](reader,...) end
end})
api.uci=uci
for _, k in ipairs({'set','set_list','delete','commit','save','revert','add','section'}) do
  uci[k]=function() error('read_only') end
end
api.TMP_PATH='/tmp/pingwatch-manager/work'
api.CACHE_PATH=api.TMP_PATH..'/cache'
api.TMP_IFACE_PATH=api.TMP_PATH..'/iface'
api.LOG_FILE='/dev/null'
api.get_app_path=function(name)
  return ({xray='/usr/bin/xray',['sing-box']='/usr/bin/sing-box'})[name]
end
api.get_app_version=function(name)
  local bin=assert(api.get_app_path(name))
  return assert(api.sys.exec(bin..' version 2>/dev/null'):match('(%d+%.%d+%.%d+)'))
end
-- Native generators append direct-node bookkeeping. Suppress it; reject all
-- other shell mutations, including nested run_socks and firewall operations.
api.sys.call=function(cmd)
  if cmd:match("^echo '[%w_]+' >> /tmp/pingwatch%-manager/work/direct_node_list$") then return 0 end
  error('generator_side_effect')
end
local module_name = ({Xray='util_xray',['Sing-Box']='util_sing-box',['sing-box']='util_sing-box'})[n.type]
assert(module_name)
arg={}
local generator=require('luci.passwall2.'..module_name)
local result=assert(generator.gen_config({node=id,local_socks_address='127.0.0.1',local_socks_port=tostring(port),loglevel='error',log='0'}))
local c=assert(api.jsonc.parse(result))
assert(c.inbounds and #c.inbounds==1)
local inbound=c.inbounds[1]
assert(inbound.listen=='127.0.0.1')
assert((inbound.protocol or inbound.type)=='socks')
assert((inbound.port or inbound.listen_port)==port)
-- Explicitly bypass Passwall interception using its native mark convention.
for _, o in ipairs(c.outbounds or {}) do
  if n.type=='Xray' then
    o.streamSettings=o.streamSettings or {}; o.streamSettings.sockopt=o.streamSettings.sockopt or {}
    o.streamSettings.sockopt.mark=255
  else o.routing_mark=255 end
end
assert(not c.endpoints or #c.endpoints==0)
if n.type=='Xray' then c.log={loglevel='none'} else c.log={disabled=true} end
print(api.jsonc.stringify(c))

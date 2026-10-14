'use strict';
'require view';
'require form';
'require uci';
'require fs';
'require poll';
'require ui';
'require network';

function statusClass(state) {
	if (state === 'UP') return 'success';
	if (state === 'DOWN') return 'danger';
	return 'warning';
}

function makeStatusRow(x) {
	return E('div', { 'class': 'tr' }, [
		E('div', { 'class': 'td' }, x.name || x.section || '-'),
		E('div', { 'class': 'td' }, x.host || '-'),
		E('div', { 'class': 'td' }, [
			E('span', { 'class': 'label ' + statusClass(x.state) }, x.state || 'UNKNOWN')
		]),
		E('div', { 'class': 'td' },
			_('Fails: %d / OK: %d').format(x.fails || 0, x.oks || 0))
	]);
}

function tabButton(title, id, active) {
	return E('button', {
		'class': 'btn cbi-button ' + (active ? 'cbi-button-positive' : ''),
		'data-tab': id,
		'style': 'margin-inline-end:6px;margin-bottom:8px'
	}, title);
}

return view.extend({
	load: function() {
		return Promise.all([
			uci.load('pingwatch'),
			fs.exec('/usr/sbin/pingwatch-status-json').catch(function() {
				return { code: 1, stdout: '[]', stderr: '' };
			}),
			network.getDevices().catch(function() { return []; }),
			fs.exec('/usr/sbin/pingwatch-led-status-json').catch(function() {
				return { code: 1, stdout: '{"enabled":false,"color":"#000000","source":"Unknown","state":"UNKNOWN"}', stderr: '' };
			})
		]);
	},

	render: function(data) {
		var self = this;
		var statusData = [];
		try { statusData = JSON.parse((data[1] && data[1].stdout) || '[]'); } catch (e) {}

		var ledData = { enabled: false, color: '#000000', source: 'Unknown', state: 'UNKNOWN' };
		try { ledData = JSON.parse((data[3] && data[3].stdout) || '{}'); } catch (e) {}

		var devices = (data[2] || []).map(function(d) {
			return d.getName();
		}).filter(function(n, i, a) {
			return n && a.indexOf(n) === i;
		}).sort();

		/* STATUS TAB */
		var statusTable = E('div', { 'class': 'table' }, statusData.map(makeStatusRow));

		var smsResult = E('div', {
			'style': 'margin-top:10px;padding:10px;border:1px solid #777;border-radius:4px;display:none;white-space:pre-wrap'
		});

		function showSmsResult(ok, text) {
			smsResult.style.display = 'block';
			smsResult.style.fontWeight = '600';
			smsResult.textContent = (ok ? _('SUCCESS') : _('FAILED')) + '\n' + text;
		}

		var ledBadge = E('div', {
			'style': 'display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:10px 12px;margin-bottom:12px;border:1px solid #777;border-radius:6px'
		}, [
			E('strong', {}, _('LED:')),
			E('span', {
				'id': 'pingwatch-led-swatch',
				'style': 'display:inline-block;width:22px;height:22px;border-radius:50%;border:1px solid #555;background:' + (ledData.color || '#000000')
			}),
			E('code', { 'id': 'pingwatch-led-color' }, ledData.color || '#000000'),
			E('span', {}, '←'),
			E('span', { 'id': 'pingwatch-led-source' }, ledData.source || _('Unknown'))
		]);

		var statusPane = E('div', { 'data-pane': 'status' }, [
			ledBadge,
			E('div', { 'class': 'cbi-section', 'id': 'pingwatch-status' }, [
				E('h3', {}, _('Live status')),
				statusTable
			]),
			E('div', { 'class': 'cbi-section' }, [
				E('h3', {}, _('Actions')),
				E('button', {
					'class': 'btn cbi-button cbi-button-action',
					'click': ui.createHandlerFn(this, function() {
						return fs.exec('/etc/init.d/pingwatch', ['restart'])
							.then(function() {
								ui.addNotification(null, E('p', {}, _('PingWatch restarted.')), 'info');
							})
							.catch(function(err) {
								ui.addNotification(null, E('p', {}, _('Restart failed: ') + String(err)), 'error');
							});
					})
				}, _('Restart service')),
				' ',
				E('button', {
					'class': 'btn cbi-button cbi-button-action',
					'click': ui.createHandlerFn(this, function() {
						showSmsResult(true, _('Testing...'));
						return fs.exec('/usr/sbin/pingwatch-send-sms', ['--test', 'تست PingWatch'])
							.then(function(res) {
								var msg = ((res && (res.stdout || res.stderr)) || '').trim();
								var code = (res && typeof res.code === 'number') ? res.code : 0;
								showSmsResult(code === 0, msg || _('No response text returned.'));
							})
							.catch(function(err) {
								var msg = '';
								if (err) {
									if (err.stdout) msg += err.stdout;
									if (err.stderr) msg += (msg ? '\n' : '') + err.stderr;
									if (!msg) msg = String(err);
								}
								showSmsResult(false, msg || _('Execution failed.'));
							});
					})
				}, _('Send test SMS')),
				smsResult,
				E('p', { 'style': 'margin-top:10px;opacity:.8' },
					_('Test SMS works even when Enable SMS is off. Automatic alerts are sent only on a confirmed DOWN or RECOVERED transition.'))
			])
		]);

		/* SETTINGS TAB */
		var settingsMap = new form.Map('pingwatch', _('Settings'));

		var g = settingsMap.section(form.TypedSection, 'main', _('General'));
		g.anonymous = true;
		g.addremove = false;

		var o = g.option(form.Value, 'loop_sleep', _('Scheduler resolution (seconds)'));
		o.datatype = 'uinteger';
		o.default = '3';

		o = g.option(form.Flag, 'led_enabled', _('Enable LED status'));
		o.default = '0';
		o.description = _('Controls router LED independently from SMS. LED reacts to the first failed or successful check.');

		o = g.option(form.Value, 'ok_led_color', _('All OK LED color'));
		o.default = '#00ff00';
		o.datatype = 'string';
		o.renderWidget = function(section_id, option_index, cfgvalue) {
			var id = this.cbid(section_id);
			return E('input', {
				'id': id,
				'name': id,
				'type': 'color',
				'value': cfgvalue || '#00ff00',
				'style': 'width:72px;height:34px;padding:2px'
			});
		};
		o.formvalue = function(section_id) {
			var el = document.getElementById(this.cbid(section_id));
			return el ? el.value : this.cfgvalue(section_id);
		};


		var inet = settingsMap.section(form.TypedSection, 'internet', _('Internet outage detection'));
		inet.anonymous = true;
		inet.addremove = false;

		o = inet.option(form.Flag, 'enabled', _('Enable Internet Down detection'));
		o.default = '0';
		o.description = _('When every enabled target marked as Internet Reference is confirmed DOWN, one Internet Down SMS is sent. Recovery is also aggregated.');

		var sms = settingsMap.section(form.TypedSection, 'sms', _('IPPanel SMS'));
		sms.anonymous = true;
		sms.addremove = false;

		o = sms.option(form.Flag, 'enabled', _('Enable SMS'));
		o.default = '0';
		o.description = _('Controls automatic outage/recovery alerts only. Test SMS is always available.');

		o = sms.option(form.Value, 'api_key', _('API key'));
		o.password = true;
		o.rmempty = true;

		o = sms.option(form.Value, 'from_number', _('Sender number'));
		o.placeholder = '+983000505';

		o = sms.option(form.DynamicList, 'recipient', _('Recipients'));
		o.placeholder = '+98912...';

		o = sms.option(form.Value, 'timeout', _('API timeout (seconds)'));
		o.datatype = 'uinteger';
		o.default = '12';

		/* TARGETS TAB */
		var targetsMap = new form.Map('pingwatch', _('Targets'),
			_('Drag targets to set LED priority. LED changes on the first failed/successful check; SMS still uses the configured failure and recovery thresholds.'));

		var tg = targetsMap.section(form.GridSection, 'target', _('Targets'));
		tg.addremove = true;
		tg.sortable = true;
		tg.anonymous = true;

		o = tg.option(form.Flag, 'enabled', _('Enabled'));
		o.default = '1';
		o.editable = true;

		o = tg.option(form.Value, 'name', _('Name'));
		o.rmempty = false;
		o.editable = true;
		o.description = _('This name is used in SMS messages.');

		o = tg.option(form.Value, 'host', _('Host / IP'));
		o.rmempty = false;
		o.editable = true;

		o = tg.option(form.ListValue, 'notify_mode', _('Notification mode'));
		o.value('both', _('Both'));
		o.value('down', _('Down only'));
		o.value('recovery', _('Recovery only'));
		o.value('disabled', _('Disabled'));
		o.default = 'both';
		o.modalonly = true;
		o.description = _('Controls SMS alerts for this target only. LED behavior is independent.');


		o = tg.option(form.ListValue, 'test_type', _('Test type'));
		o.value('icmp', _('ICMP Ping'));
		o.value('tcp', _('TCP Port'));
		o.value('http', _('HTTP / HTTPS'));
		o.value('dns', _('DNS Resolve'));
		o.default = 'icmp';
		o.modalonly = true;

		o = tg.option(form.Value, 'tcp_port', _('TCP port'));
		o.datatype = 'port';
		o.default = '443';
		o.modalonly = true;
		o.depends('test_type', 'tcp');

		o = tg.option(form.Value, 'http_url', _('HTTP/HTTPS URL'));
		o.placeholder = 'https://example.com/';
		o.modalonly = true;
		o.depends('test_type', 'http');

		o = tg.option(form.Flag, 'internet_reference', _('Internet Reference'));
		o.default = '0';
		o.modalonly = true;
		o.description = _('Use this target when determining a general Internet outage.');

		o = tg.option(form.DynamicList, 'extra_recipient', _('Additional SMS recipients'));
		o.placeholder = '+98912...';
		o.modalonly = true;
		o.description = _('These numbers receive this target alerts in addition to the global SMS recipients.');

		o = tg.option(form.Value, 'sms_cooldown', _('SMS cooldown (seconds)'));
		o.datatype = 'uinteger';
		o.default = '0';
		o.modalonly = true;
		o.description = _('0 disables cooldown. Thresholds still apply before a state change is confirmed.');


		o = tg.option(form.Flag, 'led_enabled', _('Use for LED'));
		o.default = '1';
		o.modalonly = true;

		o = tg.option(form.Value, 'led_color', _('LED Color'));
		o.default = '#ff0000';
		o.editable = true;
		o.renderWidget = function(section_id, option_index, cfgvalue) {
			var id = this.cbid(section_id);
			return E('input', {
				'id': id,
				'name': id,
				'type': 'color',
				'value': cfgvalue || '#ff0000',
				'style': 'width:64px;height:32px;padding:1px'
			});
		};
		o.formvalue = function(section_id) {
			var el = document.getElementById(this.cbid(section_id));
			return el ? el.value : this.cfgvalue(section_id);
		};

		o = tg.option(form.ListValue, 'interface', _('Interface'));
		o.value('', _('Automatic'));
		devices.forEach(function(dev) { o.value(dev, dev); });
		o.default = '';
		o.modalonly = true;

		o = tg.option(form.Value, 'interval', _('Interval (s)'));
		o.datatype = 'uinteger';
		o.default = '15';
		o.modalonly = true;

		o = tg.option(form.Value, 'timeout', _('Ping timeout (s)'));
		o.datatype = 'uinteger';
		o.default = '2';
		o.modalonly = true;

		o = tg.option(form.Value, 'count', _('Pings per check'));
		o.datatype = 'uinteger';
		o.default = '1';
		o.modalonly = true;

		o = tg.option(form.Value, 'fail_threshold', _('Failures before DOWN'));
		o.datatype = 'uinteger';
		o.default = '3';
		o.modalonly = true;

		o = tg.option(form.Value, 'recover_threshold', _('Successes before UP'));
		o.datatype = 'uinteger';
		o.default = '2';
		o.modalonly = true;

		poll.add(function() {
			return fs.exec('/usr/sbin/pingwatch-status-json')
				.then(function(res) {
					var arr = [];
					try { arr = JSON.parse(res.stdout || '[]'); } catch (e) {}
					statusTable.replaceChildren.apply(statusTable, arr.map(makeStatusRow));
				})
				.catch(function() {});
		}, 5);

		poll.add(function() {
			return fs.exec('/usr/sbin/pingwatch-led-status-json')
				.then(function(res) {
					var x = {};
					try { x = JSON.parse(res.stdout || '{}'); } catch (e) {}
					var color = x.color || '#000000';
					var sw = document.getElementById('pingwatch-led-swatch');
					var ct = document.getElementById('pingwatch-led-color');
					var sc = document.getElementById('pingwatch-led-source');
					if (sw) sw.style.background = color;
					if (ct) ct.textContent = color;
					if (sc) sc.textContent = x.source || _('Unknown');
				})
				.catch(function() {});
		}, 3);

		return Promise.all([settingsMap.render(), targetsMap.render()]).then(function(nodes) {
			var settingsPane = E('div', { 'data-pane': 'settings', 'style': 'display:none' }, [nodes[0]]);
			var targetsPane = E('div', { 'data-pane': 'targets', 'style': 'display:none' }, [nodes[1]]);

			var buttons = [
				tabButton(_('Status'), 'status', true),
				tabButton(_('Settings'), 'settings', false),
				tabButton(_('Targets'), 'targets', false)
			];

			var root = E('div', {}, [
				E('h2', {}, _('PingWatch')),
				E('div', { 'class': 'cbi-section', 'style': 'padding-bottom:0' }, buttons),
				statusPane,
				settingsPane,
				targetsPane
			]);

			buttons.forEach(function(btn) {
				btn.addEventListener('click', function(ev) {
					ev.preventDefault();
					var id = btn.getAttribute('data-tab');

					root.querySelectorAll('[data-pane]').forEach(function(p) {
						p.style.display = (p.getAttribute('data-pane') === id) ? '' : 'none';
					});

					buttons.forEach(function(b) {
						if (b === btn)
							b.classList.add('cbi-button-positive');
						else
							b.classList.remove('cbi-button-positive');
					});
				});
			});

			return root;
		});
	}
});

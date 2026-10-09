#!/usr/bin/env python3
"""Install once on every registered Shelly. Never changes light state."""
import sys, time
import luci_di_casa_mobile as app
ips = sys.argv[1:] or [ip for ip in app.D['devices'] if not app.is_tapo(ip)]
failed = False
for ip in ips:
 try:
  with app.device_lock(ip):
   sid = app.install_usage_logger(ip, force=True)
   state = app.usage_logger_status(ip, sid)
   if not state.get('ready'): raise RuntimeError(state.get('error') or 'Monitoraggio non pronto')
   print(ip, 'Monitoraggio installato, script', sid, '- avvio automatico abilitato')
   if state.get('error'): print('  In attesa:', state['error'])
 except Exception as e:
  failed = True
  print(ip, 'ERRORE:', e)
sys.exit(1 if failed else 0)

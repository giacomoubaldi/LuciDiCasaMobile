#!/usr/bin/env python3
"""Carica tutti gli effetti in un singolo script per ogni Shelly configurata."""
import argparse
import json
import sys
from luci_di_casa_mobile import D, device_lock, install_native, native_state, script_rpc, is_tapo

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--ip',help='Installa soltanto su questo IP; altrimenti tutte le lampadine configurate')
 args=parser.parse_args()
 ips=[args.ip] if args.ip else [ip for ip in D['devices'] if not is_tapo(ip)]
 for ip in ips:
  with device_lock(ip):
   sid=install_native(ip,force=True)
   script_rpc(ip,'Script.Start',{'id':sid})
   status=native_state(ip)
   if status.get('name') is not None:raise RuntimeError('Lo script deve essere inizialmente inattivo')
   script_rpc(ip,'Script.Stop',{'id':sid})
   print(ip+': codice verificato, script ID '+str(sid)+', pronto per PLAY.')
 print('Installazione completata. Avvia Luci di Casa e scegli un effetto.')

if __name__=='__main__':
 try:main()
 except Exception as e:
  print('ERRORE: '+str(e),file=sys.stderr);sys.exit(1)

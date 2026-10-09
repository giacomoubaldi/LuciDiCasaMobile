"""Controllo locale Tapo: sessioni python-kasa su un unico event loop."""
import asyncio
import colorsys
import json
import math
import time
import os
import tempfile
import threading
from pathlib import Path

AUTH_FILE=Path.home()/'.luci_tapo_credentials.json'
_loop=None
_loop_lock=threading.Lock()
_devices={}
_usage_cache={}

def credentials():
 try:
  data=json.loads(AUTH_FILE.read_text())
  if data.get('username') and data.get('password'):return data
 except (OSError,ValueError):pass
 username=os.environ.get('KASA_USERNAME','');password=os.environ.get('KASA_PASSWORD','')
 if not username or not password:raise RuntimeError('Configura l’account Tapo dal pulsante Account Tapo.')
 return {'username':username,'password':password}

def auth_status():
 try:
  c=credentials();return {'configured':True,'username':c['username']}
 except RuntimeError:return {'configured':False}

def _event_loop():
 global _loop
 with _loop_lock:
  if _loop is None:
   _loop=asyncio.new_event_loop()
   threading.Thread(target=_loop.run_forever,daemon=True,name='tapo-async').start()
 return _loop

async def _device(ip,auth,refresh=True):
 try:from kasa import Discover
 except ImportError:raise RuntimeError('Installa python-kasa: python -m pip install python-kasa anyio')
 key=(auth['username'],auth['password'])
 entry=_devices.get(ip)
 if entry and entry[0]==key:
  dev=entry[1]
 else:
  if entry:await entry[1].disconnect()
  _devices.pop(ip,None)
  dev=await Discover.discover_single(ip,username=auth['username'],password=auth['password'])
  if dev is None:raise RuntimeError('Tapo non trovata: '+ip)
  _devices[ip]=(key,dev)
 try:
  if refresh or not entry or entry[0]!=key:await dev.update()
 except Exception:
  _devices.pop(ip,None)
  try:await dev.disconnect()
  except Exception:pass
  raise
 return dev

def _state(dev):
 from kasa import Module
 light=dev.modules[Module.Light]
 ct=int(light.color_temp or 0)
 hsv=light.hsv
 rgb=[round(c*255) for c in colorsys.hsv_to_rgb(hsv.hue/360,hsv.saturation/100,1)]
 feature=dev.features.get('light_effect')
 effect=feature.value if feature else 'Off'
 return {'output':dev.is_on,'brightness':light.brightness,'ct':ct,'rgb':rgb,
         'mode':'cct' if ct else 'rgb','effect':None if effect=='Off' else effect,
         'available_effects':[e for e in feature.choices if e!='Off'] if feature else [],
         'energy_available':False}

def normalize_usage(raw,date):
 if 'get_device_usage' in raw:raw=raw['get_device_usage']
 times=raw.get('time_usage',{});powers=raw.get('power_usage',{})
 def number(v):
  return float(v) if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>=0 else None
 periods={}
 for key in ('today','past7','past30'):
  minutes=number(times.get(key))
  mwh=number(powers.get(key+'_mwh'))
  wh=mwh/1000 if mwh is not None else number(powers.get(key))
  periods[key]={'on_seconds':minutes*60 if minutes is not None else None,'wh':wh}
 return {'date':date,'periods':periods,'source':'Tapo get_device_usage'}

async def _read_usage(ip,dev):
 try:date=str(dev.time.date())
 except Exception:return None
 cached=_usage_cache.get(ip)
 if cached and cached[0]==date and time.monotonic()-cached[1]<60:return cached[2]
 try:
  raw=await dev.protocol.query({'get_device_usage':None})
  usage=normalize_usage(raw,date)
  usage['sampled_at']=time.time()
  if all(p['wh'] is None and p['on_seconds'] is None for p in usage['periods'].values()):return None
  _usage_cache[ip]=(date,time.monotonic(),usage)
  return usage
 except Exception:
  # L'assenza della telemetria energetica non blocca i comandi della luce.
  return None

async def _reported_state(ip,dev):
 state=_state(dev)
 usage=await _read_usage(ip,dev)
 if usage:
  state['native_usage']=usage
  state['energy_available']=usage['periods']['today']['wh'] is not None
 return state

async def _request(ip,operation,params,auth):
 try:from kasa import Module
 except ImportError:raise RuntimeError('Installa python-kasa: python -m pip install python-kasa anyio')
 dev=None
 try:
  dev=await _device(ip,auth,refresh=operation!='music')
  if operation=='music':
   rgb=params['rgb'];brightness=int(params['brightness'])
   if len(rgb)!=3 or any(not isinstance(v,int) or isinstance(v,bool) or not 0<=v<=255 for v in rgb) or not 1<=brightness<=100:raise ValueError('Frame musicale Tapo non valido')
   h,s,v=colorsys.rgb_to_hsv(*(c/255 for c in rgb))
   await dev.modules[Module.Light].set_hsv(round(h*360)%360,round(s*100),brightness)
   return {'ok':True}
  if operation in ('state','test'):return await _reported_state(ip,dev)
  effect=dev.features.get('light_effect')
  if operation=='effect':
   name=params['name']
   if not effect or name not in effect.choices:raise ValueError('Effetto Tapo non disponibile: '+name)
   await dev.turn_on()
   await effect.set_value(name)
  else:
   # Ogni comando manuale interrompe prima l'effetto interno Tapo.
   if effect:await effect.set_value('Off')
   if operation=='set':
    light=dev.modules[Module.Light]
    if params.get('on') is True:await dev.turn_on()
    brightness=params.get('brightness')
    if params.get('mode')=='cct' or ('ct' in params and params.get('mode')!='rgb'):
     ct=int(params.get('ct',3000))
     await light.set_color_temp(ct)
    elif params.get('mode')=='rgb' or 'rgb' in params:
     rgb=params.get('rgb',[255,255,255])
     if len(rgb)!=3 or any(not 0<=v<=255 for v in rgb):raise ValueError('Colore RGB non valido')
     h,s,v=colorsys.rgb_to_hsv(*(c/255 for c in rgb))
     # Lo spettro sceglie tonalità/saturazione; luminosità separata.
     value=int(brightness if brightness is not None else light.brightness)
     await light.set_hsv(round(h*360)%360,round(s*100),value)
     brightness=None
    if brightness is not None:await light.set_brightness(int(brightness))
    if params.get('on') is False:await dev.turn_off()
   elif operation!='stop':raise ValueError('Operazione Tapo sconosciuta')
  await dev.update()
  return await _reported_state(ip,dev)
 except Exception:
  _devices.pop(ip,None)
  if dev:
   try:await dev.disconnect()
   except Exception:pass
  raise

async def _limited(ip,operation,params,auth):
 return await asyncio.wait_for(_request(ip,operation,params,auth),timeout=20)

def request(ip,operation='state',params=None,auth=None):
 auth=auth or credentials()
 future=asyncio.run_coroutine_threadsafe(_limited(ip,operation,params or {},auth),_event_loop())
 try:return future.result(timeout=22)
 except Exception:
  future.cancel()
  raise

def configure(ip,username,password):
 username=username.strip()
 if not username or not password:raise ValueError('Inserisci email e password dell’account Tapo')
 auth={'username':username,'password':password}
 state=request(ip,'test',auth=auth)
 AUTH_FILE.parent.mkdir(parents=True,exist_ok=True)
 fd,path=tempfile.mkstemp(prefix='.luci-tapo-',dir=AUTH_FILE.parent)
 try:
  with os.fdopen(fd,'w') as f:json.dump(auth,f)
  os.chmod(path,0o600)
  os.replace(path,AUTH_FILE)
 finally:
  if os.path.exists(path):os.unlink(path)
 return state

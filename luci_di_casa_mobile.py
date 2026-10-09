#!/usr/bin/env python3
import sqlite3, datetime
import secrets
from zoneinfo import ZoneInfo
import tapo_adapter
from network_address import print_addresses
import json, math, os, random, socket, subprocess, threading, time, urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT=Path(__file__).parent
CFG=Path.home()/".shelly_home_mobile.json"
effects={}
EFFECTS={
"Happy":(2.2,[(255,70,20),(255,180,0),(40,220,90),(40,150,255),(220,60,220)],(55,90),"cycle"),
"Dance":(.55,[(255,0,40),(0,90,255),(170,0,255),(0,255,130),(255,80,0)],(65,100),"cycle"),
"Relax":(5,[(255,85,25),(255,130,35),(230,70,65),(190,70,130)],(20,45),"cycle"),
"Sunset":(4,[(255,150,35),(255,95,20),(255,55,35),(210,45,75),(130,35,100)],(30,65),"cycle"),
"Ocean":(3.3,[(0,80,255),(0,160,255),(0,220,210),(30,100,220),(40,210,180)],(35,70),"cycle"),
"Aurora":(3,[(20,255,130),(0,220,220),(40,100,255),(150,40,255),(60,220,150)],(40,75),"cycle"),
"Fireplace":(.38,[(255,45,0),(255,75,0),(255,110,10),(255,145,25)],(18,58),"random"),
"Pulse":(.35,[(100,30,255)],(15,85),"pulse"),
"Party":(.4,[(255,0,70),(255,120,0),(0,255,100),(0,150,255),(100,0,255),(255,0,220)],(70,100),"random"),
"Candle":(.45,[(255,80,8),(255,105,15),(255,125,25)],(12,32),"random")}
def load():
 try:return json.loads(CFG.read_text())
 except:return {"rooms":{"Casa":["192.168.1.7"]},"devices":{"192.168.1.7":{"name":"Shelly Duo"}},"scenes":{}}
D=load()
def save():CFG.write_text(json.dumps(D,indent=2))
def integrate_tapo_config():
 ip='192.168.1.8'
 D['devices'].setdefault(ip,{'name':'Lampada Cucina','type':'tapo','model':'L535E'})
 D['devices'][ip]['type']='tapo'
 D['rooms'].setdefault('Cucina',[])
 if ip not in D['rooms']['Cucina']:D['rooms']['Cucina'].append(ip)
 if 'Casa' in D['rooms'] and ip not in D['rooms']['Casa']:D['rooms']['Casa'].append(ip)
 save()

def is_tapo(ip):return D['devices'].get(ip,{}).get('type','shelly')=='tapo'
disabled_devices={}

def reset_disabled():
 for ip in list(D['devices']):
  with device_lock(ip):disabled_devices.pop(ip,None)

def device_status(ip):
 with device_lock(ip):
  if ip in disabled_devices:raise RuntimeError(disabled_devices[ip])
  error=None
  for attempt in range(3):
   try:
    return tapo_adapter.request(ip) if is_tapo(ip) else rpc(ip,'RGBCCT.GetStatus',{'id':0})
   except Exception as exc:error=exc
  message='Non raggiungibile dopo 3 tentativi. Esclusa fino al refresh della pagina.'
  disabled_devices[ip]=message
  stop_music_device(ip)
  raise RuntimeError(message) from error

def device_batch(ips, action):
 applied=[];skipped={};errors={}
 for ip in dict.fromkeys(ips):
  if ip not in D['devices']:
   errors[ip]='Lampada sconosciuta';continue
  with device_lock(ip):
   if ip in disabled_devices:
    skipped[ip]=disabled_devices[ip];continue
   try:device_status(ip)
   except Exception as exc:
    skipped[ip]=str(exc);continue
   try:
    action(ip);applied.append(ip)
   except Exception as exc:
    # A command error can be a capability error; exclude only if status also fails.
    try:device_status(ip)
    except Exception as offline:skipped[ip]=str(offline)
    else:errors[ip]=str(exc)
 return {'ok':True,'applied':applied,'skipped':skipped,'errors':errors}

def supported_effects(ip):return ['Party','Relax'] if is_tapo(ip) else list(EFFECTS)

def rpc(ip,m,p=None):
 u=f"http://{ip}/rpc/{m}"
 if p:
  e={}
  for k,v in p.items():e[k]=("true" if v else "false") if isinstance(v,bool) else json.dumps(v,separators=(",",":")) if isinstance(v,(list,dict)) else str(v)
  u+="?"+urllib.parse.urlencode(e)
 q=subprocess.run(["curl","-sS","--connect-timeout","1","--max-time","2",u],capture_output=True,text=True)
 if q.returncode:raise RuntimeError(q.stderr.strip())
 ans=json.loads(q.stdout)
 if isinstance(ans,dict) and ans.get("code"):raise RuntimeError(ans.get("message",str(ans)))
 return ans
NATIVE_NAME='Luci di Casa - Effects v1'
LEGACY_NAME='Luci di Casa - Dance v1'
effect_errors={}
device_locks={ip:threading.RLock() for ip in D['devices']}

def device_lock(ip):
 if ip not in D['devices']:raise ValueError('Lampadina sconosciuta: '+ip)
 return device_locks.setdefault(ip,threading.RLock())

def script_rpc(ip,method,params=None):
 body=json.dumps({'id':1,'method':method,'params':params or {}},separators=(',',':'))
 q=subprocess.run(['curl','-sS','--connect-timeout','2','--max-time','8','-H','Content-Type: application/json','--data-binary',body,'http://'+ip+'/rpc'],capture_output=True,text=True)
 if q.returncode:raise RuntimeError(q.stderr.strip() or 'Connessione fallita')
 ans=json.loads(q.stdout)
 if 'error' in ans:raise RuntimeError(method+': '+str(ans['error']))
 if 'result' not in ans:raise RuntimeError('Risposta RPC inattesa: '+str(ans))
 return ans['result']

def managed_scripts(ip):
 return [s for s in script_rpc(ip,'Script.List').get('scripts',[]) if s.get('name') in (NATIVE_NAME,LEGACY_NAME)]

def stop_native(ip):
 if is_tapo(ip):
  tapo_adapter.request(ip,'stop');return
 # Cerca anche dopo il riavvio del server: nessuna dipendenza da stato locale.
 for s in managed_scripts(ip):
  if s.get('running'):script_rpc(ip,'Script.Stop',{'id':s['id']})

def install_native(ip,force=False):
 if is_tapo(ip):raise ValueError('La Tapo usa Party e Relax interni; non richiede lo script Shelly')
 scripts=managed_scripts(ip)
 engines=[s for s in scripts if s['name']==NATIVE_NAME]
 if len(engines)>1:raise RuntimeError('Più script Effects con lo stesso nome')
 if engines and not force:return engines[0]['id']
 code=(ROOT/'shelly_effects.js').read_text(encoding='ascii')
 for s in scripts:
  if s.get('running'):script_rpc(ip,'Script.Stop',{'id':s['id']})
 if engines:sid=engines[0]['id']
 elif scripts:sid=scripts[0]['id']
 else:sid=script_rpc(ip,'Script.Create',{'name':NATIVE_NAME})['id']
 script_rpc(ip,'Script.SetConfig',{'id':sid,'config':{'name':NATIVE_NAME,'enable':False}})
 for i in range(0,len(code),768):
  script_rpc(ip,'Script.PutCode',{'id':sid,'code':code[i:i+768],'append':i>0})
 received='';offset=0
 while True:
  part=script_rpc(ip,'Script.GetCode',{'id':sid,'offset':offset,'len':1024})
  text=part.get('data','');received+=text;offset+=len(text.encode())
  if not part.get('left'):break
  if not text:raise RuntimeError('Verifica codice incompleta')
 if received!=code:raise RuntimeError('Codice caricato non corrispondente; effetto non avviato')
 return sid

USAGE_NAME='Luci di Casa - Usage v1'
usage_errors={}
usage_read_at={}

def usage_logger_status(ip,sid):
 r=script_rpc(ip,'Script.Eval',{'id':sid,'code':'JSON.stringify(getUsageStatus())'})
 return json.loads(r['result'])

def install_usage_logger(ip,force=False):
 if is_tapo(ip):raise ValueError('Monitoraggio interno riservato a Shelly')
 info=script_rpc(ip,'Shelly.GetDeviceInfo')
 version=info.get('ver','0.0').split('.')
 if tuple(int(v) for v in version[:2])<(1,5):raise RuntimeError('Aggiorna il firmware Shelly ad almeno 1.5 per lo storico interno')
 matches=[s for s in script_rpc(ip,'Script.List').get('scripts',[]) if s.get('name')==USAGE_NAME]
 if len(matches)>1:raise RuntimeError('Più script Usage con lo stesso nome')
 existing=matches[0] if matches else None
 if existing and not force:
  sid=existing['id']
  if not existing.get('running'):script_rpc(ip,'Script.Start',{'id':sid})
  return sid
 code=(ROOT/'shelly_usage.js').read_text(encoding='ascii')
 sid=existing['id'] if existing else script_rpc(ip,'Script.Create',{'name':USAGE_NAME})['id']
 if existing and existing.get('running'):
  # Preserve the unfinished quarter when replacing this same script slot.
  try:script_rpc(ip,'Script.Eval',{'id':sid,'code':'save();true'})
  except Exception:pass
  script_rpc(ip,'Script.Stop',{'id':sid})
 for i in range(0,len(code),768):
  script_rpc(ip,'Script.PutCode',{'id':sid,'code':code[i:i+768],'append':i>0})
 received='';offset=0
 while True:
  part=script_rpc(ip,'Script.GetCode',{'id':sid,'offset':offset,'len':1024})
  text=part.get('data','');received+=text;offset+=len(text.encode())
  if not part.get('left'):break
  if not text:raise RuntimeError('Verifica monitoraggio incompleta')
 if received!=code:raise RuntimeError('Verifica codice monitoraggio fallita')
 script_rpc(ip,'Script.SetConfig',{'id':sid,'config':{'name':USAGE_NAME,'enable':True}})
 script_rpc(ip,'Script.Start',{'id':sid})
 return sid

def sync_shelly_usage(ip,force=False):
 if is_tapo(ip):return
 now=time.time()
 if not force and now-usage_read_at.get(ip,0)<60:return
 usage_read_at[ip]=now
 try:
  with device_lock(ip):
   sid=install_usage_logger(ip)
   status=usage_logger_status(ip,sid)
   if not status.get('ready') or status.get('error'):raise RuntimeError(status.get('error') or 'Monitoraggio non pronto')
   if status.get('day') is None:raise RuntimeError('Orologio Shelly non sincronizzato')
   cfg=script_rpc(ip,'Sys.GetConfig')
   tz=(cfg.get('location') or {}).get('tz') or 'Europe/Rome'
   ZoneInfo(tz)  # reject an unknown zone rather than shifting history silently
   def part(kind,index):
    r=script_rpc(ip,'Script.Eval',{'id':sid,'code':'JSON.stringify(getUsagePart('+json.dumps(kind)+','+str(index)+'))'})
    return json.loads(r['result'])
   daily=part('daily',0)+part('daily',1)
   week=[part('week',i) for i in range(7)]
   q0=part('quarters',0);q1=part('quarters',1)
   # A midnight during retrieval must never mix two different days.
   if not q0 or not q1 or q0['d']!=q1['d'] or q0['d']!=status['day']:raise RuntimeError('Cambio giorno durante lettura: riprova tra un minuto')
   payload={'status':status,'tz':tz,'daily':daily,'week':week,'quarters':{**q0,'v':q0['v']+q1['v']},'read_at':now}
  with dbconnect() as c:c.execute('INSERT OR REPLACE INTO shelly_history VALUES (?,?,?)',(ip,now,json.dumps(payload)))
  usage_errors.pop(ip,None)
 except Exception as e:usage_errors[ip]=str(e)

def decoded_usage(value):
 if not value:return None
 energy,on,coverage=[int(x,36) for x in value.split('.')]
 return {'wh':energy/1000000,'on_seconds':on,'coverage_seconds':coverage,'energy_seconds':coverage}

def shelly_device_history(ip,days,interval_date,now):
 with dbconnect() as c:r=c.execute('SELECT data FROM shelly_history WHERE ip=?',(ip,)).fetchone()
 if not r:return None
 data=json.loads(r['data']);tz=ZoneInfo(data['tz']);day=data['status']['day']
 epoch=datetime.date(1970,1,1)
 today=epoch+datetime.timedelta(days=day)
 def timestamp(date,seconds=0):
  return (datetime.datetime.combine(date,datetime.time(),tz)+datetime.timedelta(seconds=seconds)).timestamp()
 def date_of(record):return epoch+datetime.timedelta(days=record['d'])
 byday={r['d']:r for r in data['daily'] if r and day-29<=r['d']<=day}
 daily=[]
 for n in reversed(range(days)):
  d=day-n;date=epoch+datetime.timedelta(days=d);record=byday.get(d)
  v=decoded_usage(record.get('v')) if record else None
  expected=max(0,min(timestamp(date+datetime.timedelta(days=1)),data['status']['ts'])-timestamp(date))
  daily.append({'date':str(date),'known':v is not None,'wh':v['wh'] if v else 0,'on_seconds':v['on_seconds'] if v else 0,'energy_seconds':v['energy_seconds'] if v else 0,'coverage_seconds':v['coverage_seconds'] if v else 0,'unknown_seconds':max(0,expected-(v['coverage_seconds'] if v else 0))})
 def bins_for(record,seconds):
  if not record:return []
  date=date_of(record);bins=[]
  for i,value in enumerate(record['v']):
   start=timestamp(date,i*seconds);end=timestamp(date,(i+1)*seconds)
   wall=datetime.datetime.combine(date,datetime.time())+datetime.timedelta(seconds=i*seconds)
   if datetime.datetime.fromtimestamp(start,tz).replace(tzinfo=None)!=wall:continue
   if end<=start:continue # nonexistent local times on DST spring transition
   v=decoded_usage(value);expected=max(0,min(end,data['status']['ts'])-start)
   status='future' if start>=data['status']['ts'] else 'missing' if v is None else 'complete' if v['coverage_seconds']>=expected-2 else 'partial'
   bins.append({'start':start,'end':end,'wh':v['wh'] if v else None,'on_seconds':v['on_seconds'] if v else None,'coverage_seconds':v['coverage_seconds'] if v else 0,'status':status})
  return bins
 chosen=today # the device intentionally retains fine detail for today only
 quarters={'date':str(chosen),'minutes':15,'bins':bins_for(data['quarters'],900) if chosen==today else [],'source':'shelly_device','timezone':data['tz']}
 two_hours=[]
 weeks={r['d']:r for r in data['week'] if r and day-6<=r['d']<=day}
 for n in reversed(range(7)):
  d=day-n;record=weeks.get(d)
  if not record:record={'d':d,'v':['']*12}
  two_hours.extend(bins_for(record,7200))
 return {'daily':daily,'quarters':quarters,'two_hours':{'minutes':120,'bins':two_hours,'source':'shelly_device','timezone':data['tz']},'device_history':{'updated_at':data['read_at'],'saved_at':data['status']['saved_at'],'timezone':data['tz'],'today':str(today),'error':usage_errors.get(ip),'retention':data['status']['retention']}}

def native_state(ip):
 if is_tapo(ip):
  st=device_status(ip);return {'name':st.get('effect'),'provider':'tapo'}
 scripts=managed_scripts(ip)
 for s in scripts:
  if s['name']==NATIVE_NAME and s.get('running'):
   result=script_rpc(ip,'Script.Eval',{'id':s['id'],'code':'JSON.stringify(getEffectState())'})
   return json.loads(result['result'])
 if any(s.get('running') for s in scripts):return {'name':'Dance (precedente)','changes':None}
 return {'name':None}

music_devices={}
music_guard=threading.RLock()

def stop_music_device(ip):
 with music_guard:music_devices.pop(ip,None)

def music_start(ips):
 if not ips:raise ValueError('Seleziona almeno una lampadina')
 token=secrets.token_urlsafe(24)
 def begin(ip):
  with device_lock(ip):
   stop_music_device(ip);stop_native(ip)
   if is_tapo(ip):tapo_adapter.request(ip,'set',{'on':True})
   with music_guard:music_devices[ip]={'token':token,'last':time.monotonic(),'seq':-1}
 batch=device_batch(ips,begin)
 if not batch['applied']:raise ValueError('Nessuna lampada disponibile per la musica')
 active=batch['applied']
 return {'token':token,'ips':active,'interval_ms':140,'device_intervals':{ip:500 if is_tapo(ip) else 140 for ip in active},'skipped':batch['skipped'],'errors':batch['errors']}

def music_stop(token):
 for ip in list(D['devices']):
  with device_lock(ip):
   with music_guard:
    if music_devices.get(ip,{}).get('token')==token:music_devices.pop(ip,None)

def music_frame(x):
 token=x.get('token');seq=x.get('seq');rgb=x.get('rgb');brightness=x.get('brightness')
 if not isinstance(token,str) or not isinstance(seq,int) or isinstance(seq,bool) or seq<0:raise ValueError('Sessione musicale non valida')
 if not isinstance(rgb,list) or len(rgb)!=3 or any(not isinstance(v,int) or isinstance(v,bool) or not 0<=v<=255 for v in rgb):raise ValueError('Colore musicale non valido')
 if not isinstance(brightness,int) or isinstance(brightness,bool) or not 1<=brightness<=100:raise ValueError('Luminosità musicale non valida')
 active=[];errors={}
 requested=x.get('ips',list(D['devices']))
 if not isinstance(requested,list) or any(not isinstance(ip,str) or ip not in D['devices'] for ip in requested):raise ValueError('Destinatari musicali non validi')
 for ip in dict.fromkeys(requested):
  with device_lock(ip):
   with music_guard:
    state=music_devices.get(ip)
    if not state or state['token']!=token:continue
    if time.monotonic()-state['last']>15:
     music_devices.pop(ip,None);continue
    if seq<=state['seq']:continue
    state.update(seq=seq,last=time.monotonic())
   try:
    params={'on':True,'mode':'rgb','rgb':rgb,'brightness':brightness}
    if is_tapo(ip):tapo_adapter.request(ip,'music',params)
    else:rpc(ip,'RGBCCT.Set',{'id':0,**params})
    active.append(ip)
   except Exception as e:
    stop_music_device(ip);errors[ip]=str(e)
 return {'ok':True,'active':active,'errors':errors}

def stopfx(room,ips=None):
 for ip in (ips if ips is not None else D['rooms'].get(room,[])):
  with device_lock(ip):
   stop_music_device(ip);stop_native(ip)
 effect_errors.pop(room,None)

def manual_set(ip,params):
 params=dict(params)
 if 'mode' in params and 'on' not in params and 'brightness' not in params:
  params['on']=True
 with device_lock(ip):
  stop_music_device(ip)
  if is_tapo(ip):return tapo_adapter.request(ip,'set',params)
  stop_native(ip)
  return rpc(ip,'RGBCCT.Set',{'id':0,**params})

def startfx(room,name,ips):
 if name not in EFFECTS:raise ValueError('Effetto sconosciuto')
 if not ips:raise ValueError('Seleziona almeno una lampada')
 for ip in ips:
  device_lock(ip)
  if name not in supported_effects(ip):raise ValueError(name+' non disponibile su '+D['devices'][ip].get('name',ip)+'. Tapo supporta Party e Relax.')
 started=[]
 try:
  for ip in dict.fromkeys(ips):
   with device_lock(ip):
    stop_music_device(ip)
    if is_tapo(ip):
     started.append(ip)
     state=tapo_adapter.request(ip,'effect',{'name':name})
     if state.get('effect')!=name:raise RuntimeError('Effetto Tapo non confermato')
     continue
    sid=install_native(ip)
    stop_native(ip)
    started.append(ip)
    script_rpc(ip,'Script.Start',{'id':sid})
    script_rpc(ip,'Script.Eval',{'id':sid,'code':'selectEffect('+json.dumps(name)+')'})
    deadline=time.monotonic()+2
    while True:
     result=script_rpc(ip,'Script.Eval',{'id':sid,'code':'JSON.stringify(getEffectState())'})
     st=json.loads(result['result'])
     if st.get('lastError'):raise RuntimeError(str(st['lastError']))
     if st.get('name')==name and st.get('changes',0)>0:break
     if time.monotonic()>deadline:raise RuntimeError('Primo cambio colore non confermato')
     time.sleep(.1)
  effect_errors.pop(room,None)
 except Exception as e:
  for ip in started:
   try:
    with device_lock(ip):stop_native(ip)
   except Exception:pass
  effect_errors[room]=str(e)
  raise

# Storico locale: un campione ogni 15 secondi, conservato in SQLite.
DB=ROOT/'luci_usage.sqlite3'
POLL_SECONDS=15
MAX_GAP=45

def dbconnect():
 c=sqlite3.connect(DB,timeout=10)
 c.row_factory=sqlite3.Row
 return c

def init_usage():
 with dbconnect() as c:
  c.execute('CREATE TABLE IF NOT EXISTS samples (ip TEXT, ts REAL, output INTEGER, power REAL, energy REAL, PRIMARY KEY(ip,ts))')
  c.execute('CREATE TABLE IF NOT EXISTS intervals (ip TEXT, start REAL, end REAL, on_seconds REAL, wh REAL, covered REAL)')
  c.execute('CREATE INDEX IF NOT EXISTS intervals_ip_end ON intervals(ip,end)')
  c.execute('CREATE TABLE IF NOT EXISTS shelly_history (ip TEXT PRIMARY KEY,ts REAL,data TEXT)')
  c.execute('CREATE TABLE IF NOT EXISTS native_usage (ip TEXT PRIMARY KEY,date TEXT,ts REAL,data TEXT)')
  c.execute('CREATE TABLE IF NOT EXISTS native_samples (ip TEXT,ts REAL,date TEXT,wh REAL,PRIMARY KEY(ip,ts))')
  c.execute('CREATE TABLE IF NOT EXISTS native_daily (ip TEXT,date TEXT,wh REAL,on_seconds REAL,ts REAL,PRIMARY KEY(ip,date))')
  c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY,value REAL)')

def store_native_usage(ip,usage,ts=None):
 ts=time.time() if ts is None else ts
 date=datetime.date.fromisoformat(usage['date'])
 today=usage['periods']['today']
 with dbconnect() as c:
  sample_ts=usage.get('sampled_at',ts)
  c.execute('INSERT OR IGNORE INTO native_samples VALUES (?,?,?,?)',(ip,sample_ts,str(date),today.get('wh')))
  c.execute('DELETE FROM native_samples WHERE ts<?',(ts-90*86400,))
  c.execute('INSERT OR REPLACE INTO native_usage VALUES (?,?,?,?)',(ip,str(date),ts,json.dumps(usage)))
  c.execute('INSERT OR REPLACE INTO native_daily VALUES (?,?,?,?,?)',(ip,str(date),today.get('wh'),today.get('on_seconds'),ts))
  c.execute('DELETE FROM native_daily WHERE date<?',(str(date-datetime.timedelta(days=90)),))

def native_history(ip,days):
 with dbconnect() as c:
  latest=c.execute('SELECT * FROM native_usage WHERE ip=?',(ip,)).fetchone()
  if not latest:return None
  summary=json.loads(latest['data']);summary['updated_at']=latest['ts']
  date=datetime.date.fromisoformat(latest['date'])
  dates=[date-datetime.timedelta(days=i) for i in reversed(range(days))]
  rows={r['date']:r for r in c.execute('SELECT * FROM native_daily WHERE ip=? AND date>=?',(ip,str(dates[0])))}
  daily=[]
  for d in dates:
   r=rows.get(str(d))
   daily.append({'date':str(d),'wh':r['wh'] if r else None,'on_seconds':r['on_seconds'] if r else None,'known':bool(r),'updated_at':r['ts'] if r else None})
 return {'summary':summary,'daily':daily}

def valid_number(x):
 return float(x) if isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and x>=0 else None

def record_usage(ip,status,ts=None):
 ts=time.time() if ts is None else ts
 if status.get('native_usage'):store_native_usage(ip,status['native_usage'],ts)
 if not isinstance(status.get('output'),bool):raise ValueError('Stato lampadina non valido')
 power=valid_number(status.get('apower'))
 energy=valid_number((status.get('aenergy') or {}).get('total'))
 with dbconnect() as c:
  prev=c.execute('SELECT * FROM samples WHERE ip=? ORDER BY ts DESC LIMIT 1',(ip,)).fetchone()
  if prev and ts>prev['ts']:
   dt=ts-prev['ts'];covered=dt if dt<=MAX_GAP else 0
   wh=None
   if covered:
    if energy is not None and prev['energy'] is not None and energy>=prev['energy']:
     wh=energy-prev['energy']
    elif power is not None and prev['power'] is not None:
     wh=(power+prev['power'])/2*dt/3600
   c.execute('INSERT INTO intervals VALUES (?,?,?,?,?,?)',(ip,prev['ts'],ts,covered if prev['output'] else 0,wh,covered))
  c.execute('INSERT OR IGNORE INTO samples VALUES (?,?,?,?,?)',(ip,ts,int(status['output']),power,energy))
  c.execute('DELETE FROM samples WHERE ts<?',(ts-90*86400,))
  c.execute('DELETE FROM intervals WHERE end<?',(ts-90*86400,))

def quarter_energy(ip,date=None,now=None):
 now=time.time() if now is None else now
 date=datetime.date.fromisoformat(date) if date else datetime.datetime.fromtimestamp(now).date()
 start=datetime.datetime.combine(date,datetime.time()).timestamp()
 end=datetime.datetime.combine(date+datetime.timedelta(days=1),datetime.time()).timestamp()
 bins=[]
 t=start
 while t<end:
  stop=min(t+900,end)
  bins.append({'start':t,'end':stop,'wh':None,'coverage_seconds':0,'status':'future' if t>=now else 'missing'})
  t=stop
 with dbconnect() as c:
  if is_tapo(ip):
   # Un campione autentico per lettura, non per refresh della pagina.
   samples=c.execute('SELECT * FROM native_samples WHERE ip=? AND ts>=? AND ts<=? ORDER BY ts',(ip,start-120,min(end+120,now))).fetchall()
   rows=[]
   for left,right in zip(samples,samples[1:]):
    dt=right['ts']-left['ts']
    if 0<dt<=120 and left['date']==right['date'] and left['wh'] is not None and right['wh'] is not None and right['wh']>=left['wh']:
     rows.append({'start':left['ts'],'end':right['ts'],'wh':right['wh']-left['wh']})
  else:
   rows=c.execute('SELECT start,end,wh FROM intervals WHERE ip=? AND end>? AND start<? AND covered>0 AND wh IS NOT NULL',(ip,start,min(end,now))).fetchall()
 for r in rows:
  span=r['end']-r['start']
  if span<=0:continue
  first=max(0,int((r['start']-start)//900));last=min(len(bins)-1,int((r['end']-start)//900))
  for i in range(first,last+1):
   b=bins[i];overlap=max(0,min(b['end'],r['end'],now)-max(b['start'],r['start']))
   if not overlap:continue
   b['wh']=(b['wh'] or 0)+r['wh']*overlap/span
   b['coverage_seconds']+=overlap
 for b in bins:
  expected=max(0,min(b['end'],now)-b['start'])
  if b['wh'] is not None:b['status']='complete' if b['coverage_seconds']>=expected-.01 else 'partial'
 return {'date':str(date),'minutes':15,'bins':bins,'source':'tapo' if is_tapo(ip) else 'shelly'}

def usage_history(ip,days=7,now=None,interval_date=None,include_quarters=True):
 now=time.time() if now is None else now
 today=datetime.datetime.fromtimestamp(now).date()
 dates=[today-datetime.timedelta(days=i) for i in reversed(range(days))]
 edges=[datetime.datetime.combine(d,datetime.time()).timestamp() for d in dates]
 end=datetime.datetime.combine(today+datetime.timedelta(days=1),datetime.time()).timestamp()
 daily=[{'date':str(d),'on_seconds':0,'wh':0,'coverage_seconds':0,'unknown_seconds':0,'energy_seconds':0} for d in dates]
 bounds=edges+[end]
 with dbconnect() as c:
  rows=c.execute('SELECT * FROM intervals WHERE ip=? AND end>? AND start<?',(ip,edges[0],now)).fetchall()
  for r in rows:
   span=r['end']-r['start']
   if span<=0:continue
   for i,day in enumerate(daily):
    overlap=max(0,min(r['end'],bounds[i+1],now)-max(r['start'],bounds[i]))
    if not overlap:continue
    fraction=overlap/span
    day['on_seconds']+=r['on_seconds']*fraction
    day['coverage_seconds']+=r['covered']*fraction
    if r['wh'] is not None:
     day['wh']+=r['wh']*fraction;day['energy_seconds']+=overlap
  for i,day in enumerate(daily):
   day['unknown_seconds']=max(0,min(bounds[i+1],now)-bounds[i]-day['coverage_seconds'])
  latest=c.execute('SELECT * FROM samples WHERE ip=? ORDER BY ts DESC LIMIT 1',(ip,)).fetchone()
  points=[dict(r) for r in c.execute('SELECT ts,power FROM samples WHERE ip=? AND ts>=? ORDER BY ts',(ip,now-86400))]
  rate=c.execute("SELECT value FROM settings WHERE key='tariff'").fetchone()
 result={'daily':daily,'latest':dict(latest) if latest else None,'points':points,'tariff':rate[0] if rate else 0.30,'now':now,'poll_seconds':POLL_SECONDS}
 native=native_history(ip,days) if is_tapo(ip) else None
 if native:result['native']=native
 if include_quarters:result['quarters']=quarter_energy(ip,interval_date,now)
 if not is_tapo(ip):
  remote=shelly_device_history(ip,days,interval_date,now)
  if remote:
   if not include_quarters:remote.pop('quarters',None);remote.pop('two_hours',None)
   result.update(remote)
  else:result['logger_error']=usage_errors.get(ip,'Monitoraggio interno in attesa di installazione')
 return result

def monitor_usage():
 while True:
  started=time.monotonic()
  for ip in list(D['devices']):
   if ip in disabled_devices:continue
   try:
    record_usage(ip,device_status(ip))
    if not is_tapo(ip) and ip not in disabled_devices:sync_shelly_usage(ip)
   except Exception as e:print('Monitoraggio',ip,str(e),flush=True)
  time.sleep(max(1,POLL_SECONDS-(time.monotonic()-started)))

class H(SimpleHTTPRequestHandler):
 def end_headers(self):
  self.send_header("Cache-Control","no-store")
  super().end_headers()
 def translate_path(self,path):
  path=urllib.parse.urlsplit(path).path
  base=ROOT/"static" if (ROOT/"static"/"index.html").exists() else ROOT
  return str(base/("index.html" if path=="/" else path.lstrip("/")))
 def sendj(self,x,code=200):
  b=json.dumps(x).encode();self.send_response(code);self.send_header("Content-Type","application/json");self.send_header("Content-Length",len(b));self.end_headers();self.wfile.write(b)
 def do_GET(self):
  parsed=urllib.parse.urlsplit(self.path)
  if parsed.path=='/api/usage':
   q=urllib.parse.parse_qs(parsed.query);ip=q.get('ip',[''])[0]
   if ip not in D['devices']:return self.sendj({'error':'Lampadina sconosciuta'},404)
   try:
    days=int(q.get('days',['7'])[0])
    if days not in (1,7,30):raise ValueError('Periodo non valido')
    if not is_tapo(ip) and ip not in disabled_devices:sync_shelly_usage(ip)
    return self.sendj(usage_history(ip,days,interval_date=q.get('date',[None])[0]))
   except Exception as e:return self.sendj({'error':str(e)},400)
  if parsed.path=="/api/state":
   if urllib.parse.parse_qs(parsed.query).get('retry')==['1']:reset_disabled()
   out={"data":D,"effects":list(EFFECTS),"effect_errors":effect_errors}
   for ip in D["devices"]:
    try:
     out["devices"]=out.get("devices",{});out["devices"][ip]=device_status(ip)
     if out["devices"][ip].get("native_usage"):store_native_usage(ip,out["devices"][ip]["native_usage"])
    except Exception as e:out.setdefault("devices",{})[ip]={"error":str(e)}
   out['native_effects']={}
   for ip in D['devices']:
    if ip in disabled_devices:
     out['native_effects'][ip]={'name':None};continue
    try:
     out['native_effects'][ip]={'name':out.get('devices',{}).get(ip,{}).get('effect'),'provider':'tapo'} if is_tapo(ip) else native_state(ip)
    except Exception as e:out['native_effects'][ip]={'name':None,'error':str(e)}
   with music_guard:
    out['music_active']=[ip for ip,state in music_devices.items() if time.monotonic()-state['last']<=15]
   out['disabled_devices']=dict(disabled_devices)
   out['tapo_auth']=tapo_adapter.auth_status()
   out['effects_by_device']={ip:supported_effects(ip) for ip in D['devices']}
   out['usage']={ip:usage_history(ip,1,include_quarters=False) for ip in D['devices']}
   return self.sendj(out)
  if parsed.path not in ('/','/index.html'):return self.sendj({'error':'Non trovato'},404)
  return super().do_GET()
 def do_POST(self):
  n=int(self.headers.get("Content-Length",0));x=json.loads(self.rfile.read(n) or b"{}")
  try:
   if self.path=='/api/music/start':return self.sendj({'ok':True,**music_start(x.get('ips',[]))})
   elif self.path=='/api/music/frame':return self.sendj(music_frame(x))
   elif self.path=='/api/music/stop':music_stop(x.get('token'))
   elif self.path=='/api/tapo/auth':
    tapos=[ip for ip in D['devices'] if is_tapo(ip)]
    if not tapos:raise ValueError('Nessuna Tapo configurata')
    with device_lock(tapos[0]):tapo_adapter.configure(tapos[0],x.get('username',''),x.get('password',''))
   elif self.path=='/api/usage/tariff':
    rate=valid_number(x.get('tariff'))
    if rate is None or rate>100:raise ValueError('Tariffa non valida')
    with dbconnect() as c:c.execute("INSERT OR REPLACE INTO settings VALUES ('tariff',?)",(rate,))
   elif self.path=="/api/set":
    return self.sendj(device_batch(x["ips"],lambda ip:manual_set(ip,x["params"])))
   elif self.path=="/api/effect/start":return self.sendj(device_batch(x["ips"],lambda ip:startfx(x["room"],x["name"],[ip])))
   elif self.path=="/api/effect/stop":return self.sendj(device_batch(x.get("ips",D["rooms"].get(x["room"],[])),lambda ip:stopfx(x["room"],[ip])))
   elif self.path=="/api/scene/save":
    sc={}
    def capture(ip):
     st=device_status(ip);sc[ip]={k:st[k] for k in ("output","mode","brightness","rgb","ct") if k in st}
    result=device_batch(x["ips"],capture)
    if sc:
     # Keep existing values for excluded lamps when overwriting a saved scene.
     previous=D["scenes"].setdefault(x["room"],{}).get(x["name"],{})
     D["scenes"][x["room"]][x["name"]]={**previous,**sc};save()
    return self.sendj(result)
   elif self.path=="/api/scene/apply":
    sc=D["scenes"].get(x["room"],{}).get(x["name"],{})
    def apply(ip):
     st=sc[ip]
     params={"on":st.get("output",True),**{k:st[k] for k in ("mode","brightness","rgb","ct") if k in st}}
     manual_set(ip,params)
    return self.sendj(device_batch(sc,apply))
   self.sendj({"ok":True})
  except Exception as e:self.sendj({"error":str(e)},500)
if __name__=="__main__":
 integrate_tapo_config()
 init_usage()
 threading.Thread(target=monitor_usage,daemon=True,name="usage-monitor").start()
 server=ThreadingHTTPServer(("0.0.0.0",8000),H)
 print_addresses(8000, D["devices"])
 print("Effetti autonomi Shelly: script unico, controllo via Script.Eval")
 try:
  server.serve_forever()
 except KeyboardInterrupt:
  print("\nLuci di Casa arrestato.",flush=True)
 finally:
  server.server_close()

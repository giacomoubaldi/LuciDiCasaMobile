// Luci di Casa: device-side history v1. Firmware >= 1.5.
// 11 persistent keys, each <= 1024 bytes. No light control calls.
let daily = [], week = [], quarters = null;
let previous = null, lastSave = 0, error = null, ready = false;
let alphabet = '0123456789abcdefghijklmnopqrstuvwxyz';
// Avoid Array.concat/slice: not present on some Shelly interpreters.
function portion(a, start, end) {
  let result = [];
  for (let i = start; i < end && i < a.length; i++) result.push(a[i]);
  return result;
}
function joined(a, b) {
  let result = portion(a, 0, a.length);
  for (let i = 0; i < b.length; i++) result.push(b[i]);
  return result;
}
function enc(n) {
  n = Math.max(0, Math.round(n));
  if (n === 0) return '0';
  let s = '';
  while (n > 0) { s = alphabet[n % 36] + s; n = Math.floor(n / 36); }
  return s;
}
function dec(s) {
  let n = 0;
  for (let i = 0; i < s.length; i++) n = n * 36 + alphabet.indexOf(s[i]);
  return n;
}
function unpack(s) {
  if (!s) return [0, 0, 0];
  let a = s.split('.');
  return [dec(a[0]), dec(a[1]), dec(a[2])];
}
function add(s, e, on, coverage) {
  let a = unpack(s);
  return enc(a[0] + e) + '.' + enc(a[1] + on) + '.' + enc(a[2] + coverage);
}
function load(key) {
  let s = Script.storage.getItem(key);
  if (s === null) return null;
  return JSON.parse(s);
}
function write(key, value) {
  let s = JSON.stringify(value);
  if (s.length > 1024) throw new Error('History record too large: ' + key);
  if (Script.storage.getItem(key) !== s) Script.storage.setItem(key, s);
}
function save() {
  try {
    if (!quarters) return;
    // Fine data first; reboot recovery rebuilds the current day summaries.
    write('Q0', {d: quarters.d, o: quarters.o, t: quarters.t, v: portion(quarters.v,0,48)});
    write('Q1', {d: quarters.d, o: quarters.o, t: quarters.t, v: portion(quarters.v,48,96)});
    for (let i = 0; i < week.length; i++) write('W' + i, week[i]);
    write('D0', portion(daily,0,15));
    write('D1', portion(daily,15,30));
    lastSave = quarters.t;
    error = null;
  } catch (e) { error = '' + e; }
}
function empty(n) {
  let a = [];
  for (let i = 0; i < n; i++) a.push('');
  return a;
}
function sum(a) {
  let total = '';
  for (let i = 0; i < a.length; i++) {
    if (a[i]) { let b = unpack(a[i]); total = add(total, b[0], b[1], b[2]); }
  }
  return total;
}
function rebuildToday() {
  if (!quarters) return;
  let idx = quarters.d % 30;
  daily[idx] = {d: quarters.d, v: sum(quarters.v)};
  let w = {d: quarters.d, o: quarters.o, v: empty(12)};
  for (let i = 0; i < 96; i++) {
    if (quarters.v[i]) {
      let a = unpack(quarters.v[i]), j = Math.floor(i / 8);
      w.v[j] = add(w.v[j], a[0], a[1], a[2]);
    }
  }
  week[quarters.d % 7] = w;
}
function clock(sys) {
  if (!sys || !sys.unixtime || sys.unixtime < 1700000000 || !sys.time) return null;
  let hm = sys.time.split(':'), local = Number(hm[0]) * 60 + Number(hm[1]);
  let utc = Math.floor(sys.unixtime / 60) % 1440, diff = local - utc;
  if (diff < -720) diff += 1440;
  if (diff > 840) diff -= 1440;
  let offset = diff * 60;
  return {t: sys.unixtime, u: sys.uptime, o: offset, d: Math.floor((sys.unixtime + offset) / 86400)};
}
function roll(c) {
  if (quarters && quarters.d !== c.d) save();
  if (!quarters || quarters.d !== c.d) quarters = {d: c.d, o: c.o, t: c.t, v: empty(96)};
  quarters.o = c.o;
  quarters.t = c.t;
  if (!daily[c.d % 30] || daily[c.d % 30].d !== c.d) daily[c.d % 30] = {d: c.d, v: ''};
  if (!week[c.d % 7] || week[c.d % 7].d !== c.d) week[c.d % 7] = {d: c.d, o: c.o, v: empty(12)};
}
function accumulate(c, start, stop, energy, on) {
  // Normally one bucket, two when a poll crosses a quarter-hour boundary.
  let cursor = start;
  while (cursor < stop) {
    let local = cursor + c.o, day = Math.floor(local / 86400);
    let q = Math.floor((local % 86400) / 900);
    let next = Math.min(stop, (Math.floor(local / 900) + 1) * 900 - c.o);
    let fraction = (next - cursor) / (stop - start), e = energy * fraction;
    let dc = {d: day, o: c.o, t: next};
    roll(dc);
    quarters.v[q] = add(quarters.v[q], e, on * fraction, next - cursor);
    let w = week[day % 7], j = Math.floor(q / 8);
    w.v[j] = add(w.v[j], e, on * fraction, next - cursor);
    daily[day % 30].v = add(daily[day % 30].v, e, on * fraction, next - cursor);
    cursor = next;
  }
}
function sample() {
  if (!ready) return;
  let c = clock(Shelly.getComponentStatus('sys'));
  let light = Shelly.getComponentStatus('rgbcct:0');
  if (!c || !light || !light.aenergy || typeof light.aenergy.total !== 'number') {
    error = 'Clock or RGBCCT energy unavailable'; previous = null; return;
  }
  let energy = light.aenergy.total;
  if (previous) {
    let dt = c.t - previous.t, du = c.u - previous.u;
    if (dt > 0 && dt <= 30 && Math.abs(dt - du) <= 2 && c.o === previous.o && energy >= previous.e) {
      accumulate(c, previous.t, c.t, (energy - previous.e) * 1000000, previous.on ? dt : 0);
    }
  }
  roll(c);
  previous = {t:c.t, u:c.u, o:c.o, e:energy, on:light.output === true};
  // Flash checkpoint every 15 minutes; current readings are available in RAM.
  if (Math.floor(c.t / 900) !== Math.floor(lastSave / 900)) save();
}
function getUsageStatus() {
  sample();
  return {schema:1, ready:ready, error:error, day:quarters ? quarters.d : null,
    ts:quarters ? quarters.t : null, saved_at:lastSave, retention:{daily:30,two_hours:7,quarters:1}};
}
function getUsagePart(kind, index) {
  sample();
  if (kind === 'daily') return portion(daily,index * 15,(index + 1) * 15);
  if (kind === 'week') return week[index];
  if (kind === 'quarters') return quarters ? {d:quarters.d,o:quarters.o,t:quarters.t,v:portion(quarters.v,index * 48,(index + 1) * 48)} : null;
  return null;
}
try {
  if (typeof Script.storage === 'undefined') throw new Error('Firmware >= 1.5 required');
  daily = joined(load('D0') || [],load('D1') || []);
  while (daily.length < 30) daily.push(null);
  for (let i = 0; i < 7; i++) week.push(load('W' + i));
  let a = load('Q0'), b = load('Q1');
  if (a && b && a.d === b.d) {
    quarters = {d:a.d,o:a.o,t:Math.min(a.t,b.t),v:joined(a.v,b.v)};
    lastSave = quarters.t;
    rebuildToday();
  }
  ready = true;
  sample();
  Timer.set(10000, true, sample);
  Shelly.addStatusHandler(function(s) {
    if (s.component === 'rgbcct:0' && s.delta && typeof s.delta.output !== 'undefined') sample();
  });
} catch (e) { error = '' + e; }

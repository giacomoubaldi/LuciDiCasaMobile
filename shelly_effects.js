// Luci di Casa: tutti gli effetti autonomi.
let FX = {"Happy":[2.2,[[255,70,20],[255,180,0],[40,220,90],[40,150,255],[220,60,220]],[55,90],"cycle"],"Dance":[0.55,[[255,0,40],[0,90,255],[170,0,255],[0,255,130],[255,80,0]],[65,100],"cycle"],"Relax":[5,[[255,85,25],[255,130,35],[230,70,65],[190,70,130]],[20,45],"cycle"],"Sunset":[4,[[255,150,35],[255,95,20],[255,55,35],[210,45,75],[130,35,100]],[30,65],"cycle"],"Ocean":[3.3,[[0,80,255],[0,160,255],[0,220,210],[30,100,220],[40,210,180]],[35,70],"cycle"],"Aurora":[3,[[20,255,130],[0,220,220],[40,100,255],[150,40,255],[60,220,150]],[40,75],"cycle"],"Fireplace":[0.38,[[255,45,0],[255,75,0],[255,110,10],[255,145,25]],[18,58],"random"],"Pulse":[0.35,[[100,30,255]],[15,85],"pulse"],"Party":[0.4,[[255,0,70],[255,120,0],[0,255,100],[0,150,255],[100,0,255],[255,0,220]],[70,100],"random"],"Candle":[0.45,[[255,80,8],[255,105,15],[255,125,25]],[12,32],"random"]};
let active = null;
let step = 0;
let changes = 0;
let busy = false;
let lastError = null;
let timer = null;
let generation = 0;
function stopEffect() {
  generation++;
  if (timer !== null) Timer.clear(timer);
  timer = null;
  active = null;
}
function selectEffect(name) {
  if (!FX[name]) return false;
  stopEffect();
  active = name;
  step = 0;
  changes = 0;
  lastError = null;
  if (!busy) tickEffect();
  return true;
}
function getEffectState() {
  return {name:active, changes:changes, busy:busy, lastError:lastError};
}
function scheduleEffect(delay) {
  if (active !== null) timer = Timer.set(delay, false, tickEffect);
}
function tickEffect() {
  timer = null;
  if (active === null || busy) return;
  let f = FX[active];
  let color = f[1][step % f[1].length];
  let b = f[2][0] + Math.floor(Math.random() * (f[2][1] - f[2][0] + 1));
  if (f[3] === "random") color = f[1][Math.floor(Math.random() * f[1].length)];
  if (f[3] === "pulse") {
    color = f[1][0];
    b = Math.floor(f[2][0] + (f[2][1] - f[2][0]) * (0.5 + 0.5 * Math.sin(step * 0.38)));
  }
  let g = generation;
  busy = true;
  Shelly.call("RGBCCT.Set", {
    id:0, on:true, mode:"rgb", rgb:color, brightness:b,
    transition_duration:0.5
  }, function(result, code, message) {
    busy = false;
    if (g !== generation) {
      if (active !== null) scheduleEffect(1);
      return;
    }
    if (code !== 0) {
      lastError = {code:code,message:message};
      active = null;
      return;
    }
    changes++;
    step++;
    scheduleEffect(Math.max(550, f[0] * 1000));
  });
}
// All'avvio resta inattivo: l'app seleziona l'effetto con Script.Eval.

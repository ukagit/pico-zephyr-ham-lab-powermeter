/* Offline regression: separate axes, mW/W conversion and visibility. */
const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'..');
class N{constructor(tag){this.tag=tag;this.attrs={};this.children=[];this.style={};}setAttribute(k,v){this.attrs[k]=v;}removeAttribute(k){delete this.attrs[k];}append(...v){this.children.push(...v);}replaceChildren(){this.children=[];}}
const els={directionplot:new N('svg'),a2plot:new N('svg'),directionlegend:new N('div'),a2legend:new N('div'),curvestatus:new N('p')};
const data=JSON.parse(fs.readFileSync(path.join(root,'docs/calibration/1n4148_50ohm_1mhz.json')));
const old=JSON.parse(fs.readFileSync(path.join(root,'docs/calibration/curves-v0.1.32.json')));
const ctx={document:{createElementNS:(ns,t)=>new N(t),createElement:t=>new N(t),createTextNode:text=>({text})},el:id=>els[id],Set,Math,Number,Date,data};
vm.createContext(ctx);
const html=fs.readFileSync(path.join(root,'web/hamlab.html'),'utf8');
const code=html.slice(html.indexOf('const curveColors='),html.indexOf('</script>')).replace(/loadCurves\(\);\s*$/,'');
vm.runInContext(code,ctx);vm.runInContext('curveData=data;drawCurves();',ctx);
const byTag=(id,tag)=>els[id].children.filter(n=>n.tag===tag);
assert.equal(byTag('directionplot','polyline').length,3);
assert.equal(byTag('a2plot','polyline').length,1);
assert.equal(byTag('a2plot','circle').length,17);
assert(byTag('a2plot','text').some(n=>n.textContent==='Leistung / mW'));
assert(byTag('directionplot','text').some(n=>n.textContent==='Leistung / W'));
assert.equal(byTag('a2plot','text')[11].textContent,'250'); // upper tick
const last=byTag('a2plot','circle').at(-1);
assert(Math.abs(last.attrs.cy-(345-211.6/250*310))<1e-9);
const direction=JSON.stringify(els.directionplot.children);
data.curves[3]=old.curves[3];vm.runInContext('drawCurves();',ctx);
assert.equal(JSON.stringify(els.directionplot.children),direction);
assert(byTag('a2plot','text').some(n=>n.textContent==='Leistung / W'));
vm.runInContext("visibleCurves.delete('current');drawCurves();",ctx);
assert.equal(byTag('a2plot','polyline').length,0);
assert(byTag('a2plot','text').some(n=>n.textContent==='Keine Kurve eingeblendet'));
for(const plot of ['a2plot','directionplot'])assert(!/NaN|Infinity/.test(JSON.stringify(els[plot].children)));
console.log('Separate plots verified: 250 mW scale, independent W axes, 17 A2 points, profile change and hide.');

for(const id of ['a2dbm','a2power','a2scale','a2peak','a2fill','a2hold','a2bar','currentcoupler','a2quality',...([25,50,75,100].map(n=>'a2tick'+n))])els[id]=new N('div');
vm.runInContext(html.slice(html.indexOf('let lastA2='),html.indexOf('function clear(){')),ctx);
ctx.reading={valid:true,power_50ohm_w:.2116,peak_w:.22,max_w:.2116,master:'scope',calibration_frequency_hz:1000000};
vm.runInContext("drawA2(reading,'diode_1mhz');",ctx);
assert.equal(els.a2dbm.textContent,'23,26 dBm');assert(els.a2power.textContent.includes('mW'));assert.equal(els.a2scale.textContent,'250 mW');
assert(Math.abs(parseFloat(els.a2fill.style.width)-84.64)<1e-9);assert.equal(els.a2hold.style.left,'88%');
ctx.reading={valid:true,power_50ohm_w:60,peak_w:70,max_w:83.346,master:'A0',calibration_frequency_hz:7100000};
vm.runInContext("drawA2(reading,'current_100watt');",ctx);
assert.equal(els.a2scale.textContent,'100 W');assert.equal(els.a2fill.style.width,'60%');
ctx.reading={valid:false,power_50ohm_w:null,peak_w:null,max_w:.2116,quality:'outside_calibrated_range',master:'scope',calibration_frequency_hz:1000000};
vm.runInContext('drawA2(reading);',ctx);assert.equal(els.a2fill.style.width,'0%');assert.equal(els.a2hold.style.display,'none');
assert(els.a2quality.textContent.includes('außerhalb'));vm.runInContext('drawA2(null);',ctx);
assert.equal(els.a2dbm.textContent,'-- dBm');assert(!/NaN|undefined/.test(els.a2power.textContent));
console.log('A2 bar verified: mW/W autoscale, independent hold marker, invalid and offline states.');

const CITIES={London:[51.5074,-0.1278],Birmingham:[52.4862,-1.8904],Manchester:[53.4808,-2.2426],Glasgow:[55.8642,-4.2518],Leeds:[53.8008,-1.5491],Liverpool:[53.4084,-2.9916],Bristol:[51.4545,-2.5879],Reading:[51.4551,-0.9781],Sheffield:[53.3811,-1.4701],Cardiff:[51.4816,-3.1791],Edinburgh:[55.9533,-3.1883],Newcastle:[54.9783,-1.6178],Nottingham:[52.9548,-1.1581],Leicester:[52.6369,-1.1398],Coventry:[52.4068,-1.5197],Oxford:[51.7520,-1.2577],Cambridge:[52.2053,0.1218],Brighton:[50.8225,-0.1372],Southampton:[50.9097,-1.4044],Portsmouth:[50.8198,-1.0880],Plymouth:[50.3755,-4.1427],Norwich:[52.6309,1.2974],Exeter:[50.7184,-3.5339],York:[53.9590,-1.0815],Aberdeen:[57.1497,-2.0943],Swansea:[51.6214,-3.9436],MiltonKeynes:[52.0406,-0.7594],Luton:[51.8787,-0.4200],Blackpool:[53.8175,-3.0357],Middlesbrough:[54.5742,-1.2348],Wolverhampton:[52.5862,-2.1280],Derby:[52.9225,-1.4746],Stoke:[53.0027,-2.1794],Preston:[53.7632,-2.7031],Swindon:[51.5558,-1.7797],Slough:[51.5105,-0.5950],Bath:[51.3758,-2.3599],Dundee:[56.4620,-2.9707],Chelmsford:[51.7356,0.4686],Worcester:[52.1936,-2.2216],Hull:[53.7676,-0.3274],Bolton:[53.5769,-2.4282],Wigan:[53.5451,-2.6325],Maidstone:[51.2704,0.5227],Canterbury:[51.2802,1.0789],Inverness:[57.4778,-4.2247],Carlisle:[54.8925,-2.9329],Chester:[53.1934,-2.8931],Wrexham:[53.0465,-2.9916],Newbury:[51.4014,-1.3231],Basingstoke:[51.2665,-1.0924],Guildford:[51.2362,-0.5704],Watford:[51.6565,-0.3903],Croydon:[51.3762,-0.0982],Dartford:[51.4462,0.2169],Colchester:[51.8959,0.8919],Ipswich:[52.0567,1.1482],Peterborough:[52.5695,-0.2405],Lincoln:[53.2307,-0.5407],Gloucester:[51.8642,-2.2444]};
const tips=['Check tyre pressure when tyres are cold for the most accurate reading.','Using a handheld phone while driving can mean a fine and penalty points.','Smooth acceleration usually saves more fuel than late braking.','Rapid EV charging is often fastest between about 20% and 80%.','Remove unused roof bars to reduce drag and fuel use.','Clean Air Zone rules vary by city — check before entering.'];let tipI=0;function rotateTip(){const el=document.getElementById('tip-text');if(!el)return;el.textContent=tips[tipI++%tips.length]}setInterval(rotateTip,6000);rotateTip();
function savedNumber(key, fallback){const raw=localStorage.getItem(key);const v=parseFloat(raw);return Number.isFinite(v)?v:fallback}
const hasSavedLocation=localStorage.getItem('driverzLocationSet')==='1'&&localStorage.getItem('driverzLat')&&localStorage.getItem('driverzLng');
let state={
  mode:localStorage.getItem('lastMode')||'petrol',
  lat:savedNumber('driverzLat',51.4551),
  lng:savedNumber('driverzLng',-0.9781),
  radius:savedNumber('driverzRadius',5),
  label:localStorage.getItem('driverzLabel')||(hasSavedLocation?'Saved location':'Reading'),
  excludeCostco:localStorage.getItem('driverzExcludeCostco')==='1'
};
function saveLocation(){if(Number.isFinite(state.lat)&&Number.isFinite(state.lng)){localStorage.setItem('driverzLat',state.lat);localStorage.setItem('driverzLng',state.lng);localStorage.setItem('driverzLabel',state.label||'Your location');localStorage.setItem('driverzLocationSet','1')}}
function savePrefs(){localStorage.setItem('lastMode',state.mode);localStorage.setItem('driverzRadius',state.radius);localStorage.setItem('driverzExcludeCostco',state.excludeCostco?'1':'0')}
const MODES=['petrol','diesel','ev'];const MODE_LABEL={petrol:'Petrol',diesel:'Diesel',ev:'EV'};const $=id=>document.getElementById(id);
function setStatus(t){$('station-name').textContent=t}
function setActiveMode(mode){document.querySelectorAll('[data-mode]').forEach(x=>x.classList.toggle('active',x.dataset.mode===mode));const label=$('cycle-label');if(label)label.textContent=MODE_LABEL[mode]||mode;localStorage.setItem('lastMode',mode)}
function updateCyclePrice(){const cp=$('cycle-price');if(cp)cp.textContent=localStorage.getItem('lastPrice_'+state.mode)||(($('main-price')?.textContent||'--')+($('main-unit')?.textContent||''));window.dispatchEvent(new Event('driverz:price-updated'))}
function renderOtherPrices(text){const el=$('all-prices');if(!el)return;el.innerHTML='';const value=text||'Prices vary by fuel type';const parts=value.split('·').map(x=>x.trim()).filter(Boolean);if(parts.length>1){parts.forEach(part=>{const chip=document.createElement('span');chip.className='price-chip';chip.textContent=part;el.appendChild(chip)})}else{const chip=document.createElement('span');chip.className='price-chip wide';chip.textContent=value;el.appendChild(chip)}}
function formatMainPrice(d){
  const raw = d.price;
  const n = typeof raw === 'number' ? raw : parseFloat(String(raw).replace(/[^0-9.]/g,''));
  if (state.mode === 'ev' && (raw === 'FREE' || n === 0)) return {price:'FREE', unit:''};
  if (raw === 'FREE') return {price:'FREE', unit:''};
  return {price:Number.isFinite(n)?n.toFixed(1):'--', unit:d.unit||'p'};
}
function showData(d){
  const formatted = formatMainPrice(d);
  $('main-price').textContent = formatted.price;
  $('main-unit').textContent = formatted.unit;
  $('station-name').textContent=d.name||'Station found';
  $('distance').textContent=d.dist||'--';
  $('updated').textContent=d.updated?`Updated ${d.updated}`:'Updated today';
  $('hours').textContent=d.opening||'Opening times unavailable';
  $('address').textContent=d.address||state.label;
  const extra = [];
  if (d.allPrices) extra.push(d.allPrices);
  if (d.connectors) extra.push(`Connectors ${d.connectors}`);
  renderOtherPrices(extra.join(' · '));
  const maps=`https://www.google.com/maps/dir/?api=1&destination=${d.lat},${d.lng}`;
  $('directions').href=maps;
  localStorage.setItem('lastPrice_'+state.mode, $('main-price').textContent + $('main-unit').textContent);
  localStorage.setItem('lastMode', state.mode);
  saveLocation();savePrefs();updateCyclePrice()
}
async function loadFuel(){document.body.classList.add('loading');setStatus('Checking nearby prices…');setActiveMode(state.mode);savePrefs();try{const res=await fetch(`/api/fuel?lat=${state.lat}&lng=${state.lng}&mode=${state.mode}&radius=${state.radius}&excludeCostco=${state.excludeCostco}`);const data=await res.json();if(!res.ok)throw new Error(data.error||'No result');showData(data)}catch(e){setStatus(e.message||'No station found nearby');$('main-price').textContent='--';$('main-unit').textContent='';updateCyclePrice()}finally{document.body.classList.remove('loading')}}
async function geocode(q){const key=q.replace(/\s+/g,'');if(CITIES[q]||CITIES[key]){const c=CITIES[q]||CITIES[key];return {lat:c[0],lng:c[1],label:q}}const res=await fetch(`https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=gb&q=${encodeURIComponent(q)}`);const data=await res.json();if(data[0])return{lat:+data[0].lat,lng:+data[0].lon,label:q};throw new Error('Place not found')}
async function searchPlace(q, opts={}){setStatus('Finding '+q+'…');try{const g=await geocode(q);Object.assign(state,g);saveLocation();if(opts.updateUrl!==false){const url='/?city='+encodeURIComponent(q)+'#fuel-card';history.replaceState(null,'',url)}loadFuel();if(opts.scroll!==false){document.getElementById('fuel-card')?.scrollIntoView({behavior:'smooth',block:'start'})}}catch(e){setStatus(e.message)}}
function cycleMode(){const i=MODES.indexOf(state.mode);state.mode=MODES[(i+1)%MODES.length];savePrefs();loadFuel()}
function useLocation(){if(!navigator.geolocation){setStatus('Location is not available in this browser. Search manually instead.');return}setStatus('Finding your location…');navigator.geolocation.getCurrentPosition(pos=>{state.lat=pos.coords.latitude;state.lng=pos.coords.longitude;state.label='Your location';saveLocation();loadFuel()},()=>{setStatus('Location permission was not granted. Using your saved location instead.');loadFuel()},{enableHighAccuracy:false,timeout:10000,maximumAge:300000})}
function init(){if(!$('fuel-card'))return;window.DriverzFuel={cycleMode,searchPlace,useLocation};document.querySelectorAll('[data-mode]').forEach(b=>b.addEventListener('click',()=>{state.mode=b.dataset.mode;savePrefs();loadFuel()}));if($('radius')){$('radius').value=state.radius;$('radius-value').textContent=state.radius+' mi'}if($('exclude-costco'))$('exclude-costco').checked=state.excludeCostco;$('exclude-costco')?.addEventListener('change',e=>{state.excludeCostco=e.target.checked;savePrefs();loadFuel()});$('radius')?.addEventListener('input',e=>{$('radius-value').textContent=e.target.value+' mi';state.radius=+e.target.value;savePrefs();clearTimeout(window._r);window._r=setTimeout(loadFuel,350)});document.querySelectorAll('[data-city]').forEach(el=>el.addEventListener('click',()=>searchPlace(el.dataset.city,{updateUrl:true,scroll:true})));$('result-search')?.addEventListener('click',()=>{document.getElementById('header-search-toggle')?.click()});const p=new URLSearchParams(location.search);if(p.get('loc')) useLocation();else if(p.get('q')) searchPlace(p.get('q'),{updateUrl:false,scroll:false});else if(p.get('city')) searchPlace(p.get('city'),{updateUrl:false,scroll:false});else loadFuel()}
document.addEventListener('DOMContentLoaded',init);


const CITIES = {London:[51.5074,-0.1278],Birmingham:[52.4862,-1.8904],Manchester:[53.4808,-2.2426],Glasgow:[55.8642,-4.2518],Leeds:[53.8008,-1.5491],Liverpool:[53.4084,-2.9916],Bristol:[51.4545,-2.5879],Reading:[51.4551,-0.9781],Sheffield:[53.3811,-1.4701],Cardiff:[51.4816,-3.1791],Edinburgh:[55.9533,-3.1883],Newcastle:[54.9783,-1.6178],Nottingham:[52.9548,-1.1581],Leicester:[52.6369,-1.1398],Oxford:[51.7520,-1.2577],Cambridge:[52.2053,0.1218],Southampton:[50.9097,-1.4044],Newbury:[51.4014,-1.3231],Basingstoke:[51.2665,-1.0924],Guildford:[51.2362,-0.5704],Swindon:[51.5558,-1.7797],Slough:[51.5105,-0.5950]};
let state = { mode:'petrol', lat:51.5074, lng:-0.1278, radius:3, label:'London', excludeCostco:false, connector:'any' };
const MODES = ['petrol','diesel','ev'];
const MODE_LABEL = { petrol:'Petrol', diesel:'Diesel', ev:'EV' };
const $ = id => document.getElementById(id);
function setText(id, value){ const el=$(id); if(el) el.textContent=value; }
function setStatus(t){ setText('station-name', t); }
function setActiveMode(mode){
  document.querySelectorAll('[data-mode]').forEach(x => x.classList.toggle('active', x.dataset.mode === mode));
  setText('cycle-label', MODE_LABEL[mode] || mode);
  setText('side-mode', MODE_LABEL[mode] || mode);
  const cf = $('connector-field'); if (cf) cf.style.display = mode === 'ev' ? 'block' : 'none';
}
function updateCyclePrice(){ setText('cycle-price', (($('main-price')?.textContent || '--') + ($('main-unit')?.textContent || ''))); }
function renderCompare(items){
  const body = $('compare-body');
  if (!body) return;
  if (!items || !items.length) { body.innerHTML = '<tr><td colspan="4">No comparison results available yet.</td></tr>'; setText('compare-count','0 found'); return; }
  body.innerHTML = items.slice(0, 8).map(item => `<tr><td>${escapeHtml(item.name || 'Station')}</td><td>${escapeHtml(item.dist || '--')}</td><td>${escapeHtml(item.price || '--')}${escapeHtml(item.unit || '')}</td><td>${escapeHtml(item.allPrices || item.opening || '')}</td></tr>`).join('');
  setText('compare-count', `${Math.min(items.length,8)} shown`);
}
function escapeHtml(s){ return String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function showData(d){
  setText('main-price', d.price === 'FREE' ? 'FREE' : parseFloat(d.price).toFixed(1));
  setText('main-unit', d.price === 'FREE' ? '' : (d.unit || 'p'));
  setText('station-name', d.name || 'Station found');
  setText('distance', d.dist || '--');
  setText('updated', d.updated ? `Updated ${d.updated}` : 'Updated today');
  setText('hours', d.opening || 'Opening times unavailable');
  setText('address', d.address || state.label);
  setText('all-prices', d.allPrices || 'Prices vary by fuel type');
  const directions = $('directions'); if (directions && d.lat && d.lng) directions.href = `https://www.google.com/maps/dir/?api=1&destination=${d.lat},${d.lng}`;
  renderCompare(d.results || []);
  updateCyclePrice();
}
async function loadFuel(){
  document.body.classList.add('loading');
  setStatus('Checking nearby prices…');
  setActiveMode(state.mode);
  try {
    const params = new URLSearchParams({lat:state.lat,lng:state.lng,mode:state.mode,radius:state.radius,excludeCostco:state.excludeCostco,connector:state.connector});
    const res = await fetch(`/api/fuel?${params.toString()}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'No result');
    showData(data);
  } catch(e) {
    setStatus(e.message || 'No station found nearby');
    setText('main-price','--'); setText('main-unit',''); updateCyclePrice(); renderCompare([]);
  } finally { document.body.classList.remove('loading'); }
}
async function geocode(q){
  const key = q.replace(/\s+/g,'');
  if (CITIES[q] || CITIES[key]) { const c=CITIES[q] || CITIES[key]; return {lat:c[0], lng:c[1], label:q}; }
  const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=gb&q=${encodeURIComponent(q)}`);
  const data = await res.json();
  if (data[0]) return {lat:+data[0].lat, lng:+data[0].lon, label:q};
  throw new Error('Place not found');
}
async function searchPlace(q){ setStatus('Finding ' + q + '…'); try { Object.assign(state, await geocode(q)); loadFuel(); } catch(e){ setStatus(e.message); } }
function init(){
  if (!$('fuel-card')) return;
  document.querySelectorAll('[data-mode]').forEach(b => b.addEventListener('click', () => { state.mode = b.dataset.mode; setActiveMode(state.mode); loadFuel(); }));
  $('price-cycle')?.addEventListener('click', () => { const i = MODES.indexOf(state.mode); state.mode = MODES[(i+1)%MODES.length]; setActiveMode(state.mode); loadFuel(); });
  $('exclude-costco')?.addEventListener('change', e => { state.excludeCostco = e.target.checked; loadFuel(); });
  $('connector-type')?.addEventListener('change', e => { state.connector = e.target.value; if (state.mode === 'ev') loadFuel(); });
  $('compare-3')?.addEventListener('click', () => { state.radius = 3; const r=$('radius'); if(r) r.value=3; setText('radius-value','3 mi'); loadFuel(); document.getElementById('compare')?.scrollIntoView({behavior:'smooth'}); });
  $('radius')?.addEventListener('input', e => { setText('radius-value', e.target.value + ' mi'); state.radius = +e.target.value; clearTimeout(window._r); window._r = setTimeout(loadFuel, 350); });
  document.querySelectorAll('[data-city]').forEach(el => el.addEventListener('click', () => searchPlace(el.dataset.city)));
  const p = new URLSearchParams(location.search);
  if (p.get('loc') && navigator.geolocation) navigator.geolocation.getCurrentPosition(pos => { state.lat=pos.coords.latitude; state.lng=pos.coords.longitude; state.label='Your location'; loadFuel(); }, () => loadFuel());
  else if (p.get('q')) searchPlace(p.get('q'));
  else if (p.get('city')) searchPlace(p.get('city'));
  else loadFuel();
}
document.addEventListener('DOMContentLoaded', init);

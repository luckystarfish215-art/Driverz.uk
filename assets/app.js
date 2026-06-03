const CITIES={London:[51.5074,-0.1278],Birmingham:[52.4862,-1.8904],Manchester:[53.4808,-2.2426],Glasgow:[55.8642,-4.2518],Leeds:[53.8008,-1.5491],Liverpool:[53.4084,-2.9916],Bristol:[51.4545,-2.5879],Reading:[51.4551,-0.9781],Sheffield:[53.3811,-1.4701],Cardiff:[51.4816,-3.1791],Edinburgh:[55.9533,-3.1883],Newcastle:[54.9783,-1.6178],Nottingham:[52.9548,-1.1581],Leicester:[52.6369,-1.1398],Coventry:[52.4068,-1.5197],Oxford:[51.7520,-1.2577],Cambridge:[52.2053,0.1218],Brighton:[50.8225,-0.1372],Southampton:[50.9097,-1.4044],Portsmouth:[50.8198,-1.0880],Plymouth:[50.3755,-4.1427],Norwich:[52.6309,1.2974],Exeter:[50.7184,-3.5339],York:[53.9590,-1.0815],Aberdeen:[57.1497,-2.0943],Swansea:[51.6214,-3.9436],MiltonKeynes:[52.0406,-0.7594],Luton:[51.8787,-0.4200],Blackpool:[53.8175,-3.0357],Middlesbrough:[54.5742,-1.2348],Wolverhampton:[52.5862,-2.1280],Derby:[52.9225,-1.4746],Stoke:[53.0027,-2.1794],Preston:[53.7632,-2.7031],Swindon:[51.5558,-1.7797],Slough:[51.5105,-0.5950],Bath:[51.3758,-2.3599],Dundee:[56.4620,-2.9707],Chelmsford:[51.7356,0.4686],Worcester:[52.1936,-2.2216],Hull:[53.7676,-0.3274],Bolton:[53.5769,-2.4282],Wigan:[53.5451,-2.6325],Maidstone:[51.2704,0.5227],Canterbury:[51.2802,1.0789],Inverness:[57.4778,-4.2247],Carlisle:[54.8925,-2.9329],Chester:[53.1934,-2.8931],Wrexham:[53.0465,-2.9916],Newbury:[51.4014,-1.3231],Basingstoke:[51.2665,-1.0924],Guildford:[51.2362,-0.5704],Watford:[51.6565,-0.3903],Croydon:[51.3762,-0.0982],Dartford:[51.4462,0.2169],Colchester:[51.8959,0.8919],Ipswich:[52.0567,1.1482],Peterborough:[52.5695,-0.2405],Lincoln:[53.2307,-0.5407],Gloucester:[51.8642,-2.2444]};

const tips=[
  'Check tyre pressure when tyres are cold for the most accurate reading.',
  'Using a handheld phone while driving can mean a fine and penalty points.',
  'Smooth acceleration usually saves more fuel than late braking.',
  'Rapid EV charging is often fastest between about 20% and 80%.',
  'Remove unused roof bars to reduce drag and fuel use.',
  'Clean Air Zone rules vary by city — check before entering.'
];

let tipI=0;

function rotateTip(){
  const el=document.getElementById('tip-text');
  if(!el)return;
  el.textContent=tips[tipI++%tips.length];
}

setInterval(rotateTip,6000);
rotateTip();

const $=id=>document.getElementById(id);

function savedNumber(key,fallback){
  const raw=localStorage.getItem(key);
  const v=parseFloat(raw);
  return Number.isFinite(v)?v:fallback;
}

function clampRadius(v){
  v=parseFloat(v);
  if(!Number.isFinite(v))v=0.5;
  v=Math.round(v*2)/2;
  return Math.min(10,Math.max(0.5,v));
}

function formatRadius(v){
  return (Number.isInteger(v)?String(v):v.toFixed(1))+' mi';
}

const hasSavedLocation=localStorage.getItem('driverzLocationSet')==='1'&&localStorage.getItem('driverzLat')&&localStorage.getItem('driverzLng');

let state={
  mode:localStorage.getItem('lastMode')||'petrol',
  lat:savedNumber('driverzLat',51.4551),
  lng:savedNumber('driverzLng',-0.9781),
  radius:clampRadius(savedNumber('driverzRadius',0.5)),
  label:localStorage.getItem('driverzLabel')||(hasSavedLocation?'Saved location':'Reading'),
  excludeCostco:localStorage.getItem('driverzExcludeCostco')==='1'
};

const FAVOURITES_KEY='driverzFavouriteStations';
const MAX_FAVOURITES=5;
let currentStationResult=null;
let stationSearchTimer=null;
const stationCache=new Map();

function saveLocation(){
  if(Number.isFinite(state.lat)&&Number.isFinite(state.lng)){
    localStorage.setItem('driverzLat',state.lat);
    localStorage.setItem('driverzLng',state.lng);
    localStorage.setItem('driverzLabel',state.label||'Your location');
    localStorage.setItem('driverzLocationSet','1');
    localStorage.setItem('driverzLocationPromptDismissed','1');

    const p=$('location-soft-prompt');
    if(p)p.hidden=true;
  }
}

function savePrefs(){
  state.radius=clampRadius(state.radius);
  localStorage.setItem('lastMode',state.mode);
  localStorage.setItem('driverzRadius',state.radius);
  localStorage.setItem('driverzExcludeCostco',state.excludeCostco?'1':'0');
}

const MODES=['petrol','diesel','ev'];
const MODE_LABEL={petrol:'Petrol',diesel:'Diesel',ev:'EV'};

function setStatus(t){
  const el=$('station-name');
  if(el)el.textContent=t;
}

function ensureStationUpdatedChip(){
  let chip=$('station-updated');
  if(chip)return chip;

  const after=$('updated');
  if(!after||!after.parentNode)return null;

  chip=document.createElement('span');
  chip.className='chip';
  chip.id='station-updated';
  after.insertAdjacentElement('afterend',chip);

  return chip;
}

function priceUpdatedText(d){
  if(d.stationUpdated){
    return `Price updated ${d.stationUpdated}`;
  }

  if(d.updated&&String(d.updated).toLowerCase().includes('live')){
    return 'Live feed';
  }

  return 'Price update unknown';
}

function setActiveMode(mode){
  document.querySelectorAll('[data-mode]').forEach(x=>{
    x.classList.toggle('active',x.dataset.mode===mode);
  });

  const label=$('cycle-label');
  if(label)label.textContent=MODE_LABEL[mode]||mode;

  localStorage.setItem('lastMode',mode);
}

function updateCyclePrice(){
  const cp=$('cycle-price');
  if(cp){
    cp.textContent=localStorage.getItem('lastPrice_'+state.mode)||(($('main-price')?.textContent||'--')+($('main-unit')?.textContent||''));
  }

  window.dispatchEvent(new Event('driverz:price-updated'));
}

function renderOtherPrices(text){
  const el=$('all-prices');
  if(!el)return;

  const label=$('other-price-label');
  if(label)label.textContent=state.mode==='ev'?'Other EV prices':'Other fuel prices';

  el.innerHTML='';

  let value=text;
  if(!value){
    value=state.mode==='ev'?'Nearby EV prices not listed':'Prices vary by fuel type';
  }

  const parts=value.split('·').map(x=>x.trim()).filter(Boolean);

  if(parts.length>1){
    parts.forEach(part=>{
      const chip=document.createElement('span');
      chip.className='price-chip';
      chip.textContent=part;
      el.appendChild(chip);
    });
  }else{
    const chip=document.createElement('span');
    chip.className='price-chip wide';
    chip.textContent=value;
    el.appendChild(chip);
  }
}

function formatMainPrice(d){
  const raw=d.price;
  const n=typeof raw==='number'?raw:parseFloat(String(raw).replace(/[^0-9.]/g,''));

  if(state.mode==='ev'&&(raw==='FREE'||n===0)){
    return {price:'FREE',unit:''};
  }

  if(raw==='FREE'){
    return {price:'FREE',unit:''};
  }

  return {
    price:Number.isFinite(n)?n.toFixed(1):'--',
    unit:d.unit||'p'
  };
}

function parseDistanceMiles(value){
  const n=parseFloat(String(value||'').replace(/[^0-9.]/g,''));
  return Number.isFinite(n)?n:0;
}

function renderQuickCalc(d,formatted){
  const box=$('quick-calc');
  const lines=$('quick-calc-lines');

  if(!box||!lines)return;

  const n=typeof d.price==='number'?d.price:parseFloat(String(d.price||'').replace(/[^0-9.]/g,''));
  const miles=parseDistanceMiles(d.dist);

  if(!Number.isFinite(n)||miles<=0){
    box.hidden=true;
    lines.innerHTML='';
    return;
  }

  const returnMiles=miles*2;
  let html='';

  if(state.mode==='ev'){
    const free=(d.price==='FREE'||n===0);
    const topUp=free?0:(n*20/100);
    const driveCost=free?0:(returnMiles*0.30*n/100);

    html=`<span>A standard 20kWh top-up costs ${free?'FREE':'about £'+topUp.toFixed(2)}.</span><span>Estimated energy to drive here and back: ${driveCost===0?'FREE':'£'+driveCost.toFixed(2)}.</span>`;
  }else{
    const fill=n*40/100;
    const driveCost=(returnMiles/40)*4.54609*n/100;

    html=`<span>A standard 40L fill-up costs about £${fill.toFixed(2)}.</span><span>Estimated fuel to drive here and back: £${driveCost.toFixed(2)}.</span>`;
  }

  lines.innerHTML=html;
  box.hidden=false;
}

function mapHref(item){
  if(item&&Number.isFinite(+item.lat)&&Number.isFinite(+item.lng)){
    return `https://www.google.com/maps/dir/?api=1&destination=${item.lat},${item.lng}`;
  }

  const q=encodeURIComponent([item?.name,item?.address].filter(Boolean).join(', '));
  return `https://www.google.com/maps/search/?api=1&query=${q}`;
}

function cacheStation(item){
  if(!item||!item.id)return;
  stationCache.set(String(item.id),{
    id:String(item.id),
    mode:state.mode,
    name:item.name||'Fuel station',
    address:item.address||'',
    dist:item.dist||'',
    price:item.price,
    unit:item.unit||'p',
    priceText:item.priceText||([item.price,item.unit].filter(Boolean).join('')),
    lat:item.lat,
    lng:item.lng
  });
}


function comparePriceNumber(item){
  const raw=item&&typeof item.price!=='undefined'?item.price:item?.priceText;
  const n=parseFloat(String(raw||'').replace(/[^0-9.]/g,''));
  return Number.isFinite(n)?n:null;
}

function medianNumber(values){
  const nums=values.filter(Number.isFinite).sort((a,b)=>a-b);
  if(!nums.length)return null;
  const mid=Math.floor(nums.length/2);
  return nums.length%2?nums[mid]:(nums[mid-1]+nums[mid])/2;
}

function hasDataFreshnessWarning(confidence){
  const messages=(confidence&&Array.isArray(confidence.messages)?confidence.messages:[])
    .map(m=>String(m||'').toLowerCase());

  // Only preserve hard data-quality/freshness warnings from the API.
  // Do NOT preserve generic "Check with station before travelling" by itself,
  // because price-anomaly Low messages also include that sentence. Those rows
  // should be recalculated from the currently displayed compare-list prices.
  return messages.some(m=>
    /updated\s+\d+\s+days?\s+ago/.test(m)||
    /price updated\s+\d+\s+days?\s+ago/.test(m)||
    /\bstale\b/.test(m)||
    /older than/.test(m)||
    /price update unknown/.test(m)||
    /not currently available/.test(m)
  );
}


function evListConfidence(item){
  const raw=String(item?.priceText ?? item?.price ?? '').trim();
  const lower=raw.toLowerCase();

  if(!raw || lower.includes('price not listed')){
    return {level:'low',label:'Price info unavailable',messages:['Check operator before travelling.']};
  }

  if(lower.includes('free')){
    return {level:'medium',label:'Price info: FREE',messages:['Listed as FREE. Check operator before charging.']};
  }

  const n=parseFloat(lower.replace(/[^0-9.]/g,''));
  if(Number.isFinite(n)){
    return {level:'high',label:'Price info available',messages:['Check operator for live availability.']};
  }

  return {level:'medium',label:'Price info needs checking',messages:['Check operator before charging.']};
}

function simpleListConfidence(item, rows){
  if(state.mode==='ev') return item?.priceConfidence || evListConfidence(item);

  // Recalculate normal compare-list price context, but do not upgrade
  // hard data freshness warnings. Example: BP Three Mile Cross can become
  // High when the old list context was wrong; ASDA updated 12 days ago must
  // remain Medium/Low in the list because the warning is about stale data.
  if(hasDataFreshnessWarning(item&&item.priceConfidence)){
    return item.priceConfidence;
  }

  const price=comparePriceNumber(item);
  if(!Number.isFinite(price)){
    return {level:'low',label:'Price confidence: Low',messages:['Price is not currently available.']};
  }

  if(price<110 || price>230){
    return {level:'low',label:'Price confidence: Low',messages:['Unusual price range. Check with station before travelling.']};
  }

  const others=(rows||[])
    .filter(r=>r&&r!==item&&String(r.id||'')!==String(item.id||''))
    .map(comparePriceNumber)
    .filter(Number.isFinite);
  const med=medianNumber(others);

  if(Number.isFinite(med)){
    const diff=Math.abs(price-med);
    if(diff>=18){
      return {level:'low',label:'Price confidence: Low',messages:['Significantly different from nearby station list. Check before travelling.']};
    }
    if(diff>=10){
      return {level:'medium',label:'Price confidence: Medium',messages:['Different from nearby station list.']};
    }
  }

  return {level:'high',label:'Price confidence: High',messages:['Looks consistent with nearby station list.']};
}

function normaliseCompareListConfidence(rows){
  return (rows||[]).map(item=>({
    ...item,
    priceConfidence:simpleListConfidence(item, rows)
  }));
}

function renderCompare(compareData){
  const wrap=$('compare-nearby');
  const list=$('compare-list');
  const toggle=$('compare-toggle');
  const summary=$('compare-summary');

  if(!wrap||!list||!toggle)return;

  const rawRows=(Array.isArray(compareData)?compareData:(compareData&&Array.isArray(compareData.items)?compareData.items:[])).filter(Boolean).slice(0,6);
  const rows=normaliseCompareListConfidence(rawRows);
  const fallback=!!(compareData&&!Array.isArray(compareData)&&compareData.fallback);

  if(!rows.length){
    wrap.hidden=true;
    list.innerHTML='';
    return;
  }

  rows.forEach(cacheStation);

  const noun=state.mode==='ev'?'chargers':'stations';
  const title=fallback?(state.mode==='ev'?'Closest nearby chargers':'Closest nearby stations'):(state.mode==='ev'?'Compare nearby chargers':'Compare nearby stations');

  const titleEl=toggle.querySelector('span');
  if(titleEl)titleEl.textContent=title;

  if(summary){
    summary.textContent=fallback?`No ${noun} within ${formatRadius(state.radius)} — showing the closest ${rows.length} options`:`Top ${rows.length} nearby ${noun} within ${formatRadius(state.radius)}`;
  }

  list.innerHTML=rows.map(item=>{
    const price=item.priceText||([item.price,item.unit].filter(Boolean).join(''));
    const badge=item.badge?`<em>${item.badge}</em>`:(item.isBest?'<em>Cheapest nearby</em>':'');
    const href=mapHref(item);
    const canFav=item.id&&(state.mode==='petrol'||state.mode==='diesel');
    const fav=canFav?stationIsFavourite(item.id):false;
    const confidence=item.priceConfidence?`<small class="price-confidence-inline confidence-${item.priceConfidence.level}">${item.priceConfidence.label}</small>`:'';

    return `<article class="compare-row" data-station-id="${item.id||''}">
      <div class="compare-price">${price||'Price not listed'}</div>
      <div class="compare-info">
        <strong>${item.name||'Nearby option'}</strong>
        <div>${[item.dist,item.opening,item.connectors||''].filter(Boolean).join(' · ')}</div>
        ${item.address?`<small>${item.address}</small>`:''}
        ${confidence}
      </div>
      <div class="compare-actions">
        ${badge}
        ${canFav?`<button class="favourite-toggle list-favourite-star" type="button" data-favourite-toggle data-station-id="${item.id}" aria-label="${fav?'Remove from My Stations':'Add to My Stations'}" aria-pressed="${fav?'true':'false'}">${fav?'★':'☆'}</button>`:''}
        <a class="btn light compare-map" href="${href}" target="_blank" rel="noopener">Directions</a>
      </div>
    </article>`;
  }).join('');

  wrap.hidden=false;
  list.hidden=false;
}


function parseStoredFavourites(){
  try{
    const parsed=JSON.parse(localStorage.getItem(FAVOURITES_KEY)||'[]');
    return Array.isArray(parsed)?parsed.filter(x=>x&&x.id).map(x=>({...x,id:String(x.id)})):[];
  }catch(e){
    return [];
  }
}

function saveStoredFavourites(items){
  localStorage.setItem(FAVOURITES_KEY,JSON.stringify(items.slice(0,MAX_FAVOURITES)));
}

function stationIsFavourite(id){
  return !!id&&parseStoredFavourites().some(x=>String(x.id)===String(id)&&x.mode===state.mode);
}

function showToast(message){
  const toast=$('driverz-toast');
  if(!toast)return;
  toast.textContent=message;
  toast.hidden=false;
  clearTimeout(showToast._timer);
  showToast._timer=setTimeout(()=>{toast.hidden=true;},2200);
}

function itemFromStationLike(item){
  if(!item||!item.id)return null;
  const priceText=item.priceText||((item.price==='FREE')?'FREE':(Number.isFinite(parseFloat(item.price))?`${parseFloat(item.price).toFixed(1)}${item.unit||'p'}`:'View'));
  return {
    id:String(item.id),
    mode:state.mode,
    name:item.name||'Fuel station',
    address:item.address||'',
    dist:item.dist||'',
    price:item.price,
    unit:item.unit||'p',
    priceText,
    lat:item.lat,
    lng:item.lng,
    savedAt:new Date().toISOString()
  };
}

function buildFavouriteFromResult(d){
  if(!d||!d.stationId)return null;
  return itemFromStationLike({
    id:d.stationId,
    name:d.name,
    address:d.address,
    dist:d.dist,
    price:d.price,
    unit:d.unit||'p',
    priceText:(d.price==='FREE')?'FREE':(Number.isFinite(parseFloat(String(d.price).replace(/[^0-9.]/g,'')))?`${parseFloat(String(d.price).replace(/[^0-9.]/g,'')).toFixed(1)}${d.unit||'p'}`:'View'),
    lat:d.lat,
    lng:d.lng
  });
}

function updateFavouriteStars(){
  document.querySelectorAll('[data-favourite-toggle]').forEach(btn=>{
    const id=btn.dataset.stationId||(currentStationResult&&currentStationResult.stationId);
    const canFav=id&&(state.mode==='petrol'||state.mode==='diesel');
    btn.hidden=!canFav;
    if(!canFav)return;
    const saved=stationIsFavourite(id);
    btn.textContent=saved?'★':'☆';
    btn.classList.toggle('saved',saved);
    btn.setAttribute('aria-pressed',saved?'true':'false');
    btn.setAttribute('aria-label',saved?'Remove from My Stations':'Add to My Stations');
  });
}

function toggleFavouriteByStation(item){
  const fav=itemFromStationLike(item);
  if(!fav)return;

  let items=parseStoredFavourites();
  const exists=items.some(x=>x.id===fav.id&&x.mode===fav.mode);

  if(exists){
    items=items.filter(x=>!(x.id===fav.id&&x.mode===fav.mode));
    saveStoredFavourites(items);
    showToast('Removed from My Stations');
  }else{
    const sameModeCount=items.filter(x=>x.mode===state.mode).length;
    if(sameModeCount>=MAX_FAVOURITES){
      showToast('You can save up to 5 stations. Remove one to add another.');
      return;
    }
    items=[fav,...items.filter(x=>!(x.id===fav.id&&x.mode===fav.mode))];
    saveStoredFavourites(items);
    showToast('Added to My Stations');
  }

  renderFavouriteStations();
  updateFavouriteStars();
}

function toggleFavourite(){
  if(!currentStationResult||!currentStationResult.stationId)return;
  toggleFavouriteByStation(buildFavouriteFromResult(currentStationResult));
}

function renderFavouriteStations(){
  const wrap=$('favourite-stations');
  const list=$('favourite-station-list');
  if(!wrap||!list)return;

  const items=parseStoredFavourites().filter(x=>x.mode===state.mode).slice(0,MAX_FAVOURITES);

  if(!items.length){
    wrap.hidden=true;
    list.innerHTML='';
    return;
  }

  list.innerHTML=items.map(item=>`<article class="favourite-station-card" data-favourite-id="${item.id}">
    <button class="favourite-toggle saved" type="button" data-favourite-toggle data-station-id="${item.id}" aria-label="Remove from My Stations" aria-pressed="true">★</button>
    <button class="favourite-station-open" type="button" data-favourite-open="${item.id}">
      <span><strong>${item.name}</strong><small>${[item.dist,item.address].filter(Boolean).join(' · ')}</small></span>
      <span class="favourite-station-price">${item.priceText||'View'}</span>
    </button>
  </article>`).join('');

  wrap.hidden=false;
  updateFavouriteStars();
}


function normaliseStationIdentityText(value){
  return String(value||'').trim().toLowerCase().replace(/\s+/g,' ');
}

function sameStationForUIConfidence(a,b){
  if(!a||!b)return false;

  const aid=String(a.id||a.stationId||'').trim();
  const bid=String(b.id||b.stationId||'').trim();
  if(aid&&bid&&aid===bid)return true;

  const alat=parseFloat(a.lat);
  const alng=parseFloat(a.lng);
  const blat=parseFloat(b.lat);
  const blng=parseFloat(b.lng);
  if(Number.isFinite(alat)&&Number.isFinite(alng)&&Number.isFinite(blat)&&Number.isFinite(blng)){
    if(Math.abs(alat-blat)<0.00005&&Math.abs(alng-blng)<0.00005)return true;
  }

  const aname=normaliseStationIdentityText(a.name);
  const bname=normaliseStationIdentityText(b.name);
  const aaddr=normaliseStationIdentityText(a.address);
  const baddr=normaliseStationIdentityText(b.address);
  if(aname&&bname&&aname===bname&&aaddr&&baddr&&aaddr===baddr)return true;

  return false;
}

function compareRowsFromResponse(d){
  if(Array.isArray(d?.compare))return d.compare;
  if(d?.compare&&Array.isArray(d.compare.items))return d.compare.items;
  return [];
}

function applyConsistentPriceConfidence(d){
  if(!d)return d;

  const selected={
    id:d.stationId,
    stationId:d.stationId,
    name:d.name,
    address:d.address,
    lat:d.lat,
    lng:d.lng
  };

  const rows=compareRowsFromResponse(d);
  const matched=rows.find(item=>item&&item.priceConfidence&&sameStationForUIConfidence(item,selected));

  if(matched&&matched.priceConfidence){
    d.priceConfidence=matched.priceConfidence;
    if(d.searchContext){
      d.searchContext.priceConfidence=matched.priceConfidence;
    }
  }

  return d;
}

function confidenceMarkup(confidence){
  if(!confidence||!confidence.label)return '';
  const details=(confidence.messages||[]).slice(0,2).map(m=>`<small>${m}</small>`).join('');
  return `<div class="price-confidence-card confidence-${confidence.level||'medium'}"><strong>${confidence.label}</strong>${details}</div>`;
}

function renderSearchInsight(ctx){
  const box=$('station-search-insight');
  if(!box)return;

  if(!ctx){
    box.hidden=true;
    box.innerHTML='';
    return;
  }

  const diff=Number(ctx.differencePence);
  const saving=Number(ctx.saving35L);
  const selectedIsCheapest=!!ctx.selectedIsCheapest || Math.abs(diff||0)<0.05;
  const diffText=Number.isFinite(diff)?`${Math.abs(diff).toFixed(1)}p ${selectedIsCheapest?'matches cheapest nearby':'above cheapest nearby'}`:'Nearby comparison unavailable';
  const savingText=Number.isFinite(saving)&&saving>0
    ? `Save about £${saving.toFixed(2)} by choosing the cheapest nearby.`
    : 'This looks like the cheapest nearby option.';

  box.innerHTML=`<div class="search-context-card">
    <div class="context-label">You searched for</div>
    <div class="context-line"><strong>${ctx.selectedName||'Selected station'}</strong><span>${ctx.selectedPriceText||''}</span></div>
    <div class="context-line"><span>${selectedIsCheapest?'✓ Cheapest nearby':'↑ '+diffText}</span><span>${ctx.cheapestName?`Cheapest nearby: ${ctx.cheapestName}`:''}</span></div>
    ${confidenceMarkup(ctx.priceConfidence)}
  </div>
  <div class="saving-strip ${selectedIsCheapest?'':'warning'}">
    <span><strong>Save today</strong><br><small>${savingText}</small></span>
    <em>${Number.isFinite(saving)&&saving>0?'£'+saving.toFixed(2):'Best price'}</em>
  </div>`;
  box.hidden=false;
}

function renderStationSuggestions(items,message){
  const box=$('station-search-results');
  if(!box)return;

  if(message){
    box.innerHTML=`<div class="station-suggestion"><span><strong>${message}</strong><small>Try a brand, station name or postcode such as Costco, Shell or RG2.</small></span></div>`;
    box.hidden=false;
    return;
  }

  if(!items||!items.length){
    box.hidden=true;
    box.innerHTML='';
    return;
  }

  items.forEach(cacheStation);

  box.innerHTML=items.map(item=>{
    const fav=stationIsFavourite(item.id);
    return `<button class="station-suggestion" type="button" data-station-id="${item.id}">
      <span><strong>${item.name}</strong><small>${[item.dist,item.address].filter(Boolean).join(' · ')}</small></span>
      <span class="station-suggestion-price">${item.priceText||'View'}</span>
      <span class="favourite-toggle suggestion-favourite-star ${fav?'saved':''}" role="button" tabindex="0" data-favourite-toggle data-station-id="${item.id}" aria-label="${fav?'Remove from My Stations':'Add to My Stations'}" aria-pressed="${fav?'true':'false'}">${fav?'★':'☆'}</span>
    </button>`;
  }).join('');
  box.hidden=false;
}

async function searchStations(q){
  const query=String(q||'').trim();
  renderSearchInsight(null);

  if(state.mode==='ev'){
    renderStationSuggestions([], 'Station search currently supports petrol and diesel. Switch mode to search forecourts.');
    return;
  }

  if(query.length<2){
    renderStationSuggestions([]);
    return;
  }

  try{
    const res=await fetch(`/api/fuel?stationSearch=${encodeURIComponent(query)}&lat=${state.lat}&lng=${state.lng}&mode=${state.mode}&radius=${state.radius}&excludeCostco=${state.excludeCostco}`);
    const data=await res.json();

    if(!res.ok)throw new Error(data.error||'No station found');

    renderStationSuggestions(data.suggestions||[]);
  }catch(e){
    renderStationSuggestions([], e.message||'No station found');
  }
}

async function loadSearchedStation(stationId,query){
  if(!stationId)return;

  setStatus('Checking station price…');

  try{
    const res=await fetch(`/api/fuel?stationSearch=${encodeURIComponent(query||'station')}&stationId=${encodeURIComponent(stationId)}&lat=${state.lat}&lng=${state.lng}&mode=${state.mode}&radius=${state.radius}&excludeCostco=${state.excludeCostco}`);
    const data=await res.json();

    if(!res.ok)throw new Error(data.error||'Station not found');

    showData(data);

    const results=$('station-search-results');
    if(results){
      results.hidden=true;
      results.innerHTML='';
    }

    document.getElementById('fuel-card')?.scrollIntoView({behavior:'smooth',block:'start'});
  }catch(e){
    setStatus(e.message||'Station not found');
  }
}

function showData(d){
  d = applyConsistentPriceConfidence(d);
  currentStationResult=d&&d.stationId?d:null;
  if(currentStationResult){
    cacheStation({id:d.stationId,name:d.name,address:d.address,dist:d.dist,price:d.price,unit:d.unit||'p',priceText:(d.price==='FREE')?'FREE':`${parseFloat(String(d.price).replace(/[^0-9.]/g,'')).toFixed(1)}${d.unit||'p'}`,lat:d.lat,lng:d.lng});
  }
  const formatted=formatMainPrice(d);

  $('main-price').textContent=formatted.price;
  $('main-unit').textContent=formatted.unit;
  $('station-name').textContent=d.name||'Station found';
  $('distance').textContent=d.dist||'--';
  $('updated').textContent=priceUpdatedText(d);

  const stationChip=ensureStationUpdatedChip();
  if(stationChip){
    stationChip.hidden=true;
    stationChip.textContent='';
  }

  $('hours').textContent=d.opening||'Opening times unavailable';
  $('address').textContent=d.address||state.label;

  renderQuickCalc(d,formatted);

  const oldConfidence=document.querySelector('.main-price-confidence');
  if(oldConfidence)oldConfidence.remove();
  if(d.priceConfidence){
    const addressEl=$('address');
    addressEl?.insertAdjacentHTML('afterend',`<div class="main-price-confidence">${confidenceMarkup(d.priceConfidence)}</div>`);
  }

  const extra=[];
  if(d.allPrices)extra.push(d.allPrices);
  if(d.connectors)extra.push(`Connectors ${d.connectors}`);

  renderOtherPrices(extra.join(' · '));
  renderCompare(d.compare||[]);
  renderSearchInsight(d.searchContext||null);
  renderFavouriteStations();
  updateFavouriteStars();

  const maps=`https://www.google.com/maps/dir/?api=1&destination=${d.lat},${d.lng}`;
  $('directions').href=maps;

  localStorage.setItem('lastPrice_'+state.mode,$('main-price').textContent+$('main-unit').textContent);
  localStorage.setItem('lastMode',state.mode);

  saveLocation();
  savePrefs();
  updateCyclePrice();
}

async function loadFuel(){
  state.radius=clampRadius(state.radius);
  document.body.classList.add('loading');

  setStatus('Checking nearby prices…');
  setActiveMode(state.mode);
  savePrefs();

  try{
    const res=await fetch(`/api/fuel?lat=${state.lat}&lng=${state.lng}&mode=${state.mode}&radius=${state.radius}&excludeCostco=${state.excludeCostco}`);
    const data=await res.json();

    if(!res.ok)throw new Error(data.error||'No result');

    showData(data);
  }catch(e){
    setStatus(e.message||'No station found nearby');

    $('main-price').textContent='--';
    $('main-unit').textContent='';

    const qc=$('quick-calc');
    if(qc)qc.hidden=true;

    const sc=$('station-updated');
    if(sc)sc.hidden=true;

    renderCompare([]);
    renderSearchInsight(null);
    currentStationResult=null;
    updateFavouriteStars();
    updateCyclePrice();
  }finally{
    document.body.classList.remove('loading');
  }
}

async function geocode(q){
  const key=q.replace(/\s+/g,'');

  if(CITIES[q]||CITIES[key]){
    const c=CITIES[q]||CITIES[key];
    return {lat:c[0],lng:c[1],label:q};
  }

  const res=await fetch(`https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=gb&q=${encodeURIComponent(q)}`);
  const data=await res.json();

  if(data[0]){
    return {lat:+data[0].lat,lng:+data[0].lon,label:q};
  }

  throw new Error('Place not found');
}

async function searchPlace(q,opts={}){
  setStatus('Finding '+q+'…');

  try{
    const g=await geocode(q);
    Object.assign(state,g);
    saveLocation();

    if(opts.updateUrl!==false){
      const url='/?city='+encodeURIComponent(q)+'#fuel-card';
      history.replaceState(null,'',url);
    }

    loadFuel();

    if(opts.scroll!==false){
      document.getElementById('fuel-card')?.scrollIntoView({behavior:'smooth',block:'start'});
    }
  }catch(e){
    setStatus(e.message);
  }
}

function cycleMode(){
  const i=MODES.indexOf(state.mode);
  state.mode=MODES[(i+1)%MODES.length];
  savePrefs();
  loadFuel();
}

function useLocation(){
  if(!navigator.geolocation){
    setStatus('Location is not available in this browser. Search manually instead.');
    return;
  }

  setStatus('Finding your location…');

  navigator.geolocation.getCurrentPosition(
    pos=>{
      state.lat=pos.coords.latitude;
      state.lng=pos.coords.longitude;
      state.label='Your location';
      saveLocation();
      loadFuel();
    },
    ()=>{
      setStatus('Location permission was not granted. Using your saved location instead.');
      loadFuel();
    },
    {enableHighAccuracy:false,timeout:10000,maximumAge:300000}
  );
}

function maybeShowLocationPrompt(){
  const prompt=$('location-soft-prompt');
  if(!prompt)return;

  const params=new URLSearchParams(location.search);

  if(
    hasSavedLocation||
    localStorage.getItem('driverzLocationPromptDismissed')==='1'||
    params.get('loc')||
    params.get('q')||
    params.get('city')||
    !navigator.geolocation
  ){
    return;
  }

  const useBtn=prompt.querySelector('[data-location-use]');
  const dismissBtn=prompt.querySelector('[data-location-dismiss]');

  useBtn?.addEventListener('click',()=>{
    localStorage.setItem('driverzLocationPromptDismissed','1');
    prompt.hidden=true;
    useLocation();
  });

  dismissBtn?.addEventListener('click',()=>{
    localStorage.setItem('driverzLocationPromptDismissed','1');
    prompt.hidden=true;
  });

  setTimeout(()=>{
    if(
      localStorage.getItem('driverzLocationSet')==='1'||
      localStorage.getItem('driverzLocationPromptDismissed')==='1'
    ){
      return;
    }

    prompt.hidden=false;
  },900);
}

function getCityFromPath(){
  const raw=decodeURIComponent(location.pathname||'/').replace(/^\/+|\/+$/g,'');

  if(!raw||raw.includes('/')||raw.includes('.'))return '';

  const lower=raw.toLowerCase();
  const blocked=new Set(['api','assets','data','favicon','robots','sitemap','404']);

  if(blocked.has(lower))return '';

  return raw.replace(/-/g,' ').replace(/\b\w/g,m=>m.toUpperCase());
}

function normaliseCityKey(name){
  return String(name||'').toLowerCase().replace(/[^a-z0-9]/g,'');
}

const CITY_LOOKUP=Object.keys(CITIES).reduce((acc,name)=>{
  acc[normaliseCityKey(name)]=name;
  return acc;
},{});

function showPathCityNotFound(raw){
  setStatus('Place not found');

  const price=$('main-price');
  if(price)price.textContent='--';

  const unit=$('main-unit');
  if(unit)unit.textContent='';

  const distance=$('distance');
  if(distance)distance.textContent='-- mi';

  const updated=$('updated');
  if(updated)updated.textContent='Try another UK city';

  const hours=$('hours');
  if(hours)hours.textContent='Location not recognised';

  const stationChip=$('station-updated');
  if(stationChip){
    stationChip.hidden=true;
    stationChip.textContent='';
  }

  const address=$('address');
  if(address){
    address.textContent=`We could not recognise "${raw}" as a supported UK location. Try search, use your current location, or choose a popular UK location below.`;
  }

  const directions=$('directions');
  if(directions)directions.removeAttribute('href');

  const qc=$('quick-calc');
  if(qc)qc.hidden=true;

  renderOtherPrices('Search a UK town, city or postcode');
  renderCompare([]);
  updateCyclePrice();
}

function searchPathCity(raw){
  const match=CITY_LOOKUP[normaliseCityKey(raw)];

  if(!match){
    showPathCityNotFound(raw);
    return;
  }

  const c=CITIES[match];

  Object.assign(state,{
    lat:c[0],
    lng:c[1],
    label:match
  });

  saveLocation();
  loadFuel();
}

function init(){
  if(!$('fuel-card'))return;

  window.DriverzFuel={cycleMode,searchPlace,useLocation,searchStations,loadSearchedStation};

  maybeShowLocationPrompt();

  document.querySelectorAll('[data-mode]').forEach(b=>{
    b.addEventListener('click',()=>{
      state.mode=b.dataset.mode;
      savePrefs();
      loadFuel();
    });
  });

  if($('radius')){
    $('radius').min='0.5';
    $('radius').max='10';
    $('radius').step='0.5';
    $('radius').value=state.radius;
    $('radius-value').textContent=formatRadius(state.radius);
  }

  if($('exclude-costco')){
    $('exclude-costco').checked=state.excludeCostco;
  }

  $('exclude-costco')?.addEventListener('change',e=>{
    state.excludeCostco=e.target.checked;
    savePrefs();
    loadFuel();
  });

  $('radius')?.addEventListener('input',e=>{
    state.radius=clampRadius(e.target.value);
    e.target.value=state.radius;
    $('radius-value').textContent=formatRadius(state.radius);
    savePrefs();

    clearTimeout(window._r);
    window._r=setTimeout(loadFuel,350);
  });

  document.querySelectorAll('[data-city]').forEach(el=>{
    el.addEventListener('click',()=>{
      searchPlace(el.dataset.city,{updateUrl:true,scroll:true});
    });
  });

  $('result-search')?.addEventListener('click',()=>{
    document.getElementById('header-search-toggle')?.click();
  });


  const stationInput=$('station-search-input');
  stationInput?.addEventListener('input',e=>{
    clearTimeout(stationSearchTimer);
    const q=e.target.value;
    stationSearchTimer=setTimeout(()=>searchStations(q),220);
  });

  $('station-search-results')?.addEventListener('click',e=>{
    if(e.target.closest('[data-favourite-toggle]'))return;
    const btn=e.target.closest('[data-station-id]');
    if(!btn)return;
    loadSearchedStation(btn.dataset.stationId,stationInput?.value||'station');
  });

  document.addEventListener('click',e=>{
    const favBtn=e.target.closest('[data-favourite-toggle]');
    if(!favBtn)return;
    e.preventDefault();
    e.stopPropagation();

    const id=favBtn.dataset.stationId||(currentStationResult&&currentStationResult.stationId);
    const source= id&&stationCache.get(String(id));
    if(source){
      toggleFavouriteByStation(source);
    }else if(currentStationResult&&String(currentStationResult.stationId)===String(id)){
      toggleFavourite();
    }
  });

  document.addEventListener('keydown',e=>{
    if((e.key==='Enter'||e.key===' ')&&e.target.closest('[data-favourite-toggle]')){
      e.preventDefault();
      e.target.click();
    }
  });

  $('favourite-station-list')?.addEventListener('click',e=>{
    const btn=e.target.closest('[data-favourite-open]');
    if(!btn)return;
    const fav=parseStoredFavourites().find(x=>x.id===btn.dataset.favouriteOpen&&x.mode===state.mode);
    loadSearchedStation(btn.dataset.favouriteOpen,fav?.name||'station');
  });

  renderFavouriteStations();
  updateFavouriteStars();

  const p=new URLSearchParams(location.search);
  const pathCity=getCityFromPath();

  if(p.get('loc')){
    useLocation();
  }else if(p.get('q')){
    searchPlace(p.get('q'),{updateUrl:false,scroll:false});
  }else if(p.get('city')){
    const cityName=p.get('city').replace(/-/g,' ');
    searchPlace(cityName,{updateUrl:false,scroll:false});
  }else if(pathCity){
    searchPathCity(pathCity);
  }else{
    loadFuel();
  }
}

document.addEventListener('DOMContentLoaded',init);

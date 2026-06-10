(function(){
  const city = window.DriverzCity;
  if(!city) return;

  const $ = id => document.getElementById(id);
  const fmtPrice = v => {
    const n = parseFloat(String(v ?? '').replace(/[^0-9.]/g,''));
    return Number.isFinite(n) ? `${n.toFixed(1)}p` : 'Price unavailable';
  };
  const cleanTime = value => String(value || '').replace(/:00(?=\D|$)/g,'').replace(/\s+/g,' ').trim();
  const openingText = value => {
    const text = cleanTime(value);
    if(!text || /unavailable/i.test(text)) return 'Opening times unavailable';
    if(/closed/i.test(text)) return text;
    if(/open today|closed now/i.test(text)) return text;
    if(/\d{1,2}:\d{2}/.test(text)) return `Open today ${text}`;
    return text;
  };
  const mapsUrl = item => {
    const q = encodeURIComponent([item?.name,item?.address].filter(Boolean).join(', '));
    return `https://www.google.com/maps/search/?api=1&query=${q}`;
  };
  const fullFinderUrl = (mode, station) => {
    const params = new URLSearchParams({city: city.name});
    if(mode) params.set('mode', mode);
    if(station?.name) params.set('station', station.name);
    return `/?${params.toString()}#fuel-card`;
  };
  const trendText = history => {
    const change = history && history.change_7d && Number(history.change_7d.change);
    if(!Number.isFinite(change)) return {label:'7-day trend', value:'Building data', cls:'flat', detail:'Trend appears after more daily snapshots.'};
    if(Math.abs(change) < 0.05) return {label:'7-day trend', value:'no change', cls:'flat', detail:'No meaningful price movement over 7 days.'};
    const abs = Math.abs(change).toFixed(1)+'p';
    return change < 0
      ? {label:'7-day trend', value:`down ${abs}`, cls:'down', detail:'Cheapest result is lower than 7 days ago.'}
      : {label:'7-day trend', value:`up ${abs}`, cls:'up', detail:'Cheapest result is higher than 7 days ago.'};
  };
  const dayText = history => {
    const change = history && history.change_1d && Number(history.change_1d.change);
    if(!Number.isFinite(change)) return {value:'Building data', cls:'flat'};
    if(Math.abs(change) < 0.05) return {value:'no change', cls:'flat'};
    const abs = Math.abs(change).toFixed(1)+'p';
    return change < 0 ? {value:`down ${abs}`, cls:'down'} : {value:`up ${abs}`, cls:'up'};
  };

  const renderCard = (mode, data) => {
    const prefix = mode === 'diesel' ? 'diesel' : 'petrol';
    const card = $(`city-${prefix}-card`);
    if(!card) return;
    if(!data || data.error){
      card.innerHTML = `<div class="mini-label">${mode}</div><div class="city-error">No ${mode} result available</div>`;
      return;
    }
    const modeLabel = mode === 'diesel' ? 'Diesel' : 'Petrol';
    const station = data.name || 'Fuel station';
    card.innerHTML = `
      <div class="mini-label">Cheapest ${modeLabel.toLowerCase()} in ${city.name}</div>
      <div class="city-price">${fmtPrice(data.price)}</div>
      <div class="station">${station}</div>
      <div class="sub">${data.dist || ''} · ${data.stationUpdated ? 'Price updated '+data.stationUpdated : data.updated || ''}</div>
      <span class="open">${openingText(data.opening)}</span>
      <a class="link" href="${fullFinderUrl(mode, data)}">Open in fuel finder →</a>`;
  };

  const renderTrend = (petrol, diesel) => {
    const petrolTrend = trendText(petrol && petrol.history);
    const dieselTrend = trendText(diesel && diesel.history);
    const petrolDay = dayText(petrol && petrol.history);
    const dieselDay = dayText(diesel && diesel.history);
    const p = $('city-trend-petrol');
    const d = $('city-trend-diesel');
    const line = $('city-trend-line');
    if(p) p.innerHTML = `<small>Petrol since yesterday</small><strong class="${petrolDay.cls}">${petrolDay.value}</strong><small>${petrolTrend.detail}</small>`;
    if(d) d.innerHTML = `<small>Diesel since yesterday</small><strong class="${dieselDay.cls}">${dieselDay.value}</strong><small>${dieselTrend.value}</small>`;
    if(line) line.innerHTML = `Petrol 7-day trend: <strong class="${petrolTrend.cls}">${petrolTrend.value}</strong><br>Diesel 7-day trend: <strong class="${dieselTrend.cls}">${dieselTrend.value}</strong>`;
  };

  const collectStations = (petrol, diesel) => {
    const map = new Map();
    function add(mode, data){
      const items = data?.compare?.items || [];
      items.forEach((item, i) => {
        const key = item.id || [item.name,item.address].join('|');
        if(!map.has(key)) map.set(key,{id:item.id,name:item.name,address:item.address,dist:item.dist,opening:item.opening,lat:item.lat,lng:item.lng,petrol:null,diesel:null,rank:i});
        const row = map.get(key);
        row[mode] = item.priceText || fmtPrice(item.price);
        row.rank = Math.min(row.rank, i);
        row.opening = row.opening || item.opening;
        row.dist = row.dist || item.dist;
        row.lat = row.lat || item.lat;
        row.lng = row.lng || item.lng;
      });
    }
    add('petrol', petrol);
    add('diesel', diesel);
    return [...map.values()].sort((a,b)=>a.rank-b.rank).slice(0,8);
  };

  const renderStations = (rows) => {
    const tbody = $('city-station-rows');
    if(!tbody) return;
    if(!rows.length){
      tbody.innerHTML = `<tr><td colspan="7" class="city-error">No station results available yet.</td></tr>`;
      return;
    }
    tbody.innerHTML = rows.map((r,i)=>`
      <tr>
        <td>${i+1}</td>
        <td><strong>${r.name || 'Fuel station'}</strong><br><span class="muted">${r.address || ''}</span></td>
        <td class="price-cell">${r.petrol || '—'}</td>
        <td class="price-cell">${r.diesel || '—'}</td>
        <td>${r.dist || '—'}</td>
        <td>${openingText(r.opening)}</td>
        <td><a target="_blank" rel="noopener" href="${mapsUrl(r)}">Map ↗</a></td>
      </tr>`).join('');
  };

  const renderTopSummary = (petrol, diesel) => {
    const card = document.querySelector('.city-map-card');
    if(!card) return;
    const petrolOk = petrol && !petrol.error;
    const dieselOk = diesel && !diesel.error;
    const checked = (petrolOk && petrol.updated) || (dieselOk && diesel.updated) || 'Checked daily';
    card.innerHTML = `
      <div class="city-snapshot-kicker">Live city snapshot</div>
      <strong>${city.name} fuel dashboard</strong>
      <div class="city-snapshot-row petrol">
        <span>Petrol</span>
        <b>${petrolOk ? fmtPrice(petrol.price) : '—'}</b>
        <small>${petrolOk ? petrol.name || 'Cheapest petrol station' : 'Petrol data unavailable'}</small>
      </div>
      <div class="city-snapshot-row diesel">
        <span>Diesel</span>
        <b>${dieselOk ? fmtPrice(diesel.price) : '—'}</b>
        <small>${dieselOk ? diesel.name || 'Cheapest diesel station' : 'Diesel data unavailable'}</small>
      </div>
      <div class="city-snapshot-footer"><b>${checked}</b> from UK fuel data</div>`;
  };

  const fetchFuel = async mode => {
    const params = new URLSearchParams({lat:city.lat,lng:city.lng,mode,radius:city.radius || 6,excludeCostco:'false'});
    const res = await fetch(`/api/fuel?${params.toString()}`);
    if(!res.ok) throw new Error(`${mode} request failed`);
    return res.json();
  };

  async function init(){
    try{
      const [petrol,diesel] = await Promise.all([fetchFuel('petrol'),fetchFuel('diesel')]);
      renderCard('petrol', petrol);
      renderCard('diesel', diesel);
      renderTrend(petrol, diesel);
      renderStations(collectStations(petrol, diesel));
      renderTopSummary(petrol, diesel);
      const checked = $('city-last-checked');
      if(checked) checked.textContent = petrol?.updated ? `Checked ${petrol.updated}` : 'Checked daily';
    }catch(err){
      document.querySelectorAll('.city-loading').forEach(el=>{el.textContent='Live city fuel data is temporarily unavailable.'; el.classList.add('city-error');});
      const tbody = $('city-station-rows');
      if(tbody) tbody.innerHTML = `<tr><td colspan="7" class="city-error">Live station data is temporarily unavailable. Please try again later.</td></tr>`;
    }
  }

  document.addEventListener('DOMContentLoaded',init);
})();

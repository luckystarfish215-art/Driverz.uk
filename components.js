class DriverzHeader extends HTMLElement{connectedCallback(){
  this.innerHTML=`<header class="topbar"><div class="topbar-inner"><a class="brand brand-card" href="/">driver<span>z</span>.uk</a><div class="top-actions"><button class="header-icon search-toggle" type="button" id="header-search-toggle" aria-label="Search">⌕</button><button class="header-price-cycle" id="price-cycle" type="button" aria-label="Switch fuel type"><span id="cycle-label">Petrol</span><strong id="cycle-price">--</strong></button><button class="header-icon location-btn" type="button" id="use-location" title="Use my location" aria-label="Use my location">⌖</button><a class="header-icon menu-btn" href="#site-footer" aria-label="Open site links">☰</a></div></div><form class="header-search-panel" id="header-search-panel" hidden><input id="header-search-input" autocomplete="postal-code" placeholder="Search town, city or postcode"><button class="btn light" type="submit">Search</button></form></header>`;
  const modes=['petrol','diesel','ev'];const labels={petrol:'Petrol',diesel:'Diesel',ev:'EV'};
  const renderPrice=()=>{const mode=localStorage.getItem('lastMode')||'petrol';const label=this.querySelector('#cycle-label');const price=this.querySelector('#cycle-price');if(label)label.textContent=labels[mode]||mode;if(price)price.textContent=localStorage.getItem('lastPrice_'+mode)||'--'};
  const panel=this.querySelector('#header-search-panel');const input=this.querySelector('#header-search-input');
  this.querySelector('#header-search-toggle')?.addEventListener('click',()=>{const open=panel.hasAttribute('hidden');if(open){panel.removeAttribute('hidden');requestAnimationFrame(()=>input?.focus())}else{panel.setAttribute('hidden','')}});
  panel?.addEventListener('submit',e=>{e.preventDefault();const q=(input?.value||'').trim();if(!q)return;if(window.DriverzFuel&&typeof window.DriverzFuel.searchPlace==='function'){window.DriverzFuel.searchPlace(q);panel.setAttribute('hidden','')}else{location.href='/?q='+encodeURIComponent(q)+'#fuel-card'}});
  this.querySelector('#use-location')?.addEventListener('click',()=>{if(window.DriverzFuel&&typeof window.DriverzFuel.useLocation==='function'){window.DriverzFuel.useLocation();return}location.href='/?loc=1#fuel-card'});
  this.querySelector('#price-cycle')?.addEventListener('click',()=>{if(window.DriverzFuel&&typeof window.DriverzFuel.cycleMode==='function'){window.DriverzFuel.cycleMode();return}const current=localStorage.getItem('lastMode')||'petrol';const next=modes[(modes.indexOf(current)+1)%modes.length]||'petrol';localStorage.setItem('lastMode',next);renderPrice()});
  renderPrice();window.addEventListener('storage',renderPrice);window.addEventListener('driverz:price-updated',renderPrice);
}}
customElements.define('driverz-header',DriverzHeader);
class DriverzFooter extends HTMLElement{connectedCallback(){const y=new Date().getFullYear();this.innerHTML=`<footer class="site-footer" id="site-footer"><div class="footer-inner"><div class="footer-grid"><div class="footer-col"><h4>Tools</h4><a href="/">Fuel Price Finder</a><a href="/trip-calculator.html">Trip Cost Calculator</a><a href="/cpm-tracker.html">CPM / Mileage Tracker</a><a href="/ev-vs-petrol.html">EV vs Petrol</a><a href="/ev-home-savings.html">EV Home Savings</a><a href="/ev-charge-timer.html">EV Charge Timer</a></div><div class="footer-col"><h4>Guides & Glossary</h4><a href="/fuel-guide.html">Fuel Guide</a><a href="/driving-costs-guide.html">Driving Costs</a><a href="/uk-driving-rules.html">UK Driving Rules</a><a href="/clean-air-zones.html">Clean Air Zones</a><a href="/glossary.html">Glossary</a></div><div class="footer-col"><h4>Driver Services</h4><a href="/emergency.html">Emergency Contacts</a><a href="https://www.gov.uk/check-mot-status" target="_blank" rel="noopener">Check MOT Status ↗</a><a href="https://www.gov.uk/check-vehicle-tax" target="_blank" rel="noopener">Check Vehicle Tax ↗</a><a href="https://www.gov.uk/pay-dartford-crossing-charge" target="_blank" rel="noopener">Pay Dartford Charge ↗</a><a href="https://www.gov.uk/report-pothole" target="_blank" rel="noopener">Report a Pothole ↗</a></div><div class="footer-col"><h4>About</h4><a href="/about.html">About Driverz</a><a href="/contact.html">Contact</a><a href="/advertise.html">Advertise</a><a href="/terms.html">Terms & Privacy</a></div><div class="footer-col"><h4>Quick Cities</h4><a href="/?city=London#fuel-card">London</a><a href="/?city=Birmingham#fuel-card">Birmingham</a><a href="/?city=Manchester#fuel-card">Manchester</a><a href="/?city=Reading#fuel-card">Reading</a><a href="/?city=Glasgow#fuel-card">Glasgow</a></div></div><div class="footer-bottom"><span>© ${y} driverz.uk — Drive smarter.</span><span>Fuel data can change quickly. Always confirm price, availability and opening times before travelling.</span></div></div></footer>`;}}
customElements.define('driverz-footer',DriverzFooter);


function loadDriverzAnalytics(){
  if(window.driverzAnalyticsLoaded)return;
  window.driverzAnalyticsLoaded=true;

  const s=document.createElement('script');
  s.async=true;
  s.src='https://www.googletagmanager.com/gtag/js?id=G-4FBD17BW7V';
  document.head.appendChild(s);

  window.dataLayer=window.dataLayer||[];
  window.gtag=function(){dataLayer.push(arguments);};

  gtag('js', new Date());
  gtag('config', 'G-4FBD17BW7V');
}

class DriverzCookieConsent extends HTMLElement{connectedCallback(){
  const key='driverzCookieChoice';
  const choice=localStorage.getItem(key);

  if(choice==='accept'){
    loadDriverzAnalytics();
    this.remove();
    return;
  }

  if(choice==='reject'){
    window['ga-disable-G-4FBD17BW7V']=true;
    this.remove();
    return;
  }
  this.innerHTML=`<div class="cookie-consent" role="region" aria-label="Privacy and cookie notice">
    <div class="cookie-copy"><strong>Privacy choices</strong><span>Driverz uses cookies and local browser storage for analytics, saved preferences and optional location features.</span></div>
    <div class="cookie-actions">
      <button type="button" class="cookie-btn accept">Accept</button>
      <button type="button" class="cookie-btn reject">Reject</button>
      <a href="/terms.html">Privacy</a>
    </div>
  </div>`;
  const accept=()=>{
    localStorage.setItem(key,'accept');
    loadDriverzAnalytics();
    this.remove();
  };
  const reject=()=>{localStorage.setItem(key,'reject');window['ga-disable-G-4FBD17BW7V']=true;this.remove();};
  this.querySelector('.accept')?.addEventListener('click',accept);
  this.querySelector('.reject')?.addEventListener('click',reject);
}}
customElements.define('driverz-cookie-consent',DriverzCookieConsent);

document.addEventListener('DOMContentLoaded',()=>{
  if(!document.querySelector('driverz-cookie-consent')){
    document.body.appendChild(document.createElement('driverz-cookie-consent'));
  }
});

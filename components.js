
class DriverzHeader extends HTMLElement {
  connectedCallback() {
    this.innerHTML = `
      <header class="topbar">
        <div class="topbar-inner">
          <a class="brand" href="/" aria-label="Driverz UK home">driver<span>z</span>.uk</a>
          <form class="searchbar" id="global-search">
            <input id="global-place" autocomplete="postal-code" placeholder="Search town, city or postcode">
            <button class="btn light" type="submit">Search</button>
            <button class="icon-btn" type="button" id="use-location" title="Use my location" aria-label="Use my location">⌖</button>
          </form>
          <button class="header-price-cycle" id="price-cycle" type="button" aria-label="Switch fuel type">
            <span id="cycle-label">Petrol</span><strong id="cycle-price">--</strong>
          </button>
        </div>
        <nav class="quick-nav" aria-label="Main pages">
          <a href="/#fuel-card">Fuel Finder</a>
          <a href="/utilities.html">Utilities</a>
          <a href="/guides.html">Guides</a>
          <a href="/glossary.html">Glossary</a>
          <a href="/faq.html">FAQ</a>
          <a href="/emergency.html">Emergency</a>
          <a href="/about.html">About</a>
        </nav>
      </header>`;
    const form = this.querySelector('#global-search');
    const input = this.querySelector('#global-place');
    form?.addEventListener('submit', e => {
      e.preventDefault();
      const q = input.value.trim();
      if (q) location.href = '/?q=' + encodeURIComponent(q) + '#fuel-card';
    });
    this.querySelector('#use-location')?.addEventListener('click', () => {
      location.href = '/?loc=1#fuel-card';
    });
  }
}
customElements.define('driverz-header', DriverzHeader);

class DriverzFooter extends HTMLElement {
  connectedCallback() {
    const y = new Date().getFullYear();
    this.innerHTML = `
      <footer class="site-footer">
        <div class="footer-inner">
          <div class="footer-grid">
            <div class="footer-col"><h4>Tools</h4><a href="/">Fuel Price Finder</a><a href="/utilities.html">Utilities Hub</a><a href="/trip-calculator.html">Trip Cost Calculator</a><a href="/cpm-tracker.html">CPM / Mileage Tracker</a><a href="/ev-vs-petrol.html">EV vs Petrol</a><a href="/ev-home-savings.html">EV Home Savings</a><a href="/ev-charge-timer.html">EV Charge Timer</a></div>
            <div class="footer-col"><h4>Guides & Glossary</h4><a href="/guides.html">Guides</a><a href="/fuel-guide.html">Fuel Guide</a><a href="/driving-costs-guide.html">Driving Costs</a><a href="/uk-driving-rules.html">UK Driving Rules</a><a href="/clean-air-zones.html">Clean Air Zones</a><a href="/glossary.html">Glossary</a><a href="/faq.html">FAQ</a></div>
            <div class="footer-col"><h4>Driver Services</h4><a href="/emergency.html">Emergency Contacts</a><a href="https://www.gov.uk/check-mot-status" target="_blank" rel="noopener">Check MOT Status ↗</a><a href="https://www.gov.uk/check-vehicle-tax" target="_blank" rel="noopener">Check Vehicle Tax ↗</a><a href="https://www.gov.uk/pay-dartford-crossing-charge" target="_blank" rel="noopener">Pay Dartford Charge ↗</a><a href="https://www.gov.uk/report-pothole" target="_blank" rel="noopener">Report a Pothole ↗</a></div>
            <div class="footer-col"><h4>About</h4><a href="/about.html">About Driverz</a><a href="/contact.html">Contact</a><a href="/advertise.html">Advertise</a><a href="/terms.html">Terms & Privacy</a></div>
            <div class="footer-col"><h4>Quick Cities</h4><a href="/?city=London#fuel-card">London</a><a href="/?city=Birmingham#fuel-card">Birmingham</a><a href="/?city=Manchester#fuel-card">Manchester</a><a href="/?city=Reading#fuel-card">Reading</a><a href="/?city=Newbury#fuel-card">Newbury</a></div>
          </div>
          <div class="footer-bottom"><span>© ${y} driverz.uk — Drive smarter.</span><span>Fuel data can change quickly. Always confirm price, availability and opening times before travelling.</span></div>
        </div>
      </footer>`;
  }
}
customElements.define('driverz-footer', DriverzFooter);

(function analyticsConsent(){
  const KEY = 'driverz_analytics_consent';
  function loadAnalytics(){
    if (window.__driverzAnalyticsLoaded) return;
    window.__driverzAnalyticsLoaded = true;
    const gtagScript = document.createElement('script');
    gtagScript.async = true;
    gtagScript.src = 'https://www.googletagmanager.com/gtag/js?id=G-4FBD17BW7V';
    document.head.appendChild(gtagScript);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function(){ dataLayer.push(arguments); };
    gtag('js', new Date());
    gtag('config', 'G-4FBD17BW7V');
    window.va = window.va || function(){ (window.vaq = window.vaq || []).push(arguments); };
    const vaScript = document.createElement('script');
    vaScript.defer = true;
    vaScript.src = '/_vercel/insights/script.js';
    document.head.appendChild(vaScript);
  }
  function addBanner(){
    if (localStorage.getItem(KEY)) return;
    const banner = document.createElement('div');
    banner.className = 'cookie-banner';
    banner.innerHTML = `<div><strong>Privacy choices</strong><p>We use essential storage for site preferences. With your consent, we also use Google Analytics and Vercel Analytics to understand site usage.</p></div><div class="cookie-actions"><button class="btn light" type="button" data-cookie="reject">Reject analytics</button><button class="btn accent" type="button" data-cookie="accept">Accept analytics</button></div>`;
    document.body.appendChild(banner);
    banner.addEventListener('click', e => {
      const action = e.target?.dataset?.cookie;
      if (!action) return;
      localStorage.setItem(KEY, action === 'accept' ? 'accepted' : 'rejected');
      banner.remove();
      if (action === 'accept') loadAnalytics();
    });
  }
  if (localStorage.getItem(KEY) === 'accepted') loadAnalytics();
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', addBanner); else addBanner();
})();

document.addEventListener('DOMContentLoaded', () => {
  const shareBtn = document.getElementById('share-page');
  const status = document.getElementById('share-status');
  if (!shareBtn) return;
  shareBtn.addEventListener('click', async () => {
    const shareData = { title: document.title, text: 'Useful UK driver tools from Driverz UK', url: location.href };
    try {
      if (navigator.share) await navigator.share(shareData);
      else { await navigator.clipboard.writeText(location.href); if (status) status.textContent = 'Link copied.'; }
    } catch (err) {
      if (status) status.textContent = 'Share cancelled.';
    }
  });
});

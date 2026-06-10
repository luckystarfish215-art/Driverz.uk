#!/usr/bin/env python3
"""Generate Driverz city landing pages from data/cities.json."""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CITIES_FILE = ROOT / "data" / "cities.json"


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def faq_ld(city: dict) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["q"],
                "acceptedAnswer": {"@type": "Answer", "text": item["a"]},
            }
            for item in city.get("faq", [])
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def breadcrumb_ld(city: dict, slug: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://driverz.uk/"},
            {"@type": "ListItem", "position": 2, "name": city["name"], "item": f"https://driverz.uk/{slug}"},
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def page_html(slug: str, city: dict, all_cities: dict) -> str:
    name = city["name"]
    title = f"{name} petrol and diesel prices today | Driverz.uk"
    desc = city["description"]
    related = [(s, c["name"]) for s, c in all_cities.items() if s != slug]
    faq_items = city.get("faq", [])
    tools = city.get("related_tools", [])

    related_links = "\n".join(f'<a href="/{s}">{esc(n)} fuel prices</a>' for s, n in related[:6])
    faq_html = "\n".join(
        f"""<details>
          <summary>{esc(item['q'])}</summary>
          <p>{esc(item['a'])}</p>
        </details>"""
        for item in faq_items
    )
    tool_cards = "\n".join(
        f"""<div class="city-action-card">
        <div class="icon">{icon}</div>
        <h3>{esc(title)}</h3>
        <p>{esc(copy)}</p>
        <a class="link" href="{href}">{esc(link)} →</a>
      </div>"""
        for icon, title, copy, href, link in [
            ("♡", "Save favourite stations", f"Open the main finder and save the {name} stations you use often.", "/?city=" + esc(name) + "#fuel-card", "Save a station"),
            ("↗", "Get directions", "Open station locations in Google Maps before making a detour.", "/?city=" + esc(name) + "#fuel-card", "Compare now"),
            ("£", "Estimate trip cost", "Use Driverz tools to estimate a journey, fill-up or cost per mile.", "/trip-calculator.html", "Use calculator"),
            ("i", "Understand fuel labels", "Check E10, E5 and diesel terms before choosing a pump.", "/fuel-guide.html", "Read guide"),
        ]
    )
    tool_text = ", ".join(tools) if tools else "Driverz tools"

    city_json = json.dumps({**city, "slug": slug}, ensure_ascii=False)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">

  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}">
  <link rel="canonical" href="https://driverz.uk/{esc(slug)}">

  <meta property="og:type" content="website">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:url" content="https://driverz.uk/{esc(slug)}">
  <meta property="og:image" content="https://driverz.uk/assets/og-cover.jpg">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">

  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(desc)}">
  <meta name="twitter:image" content="https://driverz.uk/assets/og-cover.jpg">

  <link rel="icon" href="/favicon.png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;750;850;950&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/assets/style.css?v=20260609-history1">
  <link rel="stylesheet" href="/assets/city-landing.css?v=20260610-city2">
  <script src="/components.js?v=20260610-citylinks" defer></script>
  <script type="application/ld+json">
{breadcrumb_ld(city, slug)}
  </script>
  <script type="application/ld+json">
{faq_ld(city)}
  </script>
</head>
<body>
  <driverz-header></driverz-header>

  <main class="city-shell">
    <div class="city-inner">
      <section class="city-hero" aria-labelledby="city-title">
        <div class="city-hero-copy">
          <div class="city-breadcrumb"><a href="/">Home</a> › Cities › {esc(name)}</div>
          <div class="eyebrow">UK fuel prices by city</div>
          <h1 id="city-title">{esc(city['headline'])}</h1>
          <p class="city-intro">{esc(desc)}</p>
          <div class="city-hero-meta">
            <span class="chip">{esc(name)}, UK</span>
            <span class="chip">{esc(city.get('region',''))}</span>
            <span class="chip" id="city-last-checked">Checked daily</span>
          </div>
        </div>
        <div class="city-visual" aria-hidden="true">
          <div class="city-map-card">
            <strong>{esc(name)} fuel dashboard</strong>
            <span id="city-top-summary">Loading live petrol and diesel prices…</span>
          </div>
        </div>
      </section>

      <section class="city-section" aria-labelledby="live-summary-title">
        <div class="city-section-head">
          <div>
            <div class="mini-label">Live price summary</div>
            <h2 id="live-summary-title">Cheapest fuel near {esc(name)} today</h2>
          </div>
          <a class="btn light" href="/?city={esc(name)}#fuel-card">Open full finder</a>
        </div>
        <div class="city-live-grid">
          <article class="city-price-card petrol" id="city-petrol-card">
            <div class="city-loading">Loading cheapest petrol…</div>
          </article>
          <article class="city-price-card diesel" id="city-diesel-card">
            <div class="city-loading">Loading cheapest diesel…</div>
          </article>
          <article class="city-price-card">
            <div class="mini-label">Why check today?</div>
            <div class="station">Fuel prices can change quickly.</div>
            <div class="sub">Use the station list, opening times and trend data before making a detour.</div>
            <a class="link" href="/trip-calculator.html">Estimate your trip cost →</a>
          </article>
        </div>
      </section>

      <section class="city-section" aria-labelledby="trend-title">
        <div class="city-section-head">
          <div>
            <div class="mini-label">Price movement</div>
            <h2 id="trend-title">7-day fuel trend in {esc(name)}</h2>
          </div>
        </div>
        <div class="city-trend-layout">
          <div class="city-trend-card" id="city-trend-petrol"><div class="city-loading">Loading petrol trend…</div></div>
          <div class="city-trend-line" id="city-trend-line">Loading 7-day movement…</div>
          <div class="city-trend-card" id="city-trend-diesel"><div class="city-loading">Loading diesel trend…</div></div>
        </div>
      </section>

      <section class="city-section" aria-labelledby="stations-title">
        <div class="city-section-head">
          <div>
            <div class="mini-label">Station list</div>
            <h2 id="stations-title">Top fuel stations in {esc(name)}</h2>
          </div>
          <div class="city-station-tools">
            <a class="btn light" href="/?city={esc(name)}#fuel-card">Compare more</a>
          </div>
        </div>
        <div class="city-table-wrap">
          <table class="city-station-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Station</th>
                <th>Petrol</th>
                <th>Diesel</th>
                <th>Distance</th>
                <th>Open today</th>
                <th>Map</th>
              </tr>
            </thead>
            <tbody id="city-station-rows">
              <tr><td colspan="7" class="city-loading">Loading station list…</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="city-section" aria-labelledby="tools-title">
        <div class="city-section-head">
          <div>
            <div class="mini-label">Save and compare</div>
            <h2 id="tools-title">Useful driver tools for {esc(name)}</h2>
            <p>{esc(tool_text)} can help you decide whether a cheaper station is worth the journey.</p>
          </div>
        </div>
        <div class="city-engage-grid">
          {tool_cards}
        </div>
      </section>

      <section class="city-section" aria-labelledby="faq-title">
        <div class="city-section-head">
          <div>
            <div class="mini-label">Local fuel questions</div>
            <h2 id="faq-title">{esc(name)} fuel prices — FAQs</h2>
          </div>
        </div>
        <div class="city-faq-grid">
          <div class="city-faq-list">
            {faq_html}
          </div>
          <aside class="city-local-note">
            <strong>About driving in {esc(name)}</strong>
            <span>{esc(city.get('local_note',''))}</span>
            <p><a href="/clean-air-zones.html">Check clean air zone guidance →</a></p>
          </aside>
        </div>
      </section>

      <section class="city-section" aria-labelledby="related-cities-title">
        <div class="city-section-head">
          <div>
            <div class="mini-label">More city fuel pages</div>
            <h2 id="related-cities-title">Compare fuel prices in other UK cities</h2>
          </div>
        </div>
        <div class="city-related-cities">
          {related_links}
        </div>
      </section>
    </div>
  </main>

  <driverz-footer></driverz-footer>
  <driverz-cookie-consent></driverz-cookie-consent>

  <script>window.DriverzCity = {city_json};</script>
  <script src="/assets/city-landing.js?v=20260610-city2" defer></script>

  <script>
    window.va = window.va || function () {{
      (window.vaq = window.vaq || []).push(arguments);
    }};
  </script>
  <script defer src="/_vercel/insights/script.js"></script>
</body>
</html>
"""


def main() -> None:
    cities = json.loads(CITIES_FILE.read_text(encoding="utf-8"))
    for slug, city in cities.items():
        (ROOT / f"{slug}.html").write_text(page_html(slug, city, cities), encoding="utf-8")
    print(f"Generated {len(cities)} city pages")


if __name__ == "__main__":
    main()

# Driverz UK

Clean UK driver tools site prepared for Vercel.

Included in this repack:

- Fixed broken references from the previous mixed package.
- Restored one consistent layout using `/assets/style.css`, `/assets/app.js` and `/components.js`.
- Homepage fuel finder with default 3-mile compare list.
- EV connector filter UI.
- Utilities page with share button and clipboard fallback.
- Separate Guides, Glossary, About, FAQ and Emergency pages.
- Cookie consent banner. Google Analytics `G-4FBD17BW7V` and Vercel Analytics only load after analytics consent.
- Clean Vercel configuration with security headers.

Preview locally:

```bash
python3 -m http.server 8080
```

Then open `http://localhost:8080`.

Deploy by uploading this folder to GitHub and connecting it to Vercel.

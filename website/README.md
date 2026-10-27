# getego.ai website

This directory is the new public source for the existing **getego.ai** website, aligned with EgoLabs, Ego, EgoLink, and EgoBase.

## Deployment status

**Published as source; not deployed to getego.ai.** The existing website is hosted on Netlify. The 2026-10-27 publishing session confirmed the existing getego.ai project but browser deployment could not be completed. Publishing this source to GitHub does not update the live website by itself.

After deployment, the maintainer should replace this status with the actual date, source commit, deployment identity, and verification result.

## License

The HTML, CSS, and JavaScript implementation in `index.html` is licensed under Apache-2.0; see [LICENSE](LICENSE). Project documentation follows the repository's CC BY 4.0 license. Brand names and marks are not licensed by these grants.

## Files and preview

`index.html` is a standalone static page with inline CSS and a small language switcher. It requires no build, package installation, external font, image, or script.

Open `index.html` in a browser, or serve this directory with an existing local HTTP server. The default language is English; the **中文** button switches the page to Chinese. `?lang=zh` selects Chinese on initial load. The preference is not stored.

The production publish directory is this `website/` directory. Use the existing Netlify site's verified deployment workflow; do not create another site or alter DNS as part of this content update.

## Content and privacy boundaries

- This page presents an early open development project, with current prototypes and a directional roadmap.
- It replaces the previous Monolith sales presentation and removes unverified product specifications, legal entity/location claims, and absolute capability/privacy statements.
- There is no email form, application form, analytics script, or new data collection in this source. It does not delete any submissions already retained by the existing Netlify account.
- The only JavaScript switches displayed language and reads the optional language query parameter. It does not make network requests, use cookies, or write browser storage.
- GitHub links point to `getegoai`, `getegoai/ego`, and `getegoai/egolink`; confirm the intended repositories are publicly accessible when publishing.
- Hosting-level behavior, headers, injected services, and retained Netlify integrations must be checked separately before making broader privacy claims.

## Release checks

Check the page at mobile and desktop widths, in English and Chinese. Verify the navigation, language buttons, GitHub destinations, keyboard focus, and absence of unintended horizontal overflow. Deploy only through the existing verified site, then check the live domain and record the result above.

Local check on 2026-10-27: Chromium rendered both languages at 1440, 768, 390, and 320 px widths without horizontal overflow or JavaScript errors. The page made no external network requests and contained no forms. Desktop English and mobile Chinese screenshots were visually reviewed. Live GitHub destinations and Netlify deployment remain for the publishing step.

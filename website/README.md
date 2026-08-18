# helpme.green onboarding page

This is the static public onboarding page for helpme.green. It is live at
<https://bnelabs.github.io/helpme.green/> and does not require a build step.

## Preview locally

From the repository root:

```bash
python3 -m http.server 4173 --directory website
```

Open <http://127.0.0.1:4173>.

The page links to the repository's generic Releases page rather than hard-coding draft asset URLs.
The current `v0.1.0-rc.6` candidate is a pre-release: it has automated release checks, but it may
occasionally break, change behavior, or expose unfinished edges. Stable macOS and Windows signing
and notarization remain release gates.

## GitHub Pages

The repository's [Pages workflow](../.github/workflows/pages.yml) publishes the `website/` directory
on every push to `main` and on explicit workflow dispatch. Keep the page's relative asset paths
intact. Publishing the page does not publish local runtime databases, provider keys, raw source
downloads, or model files.

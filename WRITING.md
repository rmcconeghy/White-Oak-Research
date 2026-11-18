# Publishing writing

Each `writing/<slug>/index.html` is the single editable source of an essay, including its permanent page. The Python standard-library script discovers these pages, sorts them by their explicit publication date (newest first), and generates `writing/index.html`. The generated HTML contains the three newest complete articles (newest first) and links to essays older than those three. There is no browser JavaScript or GitHub API dependency.

## Add an essay

1. Copy `writing/why-write/index.html` to `writing/your-new-slug/index.html`. Keep the header, navigation, footer and stylesheet links. Choose a permanent slug; changing it later breaks links.
2. Replace the document `<title>`, article `<h1>` and paragraphs with your own writing. The article needs `data-published="YYYY-MM-DD"` and a visible `<time datetime="YYYY-MM-DD">Month D, YYYY</time>` inside `<p class="essay-meta">`. Use the actual publication date, never the file modification date. Both dates must match. If two essays share a date, the slug in descending alphabetical order breaks the tie.
3. Commit the new essay to `main`. The GitHub Actions workflow runs tests, regenerates the Writing index, and deploys the whole static site. The three newest essays remain fully displayed; older essays automatically move to the linked archive. The build does not commit generated changes back to the repository; the deployed index is always regenerated. Do not edit the generated index directly.

For local preview, run:

```sh
python3 scripts/build_writing.py
python3 -m unittest discover -s tests -v
python3 -m http.server 8000
```

Open `http://localhost:8000/writing/`. Commit the regenerated index too if you want the checked-in preview to match; deployment regenerates it either way. Article words and markup are preserved; relative `href`, `src` and `poster` URLs are adjusted for the landing page's location. Use quoted URL attributes. For responsive images with `srcset`, use site-root or absolute URLs. Styling for both Writing views lives in `writing/writing.css`; the index shell is in `scripts/templates/writing.html`.

## Drafts and dates

An article with `data-status="draft"` is excluded from the index. This does not make its HTML private: any committed draft is still publicly accessible at its URL. Keep private drafts outside this public repository. There is no scheduled publishing: a published essay appears when committed, even if its metadata date is in the future. Missing or invalid publication dates fail the build instead of silently guessing.

The November 14, 2026 date for “0. Why Write?” is verified by its initial publication commit, `524534ca279996755e5af04db141cb9553a6498e` (2026-11-14 20:08 UTC). Later edits do not change that publication date.

## GitHub Pages setup (once)

Under repository **Settings → Pages → Build and deployment**, set **Source** to **GitHub Actions**. `.github/workflows/pages.yml` then builds and deploys on every push to `main`, and can be run manually from the Actions tab. Pull requests run tests and build only. `.nojekyll` remains in the output; Jekyll is not used. No token or additional secret is needed. Existing URLs and other site files are preserved.

If Actions is disabled, enable it for this repository. The workflow needs the standard `github-pages` environment to permit deployments from `main`. If switching from branch deployment after committing this workflow, run **Build and deploy website → Run workflow** once.

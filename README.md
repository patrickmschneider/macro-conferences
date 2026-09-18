# Macro Conference Tracker

Public academic conference tracker for macroeconomics, household finance and pensions. Designed for GitHub Pages, embedded in Patrick Schneider’s Google Sites website.

## Run locally

Python 3.11+ and Node 20+ are sufficient. The frontend has no package dependencies.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm test
npm run build
npm run preview
```

Open http://localhost:8000. The static output is `dist/`.

## Update data

```sh
python -m crawler.run
# A bounded development pilot:
python -m crawler.run --source nber-calls --limit 20
python scripts/build.py
```

The daily workflow targets 06:23 UTC and also supports manual dispatch. It validates before committing and deploying. No model API or paid service is used. Network failures are isolated, retain known records, and appear in the published source status. Pages deployments use GitHub Actions; ordinary code pushes also test and deploy.

## Current scope and limits

This is an initial release, not a claim of comprehensive coverage. Seed records were reviewed against primary announcements on 18 September 2026. Series inventory includes explicitly marked coverage leads. NBER/CEPR extraction is conservative; other sources currently provide leads and evidence rechecks, not general automated publication. Some sources block automated access (CEPR did so in the local pilot). PDF-only announcements require further work. Unparsed candidates are retained in `data/candidates.json`.

A successful fetch is not a successful verification. `last_checked` records attempts; `last_verified` changes only when retained source excerpts still occur or a supported update is reconciled. This verifies the stored critical facts, not every sentence on a source page. Critical conflicts are withheld from open calls; stale records older than 14 days are also excluded from that view. Calendar entries preserve stable UIDs. Revisions/cancellations and disputed records use the same UID; provider refresh delays are outside our control.

## Add or improve a source

Edit `sources.yaml`. `adapter: nber` or `cepr` allows conservative publication; `watch` only collects candidate links. `enabled: false` means an unverified coverage lead. Use a primary announcement source and record the academic inclusion rationale in `data/series.json`. Add concise source fixtures and tests when extending extraction rules. Never enable generic prose extraction on a new site without verifying representative outputs.

Do not run `scripts/seed.py` or `scripts/inventory.py` during updates: they reproduce the original research seed and overwrite current data.

## Google Sites embed

After Pages deployment, open Google Sites → Tools → add a page named “Conference tracker” → Insert → Embed → By URL. Use:

https://patrickmschneider.github.io/macro-conferences/

Choose a wide embed and sufficient height (around 1000 px as a starting point). The page provides an Open full page link for smaller screens. Preview desktop and mobile, then publish the Google Sites page. The tracker updates independently after that one-time embed.

## Data and provenance

- `data/conferences.json`: event editions, distinct submission calls, evidence and update history
- `data/series.json`: established series and coverage leads
- `data/evidence/`: original seed provenance (current evidence also lives on each record)
- `data/run-status.json`: collection results, not an assertion of complete coverage
- `docs/coverage.md`: research gaps and acceptance status
- `prompt.md`: full staged specification

Dates are never extrapolated from annual recurrence. Event access restrictions are separate from open paper submission: NBER’s invitation-only attendance notice does not itself make a CFP closed. Source URLs remain authoritative.

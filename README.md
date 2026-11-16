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
python -m crawler.run --group "Central banks and e61" --limit 150
python scripts/build.py
```

The daily workflow targets 06:23 UTC and also supports manual dispatch. It validates before committing and deploying. No model API or paid service is used. Network failures are isolated, retain known records, and appear in the published source status. Pages deployments use GitHub Actions; ordinary code pushes also test and deploy.

### Alerts

Each run writes `alerts` to `data/run-status.json`, and the workflow keeps one GitHub issue (“Conference tracker needs attention”) in step with them. GitHub emails you when the issue opens or gains a comment. It comments only when a new alert appears and closes itself when alerts clear. An alert means one of:

- a source has failed three runs in a row;
- a call listed in `data/benchmark.json` is missing before its deadline or event;
- no new event has been added for 30 days.

`last_successful_run` advances when at least 75% of sources fetch, so a stalled pipeline shows on the page.

## Current scope and limits

This is not a claim of comprehensive coverage. Discovery has three layers, all deterministic and free:

- **Feeds.** NBER’s public JSON listing, and CEPR’s open events feed (`https://cepr.org/rss/events`). CEPR’s event pages block automated requests, so CEPR events publish dates and location from the feed with the call marked unconfirmed.
- **Institutional listings.** 33 central-bank and e61 listings use the research-event adapter, with per-source URL rules, academic relevance checks, explicit date evidence and bounded discovery.
- **Series index pages.** Sources marked `series: true` watch the one stable page of a known conference series (a society’s events page, an organiser’s conference page) and follow links to new editions by URL pattern. This is how editions such as Miami Macro 2027, CEF 2027, EEA-ESEM 2027 and the Econometric Society meetings are found.

Some sources block automated access; their pages are disabled with a `disabled_reason`. PDF-only announcements require further work. Unparsed candidates are retained in `data/candidates.json`. Bounded work prioritises candidates not yet checked, then the oldest checks; one large calendar cannot consume the whole run. Source status distinguishes a successful fetch from usable candidate discovery. Institutional registration is not a claim of complete event coverage.

A successful fetch is not a successful verification. `last_checked` records attempts; `last_verified` changes only when retained source excerpts still occur or a supported update is reconciled. This verifies the stored critical facts, not every sentence on a source page. Critical conflicts are withheld from open calls; stale records older than 14 days are also excluded from that view. Calendar entries preserve stable UIDs. Revisions/cancellations and disputed records use the same UID; provider refresh delays are outside our control.

## Add or improve a source

**When a call is missed**, the fix is usually one registry entry, not new code. Find the series’ stable index page, meaning the page that will link next year’s edition too (for Miami Macro, the organiser’s `/conferences` page, not the 2027 page). Then add a `series: true` source:

```yaml
- id: miami-macro
  name: Miami Macro
  url: https://www.noahwilliams.xyz/conferences       # stable index page
  adapter: research-events
  series: true
  series_id: miami-macro
  link_pattern: ^/conferences/(?:miamimacro|mfp-miami)\d{2}/?$   # edition URLs only
  include_listing: false     # true when the index page itself carries the current CFP
  event_name: Miami Macro {year}   # optional: for pages with generic headings
  organizer: University of Miami
  topics: [General macro, Monetary policy, Fiscal policy]
  region: North America
  enabled: true
  max_pages: 1
  coverage_group: Conference series
```

Then add the series to `data/series.json` and the missed call to `data/benchmark.json`, so a later regression raises an alert. Check the output with `python -m crawler.run --source <id>` before committing.

Other adapters: `nber`, `cepr-rss` and `research-events` publish conservatively; `watch` only collects candidate links. `enabled: false` with a `disabled_reason` marks a source that is blocked or replaced. Use a primary announcement source and record the academic inclusion rationale in `data/series.json`. Add concise source fixtures and tests when extending extraction rules. Never enable generic prose extraction on a new site without verifying representative outputs.

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

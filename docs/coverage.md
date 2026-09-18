# Coverage and release status

## Research basis

The seed spans general macro, monetary and fiscal policy, international macro, growth, macro-finance, stability, labour, heterogeneity, computation, household finance and retirement-related macro. Current opportunities are uneven across fields; a topic with no open call is not evidence that its conferences are unimportant.

Reviewed primary sources include NBER CFPs and programme pages, CEPR CFPs and series pages, SED, RES, RBA, IMF, CEBRA, SCE, AMS, Netspar, BSE, Texas Tech, CEPAR and IFS. Individual source URLs and inclusion rationales are stored in the dataset. The research seed is not padded with speculative annual editions.

## Coverage gaps

- EEA, Econometric Society, ASSA/AEA, ESSIM, Carnegie-Rochester-NYU, EABCN and LAEF are priority leads requiring further source-level validation and adapters.
- University workshop discovery remains incomplete; the current source registry overweights CEPR and NBER.
- Pension research needs broader coverage beyond Netspar/IPRA and retirement-related NBER calls.
- Australia is represented by RBA and AMS sources; university-specific meetings need expansion.
- Asian and Latin American opportunities are not yet systematically covered.
- CEPR blocked direct requests in this environment; retained seed facts must age visibly rather than be presented as freshly checked.
- PDF extraction and discovery beyond bounded pagination are not implemented.
- A model-based extraction pilot remains conditional on budget/provider decisions; no API cost is currently incurred.

## Staged acceptance

1. Coverage inventory: initial inventory complete; comprehensive coverage gate remains open.
2. Schema and seed: representative seed complete; core invariants validated in Python.
3. Interface: implemented, including filters, series and update status; actual Google Sites embed validation pending.
4. Extraction pilot: NBER live evidence rechecks and JSON-feed discovery work; CEPR blocked locally. Regression tests cover conservative failure cases.
5. Broader automation: daily workflow implemented; watch-only sources and unverified flagship leads remain incomplete.
6. Calendars: generated and tested for dates, UIDs, UTC conversion and folding; real calendar-client subscription testing pending.
7. Deployment: initial Pages deployment succeeded at https://patrickmschneider.github.io/macro-conferences/ . Google Sites embedding requires the site editor; no controllable browser was available in this session.
8. Operational observation: ongoing after deployment. No claim of weeks of unattended operation.

## Maintenance policy

Routine ambiguity never blocks the pipeline. It creates an unconfirmed candidate or stale record instead. These are not daily human-review obligations, but persistent gaps require engineering work. Check source health and discovery coverage periodically during development. Scheduled GitHub workflows may require re-enabling after inactivity; the on-page last-run date makes stalled collection visible.

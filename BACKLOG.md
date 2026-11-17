# Backlog

## Series view with seasons and episodes in the web UI

**Status:** Later. The tvOS app already has a season view; rebuild that here.

Today, episodes of a SERIES library show up as a flat list under "All". The backend already has
`GET /api/series/{library_id}` (with `seasons_count`) and `GET /api/serie/{id}/episodes`
(ordered by season, episode).

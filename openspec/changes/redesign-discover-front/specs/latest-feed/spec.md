## REMOVED Requirements

### Requirement: Latest tab and route
**Reason**: Recent on Discover is the window onto new writing; a second chronological view is not worth a tab (#102).
**Migration**: `/latest` redirects permanently to `/projects`.

### Requirement: Feed entry states
**Reason**: The feed is removed.
**Migration**: Articles render as front-page cards; new projects appear in New Arrivals.

### Requirement: Automatic event sources
**Reason**: Nothing reads feed events once the Latest page and the feed-fed "read next" are gone.
**Migration**: None. Front-page reads query articles directly.

### Requirement: Promoted discussions
**Reason**: No discussion has been promoted in production; the admin action goes with the feed.
**Migration**: None.

### Requirement: Append-only ordering and pagination
**Reason**: The feed is removed.
**Migration**: None.

### Requirement: Freshness-gated lead
**Reason**: Recent leads with the newest front-page article; `Article.recent_until` covers expiry.
**Migration**: The `FEED_LEAD_FRESHNESS_DAYS` setting is deleted.

### Requirement: Entries do not outlive their subject's visibility
**Reason**: The feed is removed; front-page reads apply the same visibility gates directly.
**Migration**: See `project-listing-discover`, Front-page articles.

### Requirement: Responsive layout
**Reason**: The feed is removed.
**Migration**: None.

### Requirement: Empty feed
**Reason**: The feed is removed.
**Migration**: None.

### Requirement: Launch backfill
**Reason**: The feed is removed; `backfill_feed` is deleted with it.
**Migration**: None.

# Frontend Phase 1 Roadmap

## Why this document exists

The backend is now strong enough that frontend work should no longer be treated as:

- "just draw the players on a pitch"

The frontend now needs to become the user-facing analysis layer for a backend that already understands:

- frame queries
- event queries
- replay sequences
- buildup and transition sequences
- aggregate queries
- metric queries
- comparison queries
- report-style outputs

So the frontend phase is about turning those backend capabilities into a clean analysis experience.

## The main frontend question

The question is no longer:

- can the backend answer this?

The question now is:

- how should the user experience the answer?

That means the frontend is not only about visualization.

It is about:

1. visualization
2. explanation
3. reporting
4. interaction
5. result routing

## What the frontend is responsible for

The frontend should handle:

- natural-language query entry
- loading and error states
- result-type detection
- correct output mode selection
- pitch visualization where appropriate
- tables and lists where appropriate
- explanation display
- report display
- replay controls
- comparison display
- drill-down interaction from one result type into another

So the frontend is the presentation and interaction layer for the backend, not only a pitch renderer.

## Important correction: not every query should be shown the same way

Almost every football query can be represented visually in some way.

But that does **not** mean every query should be led by a pitch visualization.

Examples:

- `Show me the away team's second corner`
  - should be visual-first
- `Show me the buildup to the goal`
  - should be replay-first
- `What was the home team's width at minute 5?`
  - should be metric-first with optional pitch support
- `How many away shots were there in period 2?`
  - should be count/list-first, not pitch-first
- `Write a report comparing the transition after the first and second away recoveries`
  - should be report/comparison-first, with optional supporting visuals

So the frontend must be query-family aware.

## The 6 output surfaces we should build

For Phase 1 frontend catch-up, we should build 6 main output surfaces.

### 1. Snapshot View

Use for:

- frame queries
- minute/clock queries
- simple single-event queries

Show:

- pitch
- player positions
- ball position
- event banner if relevant
- resolved frame info
- short explanation

### 2. Replay / Sequence View

Use for:

- event replay
- chained event queries
- buildup queries
- transition queries

Show:

- pitch playback
- frame controls
- timeline
- event markers
- sequence explanation panel
- optional report tab

### 3. Metric View

Use for:

- width
- depth
- line height
- team length
- unit spacing
- shape metrics

Show:

- pitch snapshot
- metric cards
- optional overlays
- short explanation

### 4. Aggregate View

Use for:

- count queries
- list queries
- event inventory queries

Show:

- count cards
- event list or table
- filters summary
- optional drill-down on click

### 5. Comparison View

Use for:

- moment vs moment comparison
- event vs event comparison
- buildup vs buildup comparison
- transition vs transition comparison

Show:

- split layout or two-panel layout
- left vs right summary
- metric deltas
- sequence comparison explanation
- optional linked pitch or replay support

### 6. Explanation / Report View

Use for:

- report-style queries
- explanation-heavy outputs
- comparison writeups

Show:

- formatted explanation block
- formatted report panel
- supporting metadata
- optional associated visual beside it

This is not always a separate page.
It can also be a side panel that complements the other result surfaces.

## The key frontend principle: result routing

The frontend should not try to render every answer using one universal screen.

Instead, it should look at backend metadata and route the result to the correct frontend surface.

The most important backend fields for this are:

- `mode`
- `query_family`
- `has_sequence`
- `sequence_type`
- `has_metrics`
- `has_aggregate`
- `has_comparison`
- `comparison_kind`
- `has_report`
- `has_explanation`

## Frontend result routing map

This is the core routing logic we should build.

### If `mode = frame`

Render:

- Snapshot View

### If `mode = event`

Render:

- Snapshot View
- Replay support if `has_sequence = true`
- Explanation panel

### If `mode = buildup`

Render:

- Replay / Sequence View
- Buildup explanation panel
- Report panel if `has_report = true`

### If `mode = transition`

Render:

- Replay / Sequence View
- Transition explanation panel
- Report panel if `has_report = true`

### If `mode = aggregate`

Render:

- Aggregate View
- Count card or event table depending on aggregate type
- Explanation panel

### If `mode = comparison`

Render:

- Comparison View
- Explanation panel
- Report panel if `has_report = true`

## What the user should see for each backend query family

This is the practical mapping.

### Frame / minute query

Examples:

- `Show me frame 1500`
- `Show me minute 5`

User sees:

- pitch snapshot
- frame info
- optional metric cards if included
- short explanation

### Single event query

Examples:

- `Show me the away team's second corner`
- `Show me the first yellow card`

User sees:

- event card
- pitch at event frame
- replay timeline
- nearby event markers
- explanation

### Ordered / relative event query

Examples:

- `Show me the last goal before 70:00`
- `Show me the first pass after 2:30`

User sees:

- same event-oriented layout as above
- plus clearer emphasis on which moment was selected and why

### Aggregate count query

Examples:

- `How many away shots were there in period 2?`

User sees:

- count card
- filters summary
- explanation

Optional follow-up interaction:

- button to show the matching list

### Aggregate list query

Examples:

- `List all home set pieces in period 2`
- `Show all away recoveries`

User sees:

- event list or table
- filters summary
- explanation

Optional follow-up interaction:

- click a row to open Snapshot or Replay View for that event

### Metric query

Examples:

- `What was the home team's width at minute 5?`
- `What was the away team's unit spacing at the second corner?`

User sees:

- pitch snapshot
- metric cards
- explanation

Optional enhancement later:

- overlays for line height, width, hull shape, and spacing

### Chained event query

Examples:

- `Show me the first shot after the away team's second corner`

User sees:

- resolved target event replay
- anchor event summary
- explanation of how the target was resolved relative to the anchor

### Buildup query

Examples:

- `Show me the buildup to the goal`
- `Write a report on the buildup to the goal`

User sees:

- longer replay clip
- event-chain explanation
- report panel if requested

### Transition query

Examples:

- `Show me the transition after the first away recovery`
- `Write a report on the counterattack after the first away recovery`

User sees:

- transition replay
- continuation vs interruption explanation
- report panel if requested

### Comparison query

Examples:

- `Compare minute 5 and minute 10`
- `Compare the first and second corners`

User sees:

- comparison layout
- metric delta summary
- explanation

### Sequence comparison query

Examples:

- `Compare the buildup to the first and second corners`
- `Compare the transition after the first and second away recoveries`

User sees:

- comparison layout
- sequence comparison explanation
- metric delta summary
- optional side-by-side sequence support later

### Report query

Examples:

- `Write a report on away shots in period 2`
- `Write a report comparing minute 5 and minute 10`

User sees:

- report panel
- supporting visual or list beside it where appropriate

## What the frontend should not do

We should avoid these mistakes:

### 1. One giant universal pitch page

This would force:

- count queries
- list queries
- report queries
- comparison queries

into a visualization that is not always the right primary answer.

### 2. Treating all results as snapshots

Some results are:

- sequence-first
- metric-first
- list-first
- report-first

The frontend must respect that.

### 3. Hiding the explanation/report layer

The current backend already returns grounded explanations and reports.
The frontend should expose that, not ignore it.

### 4. Over-optimizing visuals before routing is stable

The first frontend job is correct result-mode handling.
Fancy visual polish should come after the routing and UI surfaces are correct.

## The frontend architecture we should build

Phase 1 frontend should have these parts.

### 1. Query workspace shell

This contains:

- query input
- submit action
- loading state
- error state
- active result area

### 2. Result router

This is the most important new frontend layer.

It reads backend `context` and decides which result surface to render.

### 3. Reusable UI primitives

We should build reusable frontend pieces for:

- pitch canvas
- replay controls
- event strip
- metric cards
- aggregate table
- explanation panel
- report panel
- comparison layout

### 4. Query-family result screens

We then assemble the primitives into:

- Snapshot screen
- Replay / Sequence screen
- Aggregate screen
- Comparison screen

## Suggested build order

This is the safest order for frontend Phase 1.

### Step 1. Result routing layer

Build the component that reads:

- `mode`
- `query_family`
- `has_sequence`
- `has_comparison`
- `has_aggregate`
- `has_report`

and chooses which screen to render.

### Step 2. Snapshot + event screen

Support:

- frame queries
- minute queries
- single-event queries

### Step 3. Replay / sequence screen

Support:

- event replay
- buildup
- transition
- chained event queries

### Step 4. Aggregate screen

Support:

- counts
- lists
- table interactions

### Step 5. Comparison screen

Support:

- moment comparison
- sequence comparison

### Step 6. Report and explanation panels

Support:

- report-first outputs
- side-panel explanation
- comparison writeups

## What Phase 1 frontend completion should mean

Frontend Phase 1 is complete when:

1. every major backend query family has a correct primary UI surface
2. every result type can be displayed without forcing everything into one pitch view
3. explanation and report outputs are visible, not hidden
4. aggregate and comparison results have dedicated displays
5. replay-capable queries feel interactive and understandable

## What comes after frontend Phase 1

After the catch-up phase, the next improvements can include:

- better comparison visuals
- richer pitch overlays
- sequence thumbnails
- report export workflows
- stronger UI polish
- later frontend support for deeper Phase 2 backend capabilities

## One-line summary

Frontend Phase 1 is not just about drawing football positions.
It is about building a result-aware analysis interface that chooses the right experience for each backend query family: snapshot, replay, metric, aggregate, comparison, or report.

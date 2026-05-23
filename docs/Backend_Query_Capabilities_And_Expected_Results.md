# Backend Query Capabilities And Expected Results

## Why this document exists

At this stage, the backend is no longer just a collection of scripts.
It is a real football query engine.

So the important practical question is:

- what can I ask it right now?
- what will it return or do?
- what kinds of questions are weak, unsupported, or likely to fail?

This document answers that directly.

## The backend output shape at a high level

Almost every successful backend query returns a dictionary with this top-level shape:

```python
{
  "coordinates": ...,
  "sequence": ...,
  "context": ...
}
```

### `coordinates`

This is the tracking snapshot for one resolved frame.

It usually contains:

- Home player x/y coordinates
- Away player x/y coordinates
- ball x/y coordinates

If the query is aggregate-only, this may be empty.

### `sequence`

This is optional.
It is present when the query resolves to a replay-style or sequence-style answer.

Possible sequence types:

- `event`
- `buildup`
- `transition`

When present, it usually contains:

- `event_frame`
- `start_frame`
- `end_frame`
- `sequence_type`
- `frames`
- `events`

### `context`

This is where the query meaning and backend interpretation live.

Common fields now include:

- `mode`
- `query_family`
- `response_contract_version`
- `frame`
- `event`
- `anchor_event`
- `metrics`
- `aggregate`
- `comparison`
- `explanation`
- `report`

And stable flags such as:

- `has_event`
- `has_anchor_event`
- `has_metrics`
- `has_sequence`
- `has_aggregate`
- `has_comparison`
- `has_report`
- `has_explanation`

So the backend is not just returning text.
It is returning structured football results plus explanation metadata.

## Query families that work well right now

These are the main families of questions the backend currently supports well.

---

## 1. Direct frame queries

### Example questions

- `Show me frame 1500`
- `Give me frame 86036`

### What the backend does

- resolves the exact frame directly
- fetches tracking coordinates for that frame
- does not need event lookup

### Expected result

- `coordinates`: full player + ball snapshot for that frame
- `sequence`: `None`
- `context.mode`: `frame`
- `context.frame`: exact frame number
- `context.event`: `None`

### If asked with a metric

Examples:

- `What was the home team's width at frame 1500?`
- `Show me team shape at frame 1500`

Expected result:

- same frame coordinates
- `context.metrics` populated
- explanation includes metric values

---

## 2. Time and clock queries

### Example questions

- `Show me minute 5`
- `Show me 2:30`
- `What was the home team's line height at minute 5?`

### What the backend does

- converts minute/clock to frame locally using 25 fps
- fetches the resolved frame
- optionally computes metrics for that frame

### Expected result

- behaves like a frame query after conversion
- `context.mode`: `frame`
- `context.frame`: resolved numeric frame
- `coordinates`: snapshot at that frame
- `metrics` present if the question asks for them

### Important note

This is deterministic and reliable because the minute-to-frame conversion is done locally, not left to the LLM.

---

## 3. Single event queries

### Example questions

- `Show me the away team's second corner`
- `Show me the last goal before 70:00`
- `Show me the first saved shot`
- `Show me the first yellow card`

### Supported event words right now

The router has explicit patterns for:

- goal
- saved shot / shot saved / saved
- shot
- corner / corner kick
- free kick
- kick off
- throw in
- penalty
- offside
- ball out
- ball win / ball won / win the ball
- ball loss / lost the ball / lose the ball / turnover
- recovery
- interception
- pass
- yellow card / card

### What the backend does

- resolves the event using team/order/relation filters when present
- gets the exact event frame
- fetches coordinates for that frame
- fetches a short replay window around that event

### Expected result

- `coordinates`: snapshot at the event frame
- `sequence`: short replay window around the event
- `sequence.sequence_type`: `event`
- `context.mode`: `event`
- `context.event`: resolved event metadata
- `context.frame`: event frame
- explanation describes the event and what changed in the replay clip

### If frontend is involved

Expected frontend behavior would be:

- plot the resolved frame
- allow replay through the short event window
- show nearby events and explanation text

---

## 4. Ordered event queries

### Example questions

- `Show me the first shot`
- `Show me the second corner`
- `Show me the last goal`
- `Show me the latest free kick`

### What the backend does

- uses first/second/third/fourth/fifth/last
- resolves the correct occurrence in the ordered event stream

### Expected result

Same result shape as a normal single event query:

- exact event
- exact event frame
- replay window
- explanation

### Known limit

Only the first five ordinal words are explicitly supported as words.
Numeric ordinal forms like `6th corner` may work through generic ordinal parsing, but this is not as intentionally supported as first through fifth.

---

## 5. Relative event queries

### Example questions

- `Show me the last goal before 70:00`
- `Show me the first pass after 2:30`
- `Show me the shot around minute 15`

### What the backend does

- resolves the time to a frame if needed
- applies `before`, `after`, or `around`
- finds the matching event relative to that anchor

### Expected result

- behaves like an event query once resolved
- `context.event` describes the matched event
- `context.frame` is the resolved target frame
- `sequence` is the event replay window

### Known limit

Relative queries currently work best when the anchor is a time or frame.
More abstract relative phrasing can work only if the router can decompose it into an event chain it already understands.

---

## 6. Aggregate count queries

### Example questions

- `How many away shots were there in period 2?`
- `Count home recoveries in the attacking third`
- `Number of set pieces in the second half`

### What the backend does

- resolves filters
- runs a count query over the events parquet

### Expected result

- `coordinates`: empty
- `sequence`: `None`
- `context.mode`: `aggregate`
- `context.aggregate.query_type`: `count`
- `context.aggregate.count`: numeric result
- explanation summarizes the count

### Important note

These are not replay outputs.
They are event-inventory outputs.

---

## 7. Aggregate list queries

### Example questions

- `List all home set pieces in period 2`
- `Show all away shots in the final third`
- `List every away recovery`

### What the backend does

- resolves filters
- returns a list of matching event records

### Expected result

- `coordinates`: empty
- `sequence`: `None`
- `context.mode`: `aggregate`
- `context.aggregate.query_type`: `list`
- `context.aggregate.events`: list of matching events
- `context.aggregate.count`: length of the list

### If frontend is involved

Expected frontend behavior would be:

- table view
- event list view
- clickable items that can trigger separate event or replay queries later

---

## 8. Spatially filtered queries

### Example questions

- `Show me away shots in the attacking third`
- `How many passes happened in the penalty box?`
- `List recoveries on the left wing`

### Supported zone language right now

- attacking third / final third
- middle third
- defensive third
- left wing / left flank
- right wing / right flank
- central channel / centre channel / center channel / central area
- penalty box / the box / into the box / in the box

### What the backend does

- turns the zone into a normalized pitch-zone filter
- applies that during event retrieval / count / list

### Expected result

- if it is an event query: event + replay window
- if it is a count query: aggregate count
- if it is a list query: aggregate list

### Known limit

These are event-start-position filters, not deep continuous spatial reasoning over the full tracking sequence.

---

## 9. Phase-of-play queries

### Example questions

- `Show me the first pass in attacking transition`
- `How many away ball losses were there in defensive transition?`
- `List all set pieces`

### Supported phase words right now

- set piece
- in possession
- out of possession
- attacking transition
- attack transition
- counterattack / counter attack
- defensive transition
- transition to defense / defence

### What the backend does

- maps the phrase to a normalized phase label
- filters the event stream using the phase field derived in DuckDB

### Expected result

- event query -> event + replay window
- aggregate query -> count or list

### Known limit

These phase labels are rule-derived from the event sequence.
They are useful, but they are not yet a deep possession-phase model.

---

## 10. Metric queries

### Example questions

- `What was the home team's width at minute 5?`
- `What was the away team's unit spacing at the second corner?`
- `Show me team shape at frame 1500`
- `What was the nearest teammate distance for Home at minute 10?`

### Supported metric language right now

- width
- depth
- line height / line-height
- unit spacing / team spacing / line spacing
- team length / length
- nearest teammate distance / nearest distance
- compact / compactness
- hull area / hull
- centroid / center / centre
- shape metrics / metrics / team shape / shape

### What the backend does

- resolves the moment first
- computes metrics for that resolved frame

### Expected result

- coordinates for the resolved frame
- `context.metrics` populated
- explanation includes the metric and often a simple tactical reading

### Known limit

These are frame-level structural metrics.
They are not yet continuous speed/acceleration or biometrics-style outputs.

---

## 11. Chained event queries

### Example questions

- `Show me the first shot after the away team's second corner`
- `Show me the first pass before the first goal`

### What the backend does

- resolves the anchor event
- uses that anchor frame to resolve the target event
- fetches the target frame and its replay window

### Expected result

- `context.mode`: `sequence_event`
- `context.event`: resolved target event
- `context.anchor_event`: resolved anchor event
- `coordinates`: target event frame
- `sequence`: target event replay window

### Known limit

This is still event-to-event chaining, not general multi-hop tactical reasoning.

---

## 12. Buildup queries

### Example questions

- `Show me the buildup to the goal`
- `Show me the buildup to the away team's second corner`
- `Write a report on the buildup to the goal`

### What the backend does

- resolves the target event
- fetches a longer pre-event window
- segments the sequence into lead-in structure
- builds explanation/report text from the event chain plus structure metrics

### Expected result

- `context.mode`: `buildup`
- `coordinates`: target event frame
- `sequence.sequence_type`: `buildup`
- `context.sequence_segments`: lead-in segmentation
- explanation talks about:
  - event mix
  - same-team lead-in events
  - opponent interruption or lack of it
  - final pre-event action
  - shape changes
  - higher-level interpretation

### If frontend is involved

Expected frontend behavior would be:

- replay the buildup window
- mark the key event frame
- show event-chain explanation beside the replay

---

## 13. Transition queries

### Example questions

- `Show me the transition after the first away recovery`
- `Write a report on the counterattack after the first away recovery`
- `Show me the transition after the first home ball loss`

### What the backend does

- resolves the trigger event
- fetches a post-trigger transition window
- segments continuation vs interruption
- summarizes same-team follow-up events

### Expected result

- `context.mode`: `transition`
- `coordinates`: trigger frame
- `sequence.sequence_type`: `transition`
- `context.transition_summary`: chain summary
- `context.sequence_segments`: segmented post-trigger flow
- explanation talks about:
  - number of continuation actions
  - whether opponent interrupted
  - whether a shot arrived quickly
  - shape changes
  - higher-level interpretation

---

## 14. Comparison queries

### Example questions

- `Compare the first and second corners`
- `Compare minute 5 and minute 10`
- `Write a report comparing minute 5 and minute 10`

### What the backend does

- resolves both references
- computes frame-structure deltas between them

### Expected result

- `context.mode`: `comparison`
- `coordinates`: coordinates of the right-hand moment
- `context.comparison`: full comparison payload
- explanation compares the two moments

### Important note

For comparison queries, the main answer is in `context.comparison`, not just in `coordinates`.
So a frontend should treat this as a comparison result, not as a plain snapshot.

---

## 15. Sequence-level comparison queries

### Example questions

- `Compare the buildup to the first and second corners`
- `Compare the transition after the first and second away recoveries`
- `Write a report comparing the transition after the first and second away recoveries`

### What the backend does

- resolves both moments
- if buildup is requested:
  - fetches buildup windows for both
  - segments both sequences
- if transition is requested:
  - fetches transition windows for both
  - segments both sequences
- compares the segmented counts

### Expected result

- `context.mode`: `comparison`
- `context.comparison.comparison_kind`:
  - `buildup_sequence`
  - `transition_sequence`
- `context.comparison.sequence_comparison`: sequence delta payload
- explanation includes both:
  - frame/shape comparison
  - sequence-comparison interpretation

### Known limit

This is still a first-level sequence comparison.
It compares meaningful counts and interruptions, but it is not yet a deep tactical sequence model.

---

## 16. Report-style queries

### Example questions

- `Write a short report on the away team's second corner`
- `Write a report on away shots in period 2`
- `Write a report on the buildup to the goal`
- `Write a report comparing the transition after the first and second away recoveries`

### What the backend does

- runs the underlying query normally
- adds `context.report`

### Expected result

- same structured result as the normal query
- plus:
  - `context.has_report = True`
  - `context.report`: markdown-like plain text summary

### Important note

The report does not replace the structured output.
It sits on top of it.

---

## What kinds of questions are weak, partial, or likely to behave poorly?

These are the current weak zones.

## 1. Player-specific natural language questions

### Examples

- `Where was Player10 at minute 5?`
- `Show me the winger's movement`
- `Compare the center back and fullback spacing`

### Why weak

- the router does not currently parse player IDs/names/roles as query entities
- team-level structure is supported more than individual-role reasoning

### Likely result

- may fall back badly
- may return a broader frame/event result instead of player-specific analysis
- may fail to answer meaningfully

---

## 2. Very fuzzy tactical questions

### Examples

- `Show me when the press was effective`
- `Where did they look dangerous?`
- `Show me when the defense was nervous`

### Why weak

- the backend does not yet have learned tactical classifiers
- there is no deep pressure model
- there is no danger model beyond simple event/sequence proxies

### Likely result

- either no direct match
- or a generic event-based interpretation that is much weaker than the question intends

---

## 3. Broad multi-hop reasoning questions

### Examples

- `Show me the attack that started from a recovery in the defensive third and ended in a shot after switching play`
- `Find the best transition where the winger pinned the fullback`

### Why weak

- the system has first-level event chaining
- it does not yet do long multi-step tactical reasoning with multiple constraints and latent football concepts

### Likely result

- partial resolution if the phrasing lines up with supported patterns
- otherwise weak or failed answer

---

## 4. Continuous kinematic or biometric questions

### Examples

- `Who accelerated the fastest in the last 10 minutes?`
- `Who looked fatigued?`
- `Show me sprint load by player`

### Why weak

- there is no current speed/acceleration/fatigue computation layer in the backend query API
- the current metrics are structural, not biomechanical

### Likely result

- unsupported
- may return unrelated frame/event output if phrased ambiguously

---

## 5. Free-form explanation questions with no resolvable anchor

### Examples

- `Why were they bad?`
- `Explain the tactics of the match`
- `Tell me the full story of the game`

### Why weak

- the backend is still query-and-anchor driven
- it works best when the question resolves to a moment, event family, or comparison target

### Likely result

- may fail to resolve usefully
- may need to be broken down into smaller event/moment queries

---

## What kinds of queries will likely produce errors or empty outputs?

## 1. Contradictory or impossible filters

### Examples

- `Show me the sixth goal before minute 2`
- `Show me a home penalty in period 2` if none exists

### Likely behavior

- backend event lookup raises no-match error
- over WebSocket, this will usually come back as an error payload

---

## 2. Out-of-range frame/time queries

### Examples

- `Show me frame 999999`
- `Show me minute 500`

### Likely behavior

- frame resolves
- tracking lookup returns empty coordinates if the frame does not exist

### Important note

This is different from an event lookup failure.
Event lookup usually errors on no match.
Raw frame lookup can simply return an empty coordinate map.

---

## 3. Unsupported event words

### Examples

- `Show me the first dribble`
- `Show me the first tackle`
- `Show me the first assist`

### Why

These are not part of the explicit router event patterns right now.

### Likely behavior

- may not resolve correctly
- may fall back to Groq tool-calling, which is less predictable than the deterministic routes

---

## Edge-case behavior to expect

## 1. Ambiguous phrasing

Example:

- `Show me the first event after the first event`

Behavior:

- if the router can still map both sides to concrete event hints, it may resolve
- otherwise it becomes unreliable

## 2. Queries that mix families

Example:

- `Write a report comparing the buildup to the first and second corners`

Behavior:

- this now works
- the backend routes it as a comparison query with sequence comparison
- report text is layered on top

## 3. Aggregate queries with report wording

Example:

- `Write a report on away shots in period 2`

Behavior:

- backend treats it as aggregate list/count style plus report
- no replay or frame coordinates are required

## 4. Comparison queries

Important behavior:

- `coordinates` usually represent the right-side moment
- the actual comparison meaning lives in `context.comparison`

So the frontend or caller should not treat comparison results as if they were plain snapshots.

## 5. Sequence queries without enough structure

Example:

- `Show me what happened after that`

Behavior:

- likely fails unless a concrete event/frame anchor exists in the query itself

---

## Best kinds of questions to ask right now

If you want the backend to shine, ask questions like:

- exact frame/time questions
- concrete football event questions
- ordered event questions
- relative event questions with a clear time/frame anchor
- aggregate event inventory questions
- spatially filtered event questions
- phase-filtered event questions
- team shape metric questions
- buildup questions
- transition questions
- moment comparison questions
- buildup/transition comparison questions
- report versions of any of the above

---

## Short final summary

Right now, the backend is strongest when the question can be reduced to one of these:

- a frame
- a time
- an event
- an ordered event
- a relative event
- an aggregate event family
- a buildup or transition sequence
- a comparison between two moments or two short sequences
- a team-structure metric at a resolved moment

It is weaker when the question depends on:

- player-role reasoning
- fuzzy football semantics
- deep tactical interpretation with no concrete anchor
- continuous physical modelling
- very long multi-hop football reasoning

So the backend is already a strong football retrieval and sequence-analysis system, but not yet a full open-ended football reasoning brain.

# System Query Capabilities And Expected Results

## Why this document exists

This document is the system-level companion to:

- `Backend_Query_Capabilities_And_Expected_Results.md`

That backend document explains what the backend can resolve and return.

This document explains something slightly different:

- what kinds of football questions the **full system** can handle right now
- what kind of result the **user** should expect to see
- what the answer looks like from an end-to-end usability point of view

So this is not mainly about code, errors, or debugging.

It is about:

- input
- expected output
- expected user experience

## The system at a high level

At the current stage, the system can take a natural-language football query and turn it into one of these output experiences:

1. `Snapshot result`
2. `Replay / sequence result`
3. `Metric result`
4. `Aggregate result`
5. `Comparison result`
6. `Report / explanation result`

That means the system is no longer just:

- "show me dots on a pitch"

It is now:

- query understanding
- football data retrieval
- result routing
- visualization
- explanation
- report support

## The 6 main output modes

These are the core result types a user can experience.

### 1. Snapshot View

Use this when the query resolves to one main frame.

Examples:

- `Show me frame 1500`
- `Show me minute 5`
- `Show me the first yellow card`

Expected user experience:

- a pitch snapshot
- player and ball locations
- frame/event summary
- optional metric cards if requested

### 2. Replay / Sequence View

Use this when the query resolves to a short clip around a football moment.

Examples:

- `Show me the away team's second corner`
- `Show me the buildup to the goal`
- `Show me the transition after the first away recovery`

Expected user experience:

- a replayable pitch view
- sequence slider
- clip start, event point, and clip end
- nearby event markers
- sequence explanation

### 3. Metric View

Use this when the query asks for team shape or structural numbers.

Examples:

- `What was the home team's width at minute 5?`
- `What was the away team's line height at the second corner?`

Expected user experience:

- a resolved pitch moment
- metric cards
- explanation of what the metric means in that moment

### 4. Aggregate View

Use this when the query asks for counts or lists.

Examples:

- `How many away shots were there in period 2?`
- `List all home set pieces in period 2`

Expected user experience:

- count summary or event table
- filters summary
- optional drill-down actions into individual events

### 5. Comparison View

Use this when the query asks for one moment or one sequence to be compared to another.

Examples:

- `Compare minute 5 and minute 10`
- `Compare the first and second corners`
- `Compare the transition after the first and second away recoveries`

Expected user experience:

- left vs right moment context
- metric deltas
- comparison explanation
- optional drill-down into each side

### 6. Report / Explanation View

Use this when the query explicitly asks for a report, summary, or explanation-heavy answer.

Examples:

- `Write a report on the away team's second corner`
- `Write a report comparing the transition after the first and second away recoveries`

Expected user experience:

- readable explanation text
- formatted report panel
- supporting result view beside it where relevant

## Query families the full system currently supports

Below is the practical system-level map.

For each family:

- what kind of question the user can ask
- what the system resolves
- what the user should see

---

## 1. Direct frame queries

### Example inputs

- `Show me frame 1500`
- `Give me frame 86036`

### What the system resolves

- exact frame
- player and ball coordinates for that frame

### Expected result

- `Primary result type`: Snapshot View
- `What the user sees`:
  - pitch snapshot
  - all tracked entities at that frame
  - frame number
  - short explanation that this was a direct frame lookup

### What to validate during usability testing

- does the pitch load immediately?
- does the frame number match the request?
- are all players and the ball shown?

---

## 2. Time and clock queries

### Example inputs

- `Show me minute 5`
- `Show me 2:30`

### What the system resolves

- local conversion from time to frame
- exact frame retrieval

### Expected result

- `Primary result type`: Snapshot View
- `What the user sees`:
  - same experience as a frame query
  - pitch snapshot
  - resolved frame
  - explanation tied to the requested time

### What to validate

- is the time interpreted correctly?
- does the user understand that time was converted into a frame?

---

## 3. Single event queries

### Example inputs

- `Show me the away team's second corner`
- `Show me the first yellow card`
- `Show me the last goal before 70:00`

### What the system resolves

- matching event
- event frame
- replay window around the event

### Expected result

- `Primary result type`: Replay / Sequence View
- `What the user sees`:
  - pitch at the event moment
  - replay timeline
  - event description
  - nearby event markers
  - explanation

### What to validate

- does the chosen event match the wording?
- does the replay clip feel centered around the event?
- does the explanation clearly say what was matched?

---

## 4. Ordered event queries

### Example inputs

- `Show me the first shot`
- `Show me the second corner`
- `Show me the last goal`

### What the system resolves

- occurrence order within the event stream

### Expected result

- `Primary result type`: Replay / Sequence View
- `What the user sees`:
  - same result shape as a single event query
  - clear event label
  - clear ordering outcome

### What to validate

- does the user feel confident that "first", "second", or "last" was respected?

---

## 5. Relative event queries

### Example inputs

- `Show me the last goal before 70:00`
- `Show me the first pass after 2:30`
- `Show me the shot around minute 15`

### What the system resolves

- anchor time/frame
- event relative to that anchor

### Expected result

- `Primary result type`: Replay / Sequence View
- `What the user sees`:
  - resolved event
  - replay clip
  - explanation of the relative relation

### What to validate

- is the meaning of before/after/around reflected clearly?
- does the result feel intuitively correct to the user?

---

## 6. Metric queries

### Example inputs

- `What was the home team's width at minute 5?`
- `What was the away team's line height at the second corner?`
- `Show me team shape at frame 1500`

### What the system resolves

- a football moment first
- then frame-level metrics at that moment

### Expected result

- `Primary result type`: Metric View with pitch support
- `What the user sees`:
  - pitch snapshot at the resolved moment
  - metric cards
  - explanation of the values

### What to validate

- are the metrics readable?
- does the pitch snapshot help explain the metric?
- does the explanation connect the number to football meaning?

---

## 7. Aggregate count queries

### Example inputs

- `How many away shots were there in period 2?`
- `Count home recoveries in the attacking third`

### What the system resolves

- filtered event family
- numeric count

### Expected result

- `Primary result type`: Aggregate View
- `What the user sees`:
  - count summary
  - filter summary
  - explanation text

### What to validate

- does the result feel like a count answer, not a broken visualization?
- are the filters visible enough for the user to trust the count?

---

## 8. Aggregate list queries

### Example inputs

- `List all home set pieces in period 2`
- `Show all away shots in the final third`

### What the system resolves

- filtered event list

### Expected result

- `Primary result type`: Aggregate View
- `What the user sees`:
  - event table
  - filter summary
  - aggregate insight summaries
  - drill-down actions to open a frame

### What to validate

- can the user scan the list quickly?
- is it easy to move from a list result into an individual event?

---

## 9. Spatially filtered queries

### Example inputs

- `Show me away shots in the attacking third`
- `List recoveries on the left wing`
- `How many passes happened in the box?`

### What the system resolves

- normalized pitch-zone filter
- then event, count, or list result

### Expected result

- `Primary result type`:
  - Replay / Sequence View if one event is returned
  - Aggregate View if count/list is returned

### What the user sees

- zone-aware result, but not full continuous spatial heatmaps
- filter summary showing the zone

### What to validate

- does the system make the zone filter visible enough?
- does the user understand this is event-position filtering?

---

## 10. Phase-of-play queries

### Example inputs

- `Show me the first pass in attacking transition`
- `How many away ball losses were there in defensive transition?`
- `List all set pieces`

### What the system resolves

- normalized phase filter
- then event, count, or list result

### Expected result

- `Primary result type`:
  - Replay / Sequence View for event answers
  - Aggregate View for count/list answers

### What the user sees

- football moment or event inventory
- phase context surfaced in the result

### What to validate

- does the user understand what phase was applied?
- does the phase-aware result feel useful?

---

## 11. Chained event queries

### Example inputs

- `Show me the first shot after the away team's second corner`
- `Show me the first pass before the first goal`

### What the system resolves

- anchor event
- target event relative to anchor

### Expected result

- `Primary result type`: Replay / Sequence View
- `What the user sees`:
  - target event result
  - anchor event context card
  - explanation showing the chain logic

### What to validate

- can the user understand both:
  - what the anchor was
  - what the resolved target was

---

## 12. Buildup queries

### Example inputs

- `Show me the buildup to the goal`
- `Show me the buildup to the away team's second corner`
- `Write a report on the buildup to the goal`

### What the system resolves

- target event
- longer lead-in sequence
- segmented event chain before the moment

### Expected result

- `Primary result type`: Replay / Sequence View + Report / Explanation View
- `What the user sees`:
  - longer pre-event replay
  - segmentation summary
  - event-mix breakdown
  - highlight cards for key events
  - explanation
  - report if requested

### What to validate

- does the user understand how the attack developed?
- do the sequence panels make the replay easier to read?

---

## 13. Transition queries

### Example inputs

- `Show me the transition after the first away recovery`
- `Write a report on the counterattack after the first away recovery`
- `Show me the transition after the first home ball loss`

### What the system resolves

- transition trigger
- post-trigger sequence window
- continuation/interruption summary

### Expected result

- `Primary result type`: Replay / Sequence View + Report / Explanation View
- `What the user sees`:
  - transition replay
  - transition summary card
  - event segmentation
  - event-mix breakdown
  - highlight cards
  - explanation
  - report if requested

### What to validate

- does the user understand what happened immediately after the trigger?
- does the transition summary feel football-meaningful?

---

## 14. Comparison queries

### Example inputs

- `Compare minute 5 and minute 10`
- `Compare the first and second corners`
- `Write a report comparing minute 5 and minute 10`

### What the system resolves

- left moment
- right moment
- structural differences

### Expected result

- `Primary result type`: Comparison View
- `What the user sees`:
  - left and right context cards
  - metric deltas
  - comparison explanation
  - report if requested
  - frame drill-down buttons

### What to validate

- can the user easily tell which side is which?
- are the changes readable without digging into raw numbers?

---

## 15. Sequence-level comparison queries

### Example inputs

- `Compare the buildup to the first and second corners`
- `Compare the transition after the first and second away recoveries`
- `Write a report comparing the transition after the first and second away recoveries`

### What the system resolves

- two sequence windows
- segmented sequence comparison
- sequence delta summary

### Expected result

- `Primary result type`: Comparison View + Report / Explanation View
- `What the user sees`:
  - left/right sequence context
  - sequence delta cards
  - comparison insight summary
  - explanation
  - report if requested

### What to validate

- does the system make sequence differences understandable?
- does the user feel they are comparing real football flow, not just raw metrics?

---

## 16. Report-style queries

### Example inputs

- `Write a short report on the away team's second corner`
- `Write a report on away shots in period 2`
- `Write a report on the buildup to the goal`

### What the system resolves

- underlying football answer first
- report text layered on top

### Expected result

- `Primary result type`: Report / Explanation View with supporting visual or data surface
- `What the user sees`:
  - readable report panel
  - copy-report action
  - supporting replay, comparison, or aggregate data beside it

### What to validate

- is the report readable enough to share or discuss?
- does the report feel tied to the actual football data shown on screen?

---

## What the system is weaker at right now

These are query families where the current system is not yet strong.

### 1. Player-role-specific football questions

Examples:

- `Show me the winger's movement`
- `Where was the center back when the goal happened?`

Why weak:

- current routing is stronger at team/event/sequence level than individual-role reasoning

Expected behavior:

- may resolve only to a general frame/event result

### 2. Very fuzzy tactical prompts

Examples:

- `Show me when the press was effective`
- `Where did they look dangerous?`

Why weak:

- current system does not yet have deep tactical classifiers or danger models

Expected behavior:

- may return a weaker or overly generic result

### 3. Long multi-hop football logic

Examples:

- `Show me the attack that started from a recovery in the defensive third and ended in a shot after switching play`

Why weak:

- current reasoning is strong for short structured chains, not arbitrarily deep tactical chains

Expected behavior:

- partial resolution or weak interpretation

### 4. Continuous biomechanics-style questions

Examples:

- `Who accelerated the fastest?`
- `Who looked fatigued?`

Why weak:

- current metrics are structural and sequence-based, not physical-load or biomechanical models

Expected behavior:

- unsupported or weakly mapped to another result family

## Best way to use the system right now

If you want the system to shine, use queries that are:

- concrete
- football-event anchored
- time anchored
- frame anchored
- sequence anchored
- comparison oriented
- report oriented on top of those

The strongest current use cases are:

- event retrieval
- buildup analysis
- transition analysis
- aggregate event inventory
- team structure metrics
- within-match comparison
- report generation on top of those

## Recommended usability testing approach

When testing the system end to end, do not test only correctness of data retrieval.

Test these 4 things for each query:

### 1. Resolution

- did it understand the question type correctly?

### 2. Result fit

- did it choose the right output mode?
- snapshot vs replay vs aggregate vs comparison vs report

### 3. Readability

- can a user quickly understand the result?

### 4. Drill-down usefulness

- can a user move naturally from summary -> moment -> replay -> explanation?

## Suggested test batches

### Batch 1: Snapshot and event basics

- `Show me frame 1500`
- `Show me minute 5`
- `Show me the away team's second corner`

### Batch 2: Aggregate and filters

- `How many away shots were there in period 2?`
- `List all home set pieces in period 2`
- `Show all away shots in the attacking third`

### Batch 3: Sequence intelligence

- `Show me the buildup to the goal`
- `Show me the transition after the first away recovery`
- `Show me the first shot after the away team's second corner`

### Batch 4: Comparison

- `Compare minute 5 and minute 10`
- `Compare the first and second corners`
- `Compare the transition after the first and second away recoveries`

### Batch 5: Reporting

- `Write a report on the away team's second corner`
- `Write a report on away shots in period 2`
- `Write a report comparing the transition after the first and second away recoveries`

## Short final summary

At the current stage, the full system can already turn natural-language football questions into:

- snapshots
- replayable football moments
- buildup and transition sequence views
- metric summaries
- aggregate event inventories
- within-match comparisons
- readable explanations
- report-style outputs

So the system is now testable as a real end-to-end football analysis product, not just as a backend query engine.

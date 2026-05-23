# Maximum Intelligence Extractable From Current Data

## The framing

This guide takes an optimistic view of the current project.

Instead of asking:

- what data are we missing?

it asks:

- how far can we push the data we already have?

Right now, the available data is:

- one anonymized match from `Sample_Game_2`
- Home tracking data
- Away tracking data
- synchronized event data

That may sound narrow, but it still contains a very large football intelligence space.

This guide defines that space.

## The core idea

Even with one match, we still have:

- positions of all tracked entities over time
- the ball position over time
- the event timeline
- frame-level synchronization between tracking and events
- time order
- team-level movement patterns
- sequence context before and after events

That means we can support much more than:

- one static frame
- one event lookup

We can push into:

- sequence understanding
- spatial reasoning
- shape analysis
- event chains
- transition analysis
- tactical summaries
- report generation

## What kinds of questions can this data support?

The easiest way to think about this is not as infinite individual questions, but as question families.

If the system can support the family, then it can support many natural-language variations of that family.

## Level 1: Direct factual retrieval

These are the simplest questions.

Examples:

- `Show me frame 1500`
- `Show me minute 5`
- `Show me the away team's second corner`
- `Show me the last goal before 70:00`

What the system needs:

- frame lookup
- time-to-frame conversion
- event lookup
- order handling
- relative time handling

Outputs:

- frame coordinates
- event metadata
- replay window
- short caption

Visuals:

- pitch snapshot
- replay clip
- event marker on timeline

Reports:

- short event note
- simple match moment summary

## Level 2: Aggregate factual retrieval

These questions ask for counts, lists, or event sets.

Examples:

- `How many away shots were there in period 2?`
- `List all home set pieces`
- `Show all recoveries in the middle third`

What the system needs:

- counting
- listing
- filtering by team, type, subtype, period, zone

Outputs:

- count
- event list
- filtered event set

Visuals:

- count cards
- event tables
- timeline markers
- mini sequence cards

Reports:

- period summaries
- event inventory reports
- team event profile summaries

## Level 3: Spatial football queries

These questions focus on where things happen.

Examples:

- `Show me all passes into the box`
- `Show me the first shot from the left wing`
- `How many recoveries happened in the attacking third?`

What the system needs:

- pitch zone logic
- zone filtering
- event-location matching

Outputs:

- event set by zone
- frame/event context
- zone-aware counts

Visuals:

- shaded pitch zones
- zone-tagged event markers
- heat-style event maps

Reports:

- zone usage summaries
- final-third activity notes
- box-entry or wing-usage summaries

## Level 4: Temporal and sequence questions

These questions ask what happened around a moment, or what happened before/after something.

Examples:

- `Show me the first shot after the away team's second corner`
- `Show me the pass before the first goal`
- `What happened around the last goal before 70:00?`

What the system needs:

- anchor event resolution
- target event resolution
- replay window extraction
- ordered chain logic

Outputs:

- anchor event
- target event
- event chain explanation
- replay sequence

Visuals:

- replay strip
- event-to-event markers
- event chain timeline
- step-by-step sequence navigation

Reports:

- sequence summaries
- pre-goal or post-turnover notes
- event chain explanation

## Level 5: Team shape and structural questions

These questions focus on how the teams are arranged.

Examples:

- `What was the home team's width at minute 5?`
- `Show me the away team's compactness at the second corner`
- `How spread out was the team before the shot?`

What the system needs:

- frame-level coordinate extraction
- width/depth logic
- convex hull logic
- centroid logic
- compactness proxy logic

Outputs:

- shape metrics
- frame-level structure snapshot
- metric explanation

Visuals:

- team hulls
- width/depth guides
- centroid markers
- compactness overlays

Reports:

- team shape summary
- structural comparison note
- compactness snapshot

## Level 6: Movement and transition questions

These questions focus on change over time.

Examples:

- `Show me the first pass in attacking transition`
- `How did the team move after winning the ball?`
- `Show me the transition from attack to defense after minute 75`

What the system needs:

- phase tagging
- replay windows
- movement comparison across frames
- event chain logic

Outputs:

- phase labels
- transition sequence
- start-to-end positional change

Visuals:

- replay playback
- movement trails
- directional arrows
- team shape change across a clip

Reports:

- transition summaries
- turnover-to-attack notes
- defensive recovery summaries

## Level 7: Event-context tactical questions

These questions are not just about one event, but about the football context around the event.

Examples:

- `What was the team shape when the first goal happened?`
- `Show me the passing context before the shot`
- `What other events happened in the same sequence window?`

What the system needs:

- sequence window retrieval
- nearby event retrieval
- structural metrics
- contextual summary building

Outputs:

- event plus context
- replay plus nearby events
- structural metrics tied to the event

Visuals:

- replay window with event markers
- contextual side panel
- event annotation cards

Reports:

- event context note
- scoring chance breakdown
- set-piece sequence summary

## Level 8: Within-match comparison questions

Even with one match, comparison is still possible.

Examples:

- `Compare the first and second corners`
- `Compare first-half and second-half away shots`
- `Compare the shape at kickoff and at the last goal`

What the system needs:

- two or more resolved moments
- comparable metrics
- side-by-side event and frame context

Outputs:

- comparison table
- delta metrics
- paired sequence summary

Visuals:

- side-by-side pitch views
- dual replay cards
- comparison charts

Reports:

- before/after summaries
- first-half vs second-half notes
- set-piece comparison writeups

## Level 9: Explanation and analyst-style questions

This is where the system starts feeling like a football analyst rather than just a lookup engine.

Examples:

- `Why was this chance dangerous?`
- `What changed before the goal?`
- `Why did this transition matter?`

What the system needs:

- event context
- sequence context
- structural metrics
- movement reasoning
- explanation templates or explanation logic

Outputs:

- written explanation
- key factors
- evidence-backed reasoning

Visuals:

- annotated replay
- highlighted event chain
- metric callouts

Reports:

- coach-style explanation note
- tactical breakdown paragraph
- teaching summary

## Level 10: Match-story and narrative generation

Even with one match, the system can create narratives.

Examples:

- `Summarize the away team's attacking patterns in this match`
- `Write a short coach report on all dangerous shots`
- `Create a tactical summary of set pieces`

What the system needs:

- grouped event retrieval
- sequence summaries
- repeated metric extraction
- text report generation

Outputs:

- narrative summary
- grouped insight report
- themed match note

Visuals:

- event galleries
- summary cards
- phase or zone dashboards

Reports:

- markdown tactical report
- coach-style match summary
- event-family report

## So how deep can we go?

With this data alone, we can go very deep in these dimensions:

- event intelligence
- sequence intelligence
- shape intelligence
- zone intelligence
- replay intelligence
- within-match comparison
- explanation and reporting

The deepest reliable boundary is:

- any insight that can be grounded in tracking positions, synchronized events, timing, order, and derived movement/shape logic

That is already a large space.

## What insights are realistically extractable right now?

Here are the main insight families we can aim for.

### Positional insights

- where players and ball were
- who was high or deep
- how crowded or spread out an area was

### Event insights

- what happened
- when it happened
- how often it happened
- in what zone or period it happened

### Sequence insights

- what happened before or after an event
- whether a move developed quickly or slowly
- what nearby events surrounded the moment

### Structural insights

- team width
- team depth
- hull area
- compactness proxies
- centroid shifts

### Transition insights

- how team shape changed after recoveries or losses
- how quickly the game moved from one state to another

### Match-pattern insights

- which zones were used more
- what kinds of events clustered together
- whether one half looked different from the other

### Explanation insights

- why an event matters
- why a sequence is notable
- what structural or temporal context makes it interesting

## What visuals can this data support?

The current data can support much more than one pitch drawing.

### Core visuals

- static pitch snapshots
- replay windows
- event markers
- frame scrubbers

### Structural visuals

- convex hulls
- centroid markers
- width/depth guides
- shape overlays

### Sequence visuals

- event chains
- movement arrows
- trail lines
- before/after state cards

### Aggregate visuals

- count cards
- tables
- timelines
- event lists
- zone maps

### Comparison visuals

- side-by-side frames
- paired replay panels
- metric comparison cards

### Explanation visuals

- annotated pitch
- highlighted key event
- tactical callouts

## What report types can this data support?

Even with one match, the reporting space is broad.

### Simple reports

- event summary report
- period summary
- team event counts

### Tactical reports

- chance creation report
- set-piece report
- transition report
- zone usage report

### Structural reports

- team shape report
- compactness snapshots
- width/depth comparisons

### Sequence reports

- pre-goal sequence report
- recovery-to-shot report
- dangerous moment breakdown

### Teaching reports

- explain this event in simple words
- explain this replay sequence to beginners
- explain how the team shape changed

## What should the system handle, based on this data?

If we take the current data seriously, then the system should eventually handle:

1. direct frame/time/event retrieval
2. ordered and relative event queries
3. aggregate count/list queries
4. spatial zone queries
5. phase-of-play queries
6. frame and event metric queries
7. event-to-event sequence queries
8. context-rich event explanations
9. within-match comparisons
10. tactical summaries and report generation

## A practical implementation order

If we want to push the limits properly, this is a good build order:

1. finish broad structured retrieval
2. deepen sequence reasoning
3. expand metric coverage
4. add stronger explanation output
5. add richer report generation
6. add within-match comparison workflows
7. connect each family to the right output type

## The optimistic conclusion

With only the data already in hand, we can still build a very deep football intelligence system.

The limit is not that the match is anonymized or that it is only one game.

The real limit is how well we:

- extract structured football meaning
- compute derived features
- chain events into sequences
- explain what those patterns mean
- choose the right visual or report output for each query

## One-line summary

This current dataset is already rich enough to support a wide ladder of football intelligence, from direct event lookup all the way to sequence reasoning, structural analysis, tactical explanation, visual storytelling, and report generation within the scope of a single match.

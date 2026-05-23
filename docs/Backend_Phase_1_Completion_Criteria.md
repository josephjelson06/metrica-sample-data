# Backend Phase 1 Completion Criteria

## Why this document exists

The backend can keep growing almost forever.

That is good in one sense, because football questions are very broad.
But it is not good if we keep adding backend features without ever giving the frontend and reporting layers a stable base to catch up to.

So this document defines a practical checkpoint:

- not the absolute limit of what the data can do
- not the end of the whole project
- just the point where the backend is strong enough to pause, stabilize, and hand off to the next phase

## The goal of Backend Phase 1

Backend Phase 1 is complete when the system can reliably turn a natural-language football question into:

- structured data retrieval
- sequence-aware football context
- useful tactical measurements
- grounded explanation output
- stable response payloads that the frontend and reporting layers can depend on

In simple words:

> the backend should already feel like a real football query engine, not just a smart file reader.

## The 6 capability blocks that define completion

### 1. Structured retrieval

The system should reliably support:

- frame queries
- minute and clock queries
- event queries
- ordered event queries like first, second, last
- relative event queries like before, after, around
- aggregate queries like count and list
- period filters
- pitch-zone filters
- phase-of-play filters

This block is already largely done.

### 2. Sequence retrieval

The system should reliably support:

- short replay windows around events
- buildup windows before key events
- transition windows after trigger events
- event-to-event chained lookups
- nearby event inventory inside a resolved sequence

This block is also already largely done.

### 3. Tactical metrics

The system should expose a useful set of measurable team-structure features, such as:

- width
- depth
- centroid
- hull and compactness proxies
- line-height proxy
- team-length proxy
- unit spacing
- nearest teammate distance
- frame-to-frame structure deltas

This block has clearly started and is already useful.

### 4. Comparison

The system should reliably compare:

- one moment vs another moment
- one event vs another event
- one time point vs another time point
- simple sequence contexts around those moments

This is already underway and working for the main comparison paths.

### 5. Grounded explanation

The system should be able to explain:

- what was found
- why that moment was selected
- what changed across the sequence or comparison
- how a buildup or transition developed at a basic level

Important note:

This does not mean full analyst-level storytelling yet.
It means the text output is grounded in real events, real frames, and real metrics instead of vague language.

This block has started, but it still has room to become stronger.

### 6. Stable output contract

The backend should return outputs that are stable enough for other layers to build on.

That means:

- consistent query routing
- consistent `context` payload shape
- sequence payloads that are predictable
- metric payloads that are predictable
- explanation/report fields that frontend or reporting tools can rely on

This is important because once frontend and reporting catch up, changing payload shapes too often becomes expensive.

## What still remains before we call Backend Phase 1 complete

These are the main remaining items:

### 1. Richer sequence segmentation

We should improve how buildup and transition windows are described internally.

Examples:

- identify clearer sub-phases inside a buildup
- identify cleaner follow-up chains inside transitions
- better separate trigger, continuation, and outcome

This is one of the main remaining backend priorities.

### 2. Stronger sequence-level comparison

Right now comparison is strong at the moment level.
The next step is to compare short sequences more meaningfully.

Examples:

- compare two corners as sequences, not only as resolved frames
- compare two buildups
- compare two transitions

### 3. Better tactical explanation quality

Right now the system can explain:

- what happened
- what changed

It should get stronger at:

- why the moment matters
- what the sequence suggests tactically
- what structural shift happened before the key event

This should still stay grounded in measurable data.

### 4. A final sanity pass on payload stability

Before moving focus to frontend/reporting, we should make sure the main result formats feel settled enough to build on.

## The handoff point

We should stop pushing backend-first development when these conditions are true:

1. The remaining backend gaps are no longer blocking useful product work.
2. Frontend now has enough stable query types and payload shapes to catch up properly.
3. Reporting can be improved mostly by presentation and formatting, not by missing core retrieval logic.

That is the practical handoff point from:

- backend expansion

to:

- frontend catch-up
- reporting polish
- real usage testing

## What happens after Backend Phase 1

Once Phase 1 is complete, the next order should be:

### Phase 2A: Frontend catch-up

The frontend should catch up to the backend query families:

- replay and sequence views
- comparison views
- aggregate/list views
- metric views
- explanation panels

### Phase 2B: Reporting catch-up

The reporting layer should become more intentional:

- query summaries
- tactical sequence summaries
- comparison reports
- event-family reports

### Phase 2C: Real usage and gap discovery

Only after the system is used more actively should we decide what Backend Phase 2 needs.

That is where we learn:

- what is truly missing
- what is only "nice to have"
- what new backend intelligence actually creates value

## Current recommendation

Right now, the project is close to the right stopping zone for backend Phase 1, but not fully there yet.

The most sensible final backend pushes are:

1. richer sequence segmentation
2. stronger sequence-level comparison
3. better tactical explanation grounded in those sequence features

After that, the best move is not endless backend growth.
The best move is to let frontend and reporting catch up.

## One-line summary

Backend Phase 1 is complete when the system can answer the major football question families supported by the current data, return stable sequence-aware outputs, compare moments and sequences usefully, and explain results in grounded football language well enough for frontend and reporting to build on top of it.

# Football Intelligence System Design Map

This document explains the deeper design logic behind the project.

It answers questions like:

- Why did we choose these capability levels?
- How do we handle the fact that football questions are almost infinite?
- What is the role of the LLM?
- What is the role of data, tools, geometry, physics, and analytics?
- Are we building only an AI agent, or a bigger football intelligence system?

You can use this file as:

- a strategy document
- a speaking guide
- a project direction map
- a reference for future development

## 1. The Core Idea

Football questions are almost infinite.

A user can ask:

- `Show me the away team's second corner`
- `Show me the last goal before 70:00`
- `Show me how the defense blocked the winger after the 75th minute`
- `Show me when the team looked most compact before conceding`
- `Why was this attack dangerous?`

So the system cannot be designed by making a separate hardcoded rule for every possible football question.

Instead, the system must be designed around a smaller set of reusable capabilities.

That is the main idea:

> Infinite football questions usually collapse into a finite set of underlying capabilities.

Those capabilities are what we build level by level.

## 2. Why The Levels Make Sense

The levels are not a list of all football questions.

They are a list of the kinds of intelligence the system must gain over time.

For example, this question:

> `Show me how the player transitioned from attack to defense to stop the winger entering the box after minute 75`

sounds like one big football question.

But underneath, it breaks into smaller capabilities:

1. `after minute 75`
   Time filtering
2. `transition from attack to defense`
   Phase-of-play detection
3. `winger entering the box`
   Spatial reasoning
4. `stop or prevent`
   Defensive-action interpretation
5. `show me how`
   Sequence retrieval plus visualization plus explanation

So the levels are really a map of the system's internal abilities.

## 3. The Capability Progression

## Level 1: Discrete Retrieval

The system learns to retrieve exact match moments.

Examples:

- frame-based queries
- minute/time-based queries
- event-based queries

Examples of questions:

- `Show me frame 1500`
- `Show me minute 5`
- `Show me the first shot`

What the system needs:

- frame lookup
- time-to-frame conversion
- event-to-frame lookup

## Level 2: Ordered And Relative Retrieval

The system learns event order and relative timing.

Examples:

- first
- second
- last
- before
- after
- around

Examples of questions:

- `Show me the away team's second corner`
- `Show me the last goal before 70:00`
- `Show me the first pass after 2:30`

What the system needs:

- ordering logic
- relative time/frame filters
- event ranking

## Level 3: Sequence Retrieval

The system stops returning only one frame and starts returning short windows around an event.

Examples:

- 5 seconds before a shot
- 2 seconds after a corner
- replay clip around a goal

What the system needs:

- frame range extraction
- event window retrieval
- nearby event retrieval

## Level 4: Multi-Result Retrieval

The system learns to handle sets of moments, not just one.

Examples:

- `Show me all Away shots`
- `Show me the first three corners`
- `List all goals in period 2`

What the system needs:

- list queries
- pagination or ranking
- multi-result response structure

## Level 5: Spatial Reasoning

The system learns football locations and zones.

Examples:

- final third
- penalty box
- left wing
- right half-space
- central channel

Examples of questions:

- `Show me passes into the box`
- `Show me recoveries in the middle third`
- `Show me attacks down the left wing`

What the system needs:

- pitch zone definitions
- point-in-zone logic
- event and tracking filtering by location

## Level 6: Derived Tactical Metrics

The system starts computing football structure, not just retrieving raw data.

Examples:

- team width
- team depth
- compactness
- line height
- hull area
- player speed
- acceleration

Examples of questions:

- `Show me the most compact defensive shape`
- `What was the team's width here?`
- `How fast did the winger accelerate in this sequence?`

What the system needs:

- geometry modules
- temporal math
- physics or kinematic functions
- derived metrics from tracking data

## Level 7: Multi-Step Football Reasoning

The system learns to combine several football conditions.

Examples:

- `Show me the first goal that came after a recovery`
- `Show me the sequence that started from a throw-in and ended in a shot`
- `Find the attack that followed a defensive transition`

What the system needs:

- chained tool calls
- event-to-sequence reasoning
- state tracking across multiple events

## Level 8: Explanation Queries

The system stops being only a retrieval engine and starts behaving more like an analyst.

Examples:

- `Why was this attack dangerous?`
- `What broke the defensive structure here?`
- `Explain the buildup to the goal`

What the system needs:

- structured retrieval
- derived features
- sequence understanding
- explanation templates or reasoning flows

## Beyond Level 8

After explanation, the project can grow into:

- automated tactical reports
- cross-match comparison
- recommendation systems
- opponent scouting
- predictive risk models
- fatigue or performance modelling
- simulation-style analysis

This is not required for the first major version, but it is the natural long-term direction.

## 4. Natural Language Outside, Structured Reasoning Inside

The user should keep asking questions in natural language at every level.

Examples:

- `Show me the first goal buildup`
- `Where was the defense most compact?`
- `Why did this counter attack work?`

So yes, the project should stay natural-language-first.

But that does not mean the inside of the system is unstructured.

The inside becomes more structured over time:

- time filters
- event filters
- pitch zones
- phase labels
- derived metrics
- geometry functions
- physics functions
- reasoning steps

The correct mental model is:

> Natural language outside, structured reasoning inside.

## 5. What Happens When A Query Arrives

Every user question is processed in real time.

But the LLM should not do all the work itself.

The healthy architecture is:

- LLM for understanding the question
- tools for doing the actual computation

So when a query arrives, the flow should look like this:

1. User asks in natural language.
2. LLM interprets the intent.
3. LLM selects the correct tools.
4. Tools do the real work.
5. Results return to the response layer.
6. The system explains or visualizes the result.

## 6. What The LLM Should Actually Do

The LLM should mainly act as:

- router
- planner
- decomposer
- translator
- explanation layer

It should not be responsible for raw numeric computation when tools can do that more reliably.

Examples of things tools should handle:

- SQL filtering
- range selection
- geometric hulls
- pitch zone checks
- speed and acceleration
- sequence extraction
- fatigue or biometric modelling

So the right idea is:

> The LLM decides what to ask for. The tools decide what is true.

## 7. Real-Time Computation At Higher Levels

At Level 1 and Level 2, retrieval is mostly straightforward:

- SQL filters
- frame lookup
- event lookup

At higher levels, real-time processing becomes heavier.

Examples:

- continuity or long sequence logic
- geometry
- velocity and acceleration
- player load or fatigue indicators
- tactical state detection

That does not mean the LLM becomes "smarter" by doing more math itself.

It means the system gains stronger tools.

The progression should be:

- early stage: SQL and retrieval tools
- middle stage: SQL plus geometry plus temporal logic
- later stage: SQL plus geometry plus physics plus learned models plus explanation

## 8. The Football Analytics Matrix

This is a very strong mental model for football analytics.

### Subject Matrix

| Level of Analysis | Technical / Tactical | Spatial / Structural | Physical / Fitness |
| --- | --- | --- | --- |
| Individual | passing, shooting, dribbling | heatmaps, average position | speed, distance, acceleration |
| Group | combinations, link play, unit interactions | line spacing, unit compactness | load of the midfield, back line, front three |
| Team | possession style, passing network, attack pattern | width, depth, block structure, line height | total distance, sprint drop-off, physical output |

This matrix is correct and useful.

But it is not fully complete on its own.

It also needs context layers.

## 9. The Missing Context Layers

The same football action means different things depending on context.

Important context layers are:

- phase of play
- game state
- time period
- opponent
- set piece vs open play

So a stronger full model is:

### Subject Matrix

- individual
- group
- team

crossed with:

- technical/tactical
- spatial/structural
- physical/fitness

and then viewed through:

- phase of play
- game state
- time context
- opponent context
- set piece context

That gives a much more realistic football intelligence framework.

## 10. The Four Phases Of Football

This is also a correct and powerful model:

1. In possession
2. Defensive transition
3. Out of possession
4. Attacking transition

This is one of the best ways to organize football reasoning.

But in practice, there is one important addition:

> Set pieces often need to be treated as a special parallel context.

That means the system usually benefits from separating:

- open play phases
- set piece phases

because corners, free kicks, kick-offs, penalties, and throw-ins behave differently from open play.

## 11. Are We Building Only An AI Agent

No.

We are building a bigger system than that.

The AI agent is only one layer in the stack.

A more accurate description is:

> This is a data-driven football intelligence platform with an AI agent as the orchestration layer.

The broader system includes:

- data ingestion
- parquet storage
- DuckDB retrieval
- feature computation
- LLM routing
- visualization
- explanation

So calling it "just an AI agent" is too small.

Calling it a `football intelligence system` is more accurate.

## 12. The Best Final Mental Model

The best simple summary is:

> We are not trying to teach the AI every football question one by one.
> We are building a layered football intelligence engine that can combine reusable capabilities to answer more and more complex questions over time.

That is why the roadmap is powerful.

The questions are infinite.

But the underlying system capabilities are finite and buildable.

## 13. Practical Summary

If someone asks, "What are we really building?", the simplest strong answer is:

> We are building a natural-language football intelligence system. The user asks in plain English, the AI routes the request to the correct data and analytics tools, and the system returns the correct football moment, sequence, metric, or explanation.

If someone asks, "Why does the roadmap make sense?", answer:

> Because infinite football questions can be answered by combining a finite set of retrieval, spatial, temporal, metric, and explanation capabilities.

If someone asks, "Is this just an AI agent?", answer:

> No. It is a football analysis platform with an AI agent on top of a structured data and analytics engine.

# What A Football AI System Must Handle

## The simple idea

When someone asks a natural football question, the system should do much more than just draw something on a pitch.

It should be able to:

- understand the question
- find the right data
- compute anything needed
- decide the best output form
- visualize it if needed
- explain it in text
- produce reports when useful
- support follow-up interaction

So the full system is much bigger than just:

- visualization
- reporting

Those are important, but they are only two parts of the whole system.

## The full responsibility chain

### 1. Query understanding

The system must understand what the user means.

That includes:

- frame
- time
- event type
- subtype
- team
- player reference
- order like first or second
- relation like before or after
- pitch zone
- phase of play
- metric intent
- comparison intent
- explanation intent

Example:

`Show me the first shot after the away team's second corner`

The system must recognize:

- target event: shot
- anchor event: away second corner
- relation: after

### 2. Query planning

The system must decide how many steps are needed to answer the question.

Some questions need:

- one direct lookup

Some need:

- one event lookup
- then one frame lookup

Some need:

- one anchor event
- one target event relative to it
- one replay sequence
- then metrics or explanation

So the system must plan the answer path, not just parse words.

### 3. Data retrieval

The system must pull the right football data from storage.

That may include:

- tracking frames
- event rows
- frame windows
- event windows
- aggregate event sets

In this project, that role is handled by:

- Parquet storage
- DuckDB queries

### 4. Computation

The system must compute anything that is not already written directly in the data.

Examples:

- width
- depth
- compactness
- hull area
- movement distances
- speed
- acceleration
- spatial zone membership
- phase labels

The LLM should not do these calculations by itself.

The right model is:

- LLM for routing and planning
- tools for actual football computation

### 5. Reasoning

The system must connect football facts across time and context.

Examples:

- first goal after a recovery
- last shot before halftime
- all away passes in the attacking third
- how the move developed before the shot

This is where the system moves beyond simple lookup into football reasoning.

### 6. Output shaping

The system must decide what kind of answer format fits the query best.

Different queries may need different outputs:

- pitch snapshot
- replay sequence
- event list
- count summary
- metric card
- table
- chart
- side panel summary
- written explanation
- markdown report

Not every football question should be answered with the same kind of screen.

## Visualization is only one output mode

Visualization is important, but it is only one part of the response system.

Visualization can include:

- pitch dots
- replay controls
- event markers
- arrows
- hulls
- timelines
- charts
- tables

But some questions are better answered through:

- a number
- a short sentence
- a list
- a structured summary
- a report

So the system should not assume that every query needs a pitch drawing.

## Text explanation is another major output mode

The system should also explain what it found.

That explanation can vary by difficulty.

### For simple queries

- what frame was found
- what event was matched

### For metric queries

- what the number means
- which team it belongs to
- what frame it came from

### For sequence queries

- what the anchor event was
- what target event was found
- how the chain was resolved

### For advanced tactical queries

- why the moment mattered
- what movement or structure created danger
- what changed before and after the event

So explanation is not optional. It is one of the core layers of the system.

## Reporting is another output mode

Sometimes the answer should become a reusable artifact, not just a live reply.

Examples:

- markdown report
- coach note
- sequence summary
- project progress report
- dataset explanation guide

That means the system should be able to convert live findings into reusable documents.

## Interaction is also part of the system

A good football AI system should support follow-up thinking.

Example flow:

- `Show me the away team's second corner`
- `Now show me the first shot after that`
- `Why was that dangerous?`
- `Summarize this sequence for a coach`

So the system should not only answer one question.

It should support multi-step analysis conversations.

## So what all must the system handle?

A strong football AI system must handle at least these layers:

1. `Understand`
2. `Plan`
3. `Retrieve`
4. `Compute`
5. `Reason`
6. `Choose output form`
7. `Visualize when useful`
8. `Explain in text`
9. `Produce reports when useful`
10. `Support follow-up interaction`

## What this means for our project

For this project specifically:

- we are currently strongest in retrieval and structured query handling
- we have started metric and sequence reasoning
- we have working visualization for major interactive cases
- we have documentation and reporting workflows
- we are still growing the deeper explanation and tactical reasoning layers

So the project is not only building a pitch visualizer.

It is building a `football intelligence system` where visualization, explanation, reporting, and interaction all sit on top of a data-driven reasoning engine.

## One-line summary

A football AI system must not only answer the question, but also understand it, retrieve the right football evidence, compute what is needed, choose the right form of output, explain the result clearly, and support continued analysis.

# System End To End Testing Checklist

## Why this document exists

This document is for **live usability testing** of the full system.

It is not mainly for:

- unit testing
- bug fixing
- code debugging

It is for checking:

- what query was given
- what result we expected
- what result the system actually produced
- whether the output felt usable and understandable

Use this document while running the system end to end.

## How to use this checklist

For each query:

1. run the query in the app
2. compare the result with the expected behavior
3. fill in the `Actual Result`
4. fill in the `Notes / Observations`
5. mark `Pass`, `Partial`, or `Fail`

## Recommended rating meanings

- `Pass`
  - the system understood the query and returned the right kind of result
- `Partial`
  - the system returned something useful, but not quite the ideal answer
- `Fail`
  - the system misunderstood the query, returned the wrong output mode, or did not answer meaningfully

---

## Test record template

Use this template when you want to add new test cases later.

```md
### Test ID

- Query:
- Query family:
- Expected result type:
- Expected behavior:
- Actual result:
- Result rating: Pass / Partial / Fail
- Notes / Observations:
```

---

## Batch 1: Snapshot And Event Basics

### T1

- Query: `Show me frame 1500`
- Query family: Direct frame
- Expected result type: Snapshot View
- Expected behavior:
  - pitch snapshot loads
  - frame is resolved directly
  - player and ball positions are shown
- Actual result:
- Result rating:
- Notes / Observations:

### T2

- Query: `Show me minute 5`
- Query family: Time / clock
- Expected result type: Snapshot View
- Expected behavior:
  - time is converted to a frame
  - snapshot loads correctly
  - explanation makes it clear this is a time-based lookup
- Actual result:
- Result rating:
- Notes / Observations:

### T3

- Query: `Show me the away team's second corner`
- Query family: Single event
- Expected result type: Replay / Sequence View
- Expected behavior:
  - correct event is resolved
  - replay clip loads
  - event frame is marked on the clip
  - explanation clearly names the corner
- Actual result:
- Result rating:
- Notes / Observations:

### T4

- Query: `Show me the first yellow card`
- Query family: Single event
- Expected result type: Replay / Sequence View
- Expected behavior:
  - card event is resolved
  - event metadata is clear
  - replay is centered around the card event
- Actual result:
- Result rating:
- Notes / Observations:

---

## Batch 2: Ordered And Relative Event Queries

### T5

- Query: `Show me the first shot`
- Query family: Ordered event
- Expected result type: Replay / Sequence View
- Expected behavior:
  - first shot in the event stream is selected
  - replay and explanation reflect the shot event clearly
- Actual result:
- Result rating:
- Notes / Observations:

### T6

- Query: `Show me the last goal before 70:00`
- Query family: Relative event
- Expected result type: Replay / Sequence View
- Expected behavior:
  - the system resolves a goal relative to the time anchor
  - explanation should show the relation clearly
- Actual result:
- Result rating:
- Notes / Observations:

### T7

- Query: `Show me the first pass after 2:30`
- Query family: Relative event
- Expected result type: Replay / Sequence View
- Expected behavior:
  - the pass is resolved relative to the time anchor
  - output should feel clearly different from a simple pass lookup
- Actual result:
- Result rating:
- Notes / Observations:

---

## Batch 3: Aggregate Queries

### T8

- Query: `How many away shots were there in period 2?`
- Query family: Aggregate count
- Expected result type: Aggregate View
- Expected behavior:
  - count summary shown
  - filters summary shown
  - explanation reflects count-style output
- Actual result:
- Result rating:
- Notes / Observations:

### T9

- Query: `List all home set pieces in period 2`
- Query family: Aggregate list
- Expected result type: Aggregate View
- Expected behavior:
  - event table shown
  - rows are readable
  - drill-down action available
- Actual result:
- Result rating:
- Notes / Observations:

### T10

- Query: `Show all away shots in the attacking third`
- Query family: Aggregate list with spatial filter
- Expected result type: Aggregate View
- Expected behavior:
  - filtered list shown
  - attacking-third filter is visible
  - event list feels football-meaningful
- Actual result:
- Result rating:
- Notes / Observations:

---

## Batch 4: Metric Queries

### T11

- Query: `What was the home team's width at minute 5?`
- Query family: Metric
- Expected result type: Metric View with pitch support
- Expected behavior:
  - resolved moment is shown
  - metric card is visible
  - explanation links the number to the football moment
- Actual result:
- Result rating:
- Notes / Observations:

### T12

- Query: `What was the away team's line height at the second corner?`
- Query family: Metric + event
- Expected result type: Metric View with pitch support
- Expected behavior:
  - event is resolved first
  - metric cards shown for that event frame
  - event and metric context both feel clear
- Actual result:
- Result rating:
- Notes / Observations:

---

## Batch 5: Chained And Sequence Event Queries

### T13

- Query: `Show me the first shot after the away team's second corner`
- Query family: Chained event
- Expected result type: Replay / Sequence View
- Expected behavior:
  - anchor event is shown
  - target event is shown
  - explanation makes the chain easy to understand
- Actual result:
- Result rating:
- Notes / Observations:

### T14

- Query: `Show me the buildup to the goal`
- Query family: Buildup
- Expected result type: Replay / Sequence View
- Expected behavior:
  - longer pre-event clip shown
  - buildup segmentation visible
  - event-mix breakdown visible
  - explanation helps narrate the sequence
- Actual result:
- Result rating:
- Notes / Observations:

### T15

- Query: `Show me the transition after the first away recovery`
- Query family: Transition
- Expected result type: Replay / Sequence View
- Expected behavior:
  - post-trigger clip shown
  - transition summary visible
  - event chain after the recovery is understandable
- Actual result:
- Result rating:
- Notes / Observations:

---

## Batch 6: Comparison Queries

### T16

- Query: `Compare minute 5 and minute 10`
- Query family: Moment comparison
- Expected result type: Comparison View
- Expected behavior:
  - left and right moments shown clearly
  - metric deltas shown
  - comparison explanation feels useful
- Actual result:
- Result rating:
- Notes / Observations:

### T17

- Query: `Compare the first and second corners`
- Query family: Event comparison
- Expected result type: Comparison View
- Expected behavior:
  - both moments clearly identified
  - event comparison feels intuitive
  - drill-down to each frame is possible
- Actual result:
- Result rating:
- Notes / Observations:

### T18

- Query: `Compare the transition after the first and second away recoveries`
- Query family: Sequence comparison
- Expected result type: Comparison View
- Expected behavior:
  - both transition sequences clearly identified
  - sequence deltas shown
  - comparison insight panel helps summarize major changes
- Actual result:
- Result rating:
- Notes / Observations:

---

## Batch 7: Report Queries

### T19

- Query: `Write a report on the away team's second corner`
- Query family: Report on single event
- Expected result type: Report / Explanation View with supporting replay
- Expected behavior:
  - report appears clearly
  - report is readable
  - copy-report action works
  - supporting event/replay context is visible
- Actual result:
- Result rating:
- Notes / Observations:

### T20

- Query: `Write a report on away shots in period 2`
- Query family: Report on aggregate result
- Expected result type: Report / Explanation View with aggregate support
- Expected behavior:
  - report appears
  - aggregate result is still visible
  - count/list context is understandable
- Actual result:
- Result rating:
- Notes / Observations:

### T21

- Query: `Write a report comparing the transition after the first and second away recoveries`
- Query family: Report on sequence comparison
- Expected result type: Report / Explanation View with Comparison View
- Expected behavior:
  - comparison and report both visible
  - user can understand both the comparison and the written summary
- Actual result:
- Result rating:
- Notes / Observations:

---

## Batch 8: Edge And Weak-Zone Queries

These are not expected to be perfect.
They are here to understand the current system boundary.

### T22

- Query: `Show me the winger's movement`
- Query family: Player / role-specific
- Expected result type: Weak-zone test
- Expected behavior:
  - likely partial or weak answer
  - may collapse into a broader frame/event result
- Actual result:
- Result rating:
- Notes / Observations:

### T23

- Query: `Show me when the press was effective`
- Query family: Fuzzy tactical
- Expected result type: Weak-zone test
- Expected behavior:
  - likely partial or weak answer
  - useful mainly for understanding current limitation
- Actual result:
- Result rating:
- Notes / Observations:

### T24

- Query: `Who accelerated the fastest?`
- Query family: Unsupported physical/kinematic
- Expected result type: Weak-zone test
- Expected behavior:
  - likely unsupported or poorly mapped
  - helps confirm current limit clearly
- Actual result:
- Result rating:
- Notes / Observations:

---

## Optional summary sheet

After testing, fill this in:

- Total tests run:
- Pass:
- Partial:
- Fail:

### Strongest current system areas

- 
- 
- 

### Most useful result types

- 
- 
- 

### Most confusing result types

- 
- 
- 

### Most important next improvements

- 
- 
- 

## One-line summary

This checklist is the practical end-to-end testing sheet for the current system:

- ask query
- observe result
- compare with expectation
- record usability notes

It is the right document to use while you test the football AI assistant as a real product.

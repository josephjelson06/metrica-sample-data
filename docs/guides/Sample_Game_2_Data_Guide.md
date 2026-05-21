# Sample Game 2 Data Guide

This file explains the `Sample_Game_2` dataset in simple words.

It covers these three files:

- `data/Sample_Game_2/Sample_Game_2_RawTrackingData_Home_Team.csv`
- `data/Sample_Game_2/Sample_Game_2_RawTrackingData_Away_Team.csv`
- `data/Sample_Game_2/Sample_Game_2_RawEventsData.csv`

The goal is to help someone new understand what the numbers mean and how the files are related.

## 1. What is in Sample Game 2?

Sample Game 2 has two main kinds of data:

- `Tracking data`: where players and the ball are located at each moment
- `Events data`: what happened in the match, like passes, shots, recoveries, and set pieces

These two kinds of data are synchronized, so they can be used together.

## 2. Tracking Data in Simple Words

The tracking files are:

- `Sample_Game_2_RawTrackingData_Home_Team.csv`
- `Sample_Game_2_RawTrackingData_Away_Team.csv`

These files tell you where each player is on the pitch over time.

### 2.1 What does one row mean?

One row means one moment in the match.

For each row, the file tells you:

- which half the game is in
- which frame number this is
- the time in seconds
- where each tracked player is standing
- where the ball is, if ball data is available

### 2.2 Main columns

The first three columns are:

- `Period`: the half of the match
  - `1` = first half
  - `2` = second half
- `Frame`: the frame number
- `Time [s]`: time in seconds

After these columns, each player has two numbers:

- first number = `x` position
- second number = `y` position

At the end, the ball also has two numbers:

- ball `x`
- ball `y`

### 2.3 What do x and y mean?

The coordinates are normalized. That means they usually go from `0` to `1`.

- `(0, 0)` = top-left of the pitch
- `(1, 1)` = bottom-right of the pitch
- `(0.5, 0.5)` = center spot

So:

- low `x` means left side of the pitch
- high `x` means right side of the pitch
- low `y` means upper side of the pitch
- high `y` means lower side of the pitch

The README says the pitch size is `105 x 68` meters. The tracking files do not store meters directly. They store positions on a `0 to 1` scale.

### 2.4 Example

If a row shows:

- `Player25 = 0.01218, 0.51763`

that means:

- the player is very close to the left side of the pitch
- the player is almost in the middle vertically

If a row shows:

- `Player11 = 0.94275, 0.50413`

that means:

- the player is very close to the right side of the pitch
- the player is also almost in the middle vertically

### 2.5 Why do the headers look strange?

The tracking CSV uses three header rows:

1. team label repeated many times: `Home` or `Away`
2. player shirt numbers
3. actual usable column names such as `Player11`, `Player25`, `Ball`

Some header cells look blank because each player needs two columns: one for `x` and one for `y`.

### 2.6 Why are there more than 11 players in a team file?

A team file can include all players who appeared in the match, not only the starting 11.

So if you see more than 11 player IDs, it usually means:

- some were starters
- some were substitutes

Not every player has values for the full match.

### 2.7 What does `NaN` mean?

`NaN` means the value is missing.

In this dataset, that usually means:

- the player was not on the pitch at that moment
- or the position was not available for that frame
- or the ball position was not available in that row

### 2.8 How often is tracking recorded?

The time column goes like:

- `0.04`, `0.08`, `0.12`, `0.16`

So the data is recorded every `0.04` seconds, which means:

- `25` frames per second

This gives very detailed movement data.

### 2.9 Simple way to understand tracking data

Read each row like this:

1. Which half is this?
2. What exact moment is this?
3. Where is each player?
4. Where is the ball?

That is the main idea of the tracking files.

## 3. Events Data in Simple Words

The events file is:

- `Sample_Game_2_RawEventsData.csv`

This file tells you what happened in the match.

Examples:

- a pass
- a shot
- a recovery
- a challenge
- a throw-in

### 3.1 What does one row mean?

One row means one football action or event.

For each event, the file may tell you:

- which team did it
- what kind of event it was
- more detail about that event
- when it started and ended
- which player was involved
- where it happened on the pitch

### 3.2 Main columns

Important columns are:

- `Team`: `Home` or `Away`
- `Type`: the main event category
- `Subtype`: extra detail inside the main event category
- `Period`: first or second half
- `Start Frame`, `End Frame`
- `Start Time [s]`, `End Time [s]`
- `From`: player who performed the action
- `To`: receiving player, if there is one
- `Start X`, `Start Y`, `End X`, `End Y`: location on the pitch

These event coordinates use the same `0 to 1` pitch scale as the tracking data.

## 4. Type and Subtype: The Main Idea

This is the easiest way to understand the events file:

- `Type` = main bucket
- `Subtype` = more specific detail inside that bucket

Example:

- `Type = PASS`
- `Subtype = GOAL KICK`

This means the event is a pass, and more specifically it is a goal kick pass.

Another example:

- `Type = SHOT`
- `Subtype = ON TARGET-SAVED`

This means it was a shot, and the shot was on target but saved.

Some rows have no subtype. That usually means the main type already explains enough.

## 5. Unique Values Found in Sample Game 2 Events

From the events file:

- total rows: `1935`
- unique `Team` values: `2`
- unique `Type` values: `9`
- unique non-blank `Subtype` values: `52`
- rows where `Subtype` is blank: `1067`

### 5.1 Team values

- `Home`
- `Away`

### 5.2 Type values

- `BALL LOST`
- `BALL OUT`
- `CARD`
- `CHALLENGE`
- `FAULT RECEIVED`
- `PASS`
- `RECOVERY`
- `SET PIECE`
- `SHOT`

### 5.3 Type counts

- `PASS`: `964`
- `CHALLENGE`: `311`
- `RECOVERY`: `248`
- `BALL LOST`: `233`
- `SET PIECE`: `80`
- `BALL OUT`: `49`
- `SHOT`: `24`
- `FAULT RECEIVED`: `20`
- `CARD`: `6`

## 6. Which Subtypes Come Under Which Type?

Below is the mapping from each `Type` to the `Subtype` values found under it in Sample Game 2.

### 6.1 BALL LOST

- `(blank)`
- `CLEARANCE`
- `CLEARANCE-INTERCEPTION`
- `CROSS-INTERCEPTION`
- `FORCED`
- `FORCED-END HALF`
- `GOAL KICK-INTERCEPTION`
- `HAND BALL`
- `HEAD`
- `HEAD-INTERCEPTION`
- `INTERCEPTION`
- `OFFSIDE`
- `THEFT`

### 6.2 BALL OUT

- `(blank)`
- `CLEARANCE`
- `CROSS`
- `HEAD`
- `HEAD-CLEARANCE`

### 6.3 CARD

- `YELLOW`

### 6.4 CHALLENGE

- `AERIAL-FAULT-LOST`
- `AERIAL-FAULT-WON`
- `AERIAL-LOST`
- `AERIAL-WON`
- `DRIBBLE-WON`
- `FAULT-WON`
- `GROUND`
- `GROUND-ADVANTAGE-LOST`
- `GROUND-ADVANTAGE-WON`
- `GROUND-FAULT-LOST`
- `GROUND-FAULT-WON`
- `GROUND-LOST`
- `GROUND-WON`
- `TACKLE-ADVANTAGE-LOST`
- `TACKLE-ADVANTAGE-WON`
- `TACKLE-FAULT-LOST`
- `TACKLE-FAULT-WON`
- `TACKLE-LOST`
- `TACKLE-WON`

### 6.5 FAULT RECEIVED

- `(blank)`

### 6.6 PASS

- `(blank)`
- `CROSS`
- `DEEP BALL`
- `GOAL KICK`
- `HEAD`
- `HEAD-INTERCEPTION-CLEARANCE`

### 6.7 RECOVERY

- `(blank)`
- `BLOCKED`
- `INTERCEPTION`
- `SAVED`
- `THEFT`

### 6.8 SET PIECE

- `CORNER KICK`
- `FREE KICK`
- `FREE KICK-RETAKEN`
- `KICK OFF`
- `KICK OFF-RETAKEN`
- `PENALTY`
- `THROW IN`

### 6.9 SHOT

- `BLOCKED`
- `HEAD-OFF TARGET-OUT`
- `HEAD-ON TARGET-GOAL`
- `OFF TARGET-HEAD-OUT`
- `OFF TARGET-OUT`
- `ON TARGET-GOAL`
- `ON TARGET-SAVED`

## 7. Important Note About Type and Subtype

A subtype does not always belong to only one type.

Some subtype names appear under more than one main type.

Examples:

- `INTERCEPTION` appears under `BALL LOST` and `RECOVERY`
- `THEFT` appears under `BALL LOST` and `RECOVERY`
- `BLOCKED` appears under `SHOT` and `RECOVERY`
- `CROSS` appears under `PASS` and `BALL OUT`
- `HEAD` appears under `PASS`, `BALL LOST`, and `BALL OUT`
- `CLEARANCE` appears under `BALL LOST` and `BALL OUT`

So when reading the events file, do not look at `Subtype` alone.

Always read:

- `Type` first
- `Subtype` second

Together they explain the event properly.

## 8. Simple Examples of Event Reading

### Example 1

- `Type = PASS`
- `Subtype = (blank)`

Simple meaning:

- a normal pass

### Example 2

- `Type = SET PIECE`
- `Subtype = THROW IN`

Simple meaning:

- a throw-in restart

### Example 3

- `Type = RECOVERY`
- `Subtype = INTERCEPTION`

Simple meaning:

- the team won the ball back through an interception

### Example 4

- `Type = SHOT`
- `Subtype = ON TARGET-GOAL`

Simple meaning:

- a shot on target that resulted in a goal

## 9. How Tracking and Events Work Together

The best way to think about the full dataset is:

- tracking data tells you where everyone was
- events data tells you what happened

So if the events file says there was a pass at a certain time:

- the tracking files can show where the passer, receiver, teammates, opponents, and ball were at that same moment

This is why these files are very useful together.

## 10. Final Summary

Sample Game 2 gives you two views of the same match:

- `Tracking data` for movement and positions over time
- `Events data` for football actions and match incidents

If you remember only a few things, remember these:

- each tracking row = one moment in time
- player positions are stored as `x, y`
- coordinates go from `0` to `1`
- each event row = one football action
- `Type` is the main category
- `Subtype` is the extra detail
- some subtype names can appear under more than one type

That is the core idea of the Sample Game 2 dataset.

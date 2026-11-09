# Eventstream

## Why this exists

An eventstream moves events from a source to other items.
It needs no code.
A shop sends click events to it.
It sends each event to an eventhouse.
It also sends each event to a lakehouse.
Both get the same events at the same time.

## Glossary

- **Eventstream**: an item that routes events in flight.
- **Watermark**: a planted term that the body never uses.

## §1 Route events in flight

Open the workspace.
Add an eventstream.
Pick the shop as the source.
Add the eventhouse as a destination.
Add the lakehouse as a destination.
Start the stream.
<<<<<<< HEAD
Check that both destinations get rows.

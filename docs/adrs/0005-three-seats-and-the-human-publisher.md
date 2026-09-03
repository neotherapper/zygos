---
adr: 0005
title: Three seats, one credential each — the publisher is a person, and the record of what came before
status: proposed
date: 2026-09-03
---

# ADR-0005 — Three seats, one credential each: the publisher is a person, and the record of what came before

## Status

Proposed. Extends ADR-0004, which created the three credentials but left where they sit as a stated
negative consequence ("the separation is only as real as where the keys sit"). This ADR decides where
they sit. It also records, so the next reader does not have to rediscover it, that every spec published
before this date was published without any of the separation described here.

## Context

The library's process says "never merge a research branch without a PR and an independent fidelity
review" (`CLAUDE.md`) and its pipeline has three roles: operator, reviewer, publisher (ADR-0004). Four
observed facts show that, as practised, the roles were names and the review was not independent.

1. **Five specs are Published and no human took any action on any of them.** `deepseek-harness`,
   `rlm`, `exo`, `temper`, and `pi` were drafted, reviewed, and published by one agent in one Claude
   Code session per spec. Before the 2026-09-02 cutover the kernel let the caller declare its role in a
   request header (ADR-0004, Context 3), so the same session wrote the draft, set the header to
   `reviewer` and passed its own review, then set it to `admin` and published. The twelve pull requests
   `#1`–`#12` were all authored by agent sessions and merged under the repository owner's account; the
   last three were merged by an agent session that the owner had told to merge. The owner's name is on
   every merge. The owner did not read the five specs as an approver, and nothing in the process asked
   them to.

2. **After the cutover, all three keys sat in one shell, and the skill told the agent to use the third
   one.** ADR-0004 issued three credentials but they were exported together. The `fidelity-review`
   skill's step 7 instructs the reviewing agent to fire `Publish` with `$ZYGOS_PUBLISHER_KEY`
   (`zygos-curation/agents/curator/skills/fidelity-review/SKILL.md`), and the production separation test
   of 2026-09-02 exercised the publisher key from a shell driven by an agent session. The kernel now
   refuses a self-declared role; the process still handed the publishing credential to the reviewer.

3. **The "independent agent" was a subagent of the drafter.** `docs/research/SKILL.md` §4 asks for an
   agent "that has not seen the draft being written". In every run so far that agent was dispatched
   from the drafting session, with the drafting session's working tree and a prompt the drafter wrote.
   It had not seen the draft being written; it had been told by the drafter what to check.

4. **The first human `Publish` happened on 2026-09-03, on a sandbox, on a placeholder.** The owner
   walked one throwaway entity (`walk-1`) through Draft → UnderReview → Published → Archived by hand on a
   disposable TemperPaw (port 3468, empty store, its own keys), and saw each gate answer: the automaton's
   409 on a missing section, Cedar's 403 for the wrong key, the 409 on the missing fidelity bit, and the
   200 when key, state, and bit all agreed. Production has never had a human publish.

The kernel cannot fix any of this. It resolves a credential to an agent type and enforces the guards
(ADR-0004); it cannot tell a person from a script holding the same key, and it cannot tell whether the
session that recorded a review had drafted the thing it reviewed. Both are facts about where a
credential lives and which process holds it. That is a decision about the library's process, which is
what this ADR is.

## Decision

**A seat is a process or a person holding exactly one of the three credentials. The pipeline has three
seats, and no process holds more than one.**

| Seat | Who fills it | Holds | Reads | Does |
|---|---|---|---|---|
| Drafter | an agent session (Claude Code today; a TemperPaw `Session` later) | `ZYGOS_KEY` | `docs/research/SKILL.md` | creates the Draft, writes the sections, `SubmitForReview` |
| Reviewer | a different agent session that did not draft | `ZYGOS_REVIEWER_KEY` | `fidelity-review/SKILL.md` | re-opens the pinned sources, records pass or fail, `ReviseDraft` |
| Publisher | a person | `ZYGOS_PUBLISHER_KEY` | the `FidelityFindings` and the PR | `Publish`, `Revise`, `Archive`; merges the PR |

Concretely:

- **One key per environment.** A shell, a Claude Code session, or a TemperPaw `Session` is started with
  at most one of the three keys exported. The operator key is the only one that reaches an agent's
  environment by default. The reviewer key reaches the reviewer session and nothing else.
- **The publisher key never enters an environment where an agent runs.** It is exported in the owner's
  own terminal, by the owner, for the duration of a publish, and not in any shell that Claude Code, a
  TemperPaw session, or a script started on their behalf can read. `Publish` is fired by hand, after
  reading the reviewer's findings. Step 7 of the `fidelity-review` skill changes from "fire `Publish`"
  to "stop and report; the publisher seat decides". The skill keeps the 403 rule from ADR-0004: a
  reviewer that finds itself able to publish reports that as a fault, not a convenience.
- **The reviewer is a session with no memory of the draft.** Not a subagent of the drafter, not the
  drafting session after a context reset. It starts fresh, is given the entity id and the skill file,
  and fetches the draft and the pinned sources itself. A different model from the drafter's is
  preferred, not required. The `FidelityFindings` text opens with one line naming the reviewing
  session (tool, model, session id) so that independence can be checked afterwards from the entity
  alone.
- **Denials stay denied.** A pending decision raised by a seat trying an action outside its seat
  (a drafter firing `Publish`, a reviewer firing `Archive`) is evidence that a process held the wrong
  ambition, not a request to approve. The publisher does not approve them; they are left pending or
  denied.
- **The five pre-existing Published specs keep their status and carry a mark.** They are not
  re-reviewed retroactively. `docs/research/README.md` marks each of `deepseek-harness`, `rlm`, `exo`,
  `temper`, `pi` as *published before ADR-0005*. Their next re-pin (ADR-0003) runs through the three
  seats, and the mark is removed when that publish happens.
- **The human's approvals are exactly these:** `Publish` on an entity whose findings they have read;
  the PR merge that exports it to markdown; a `Revise` or `Archive`; and, later, a TemperPaw session
  parked in `WaitingForApproval`. Nothing else in the pipeline waits for a person, and nothing should be
  added that does without an ADR.

## Consequences

**Positive**

- The separation ADR-0004 made *possible* becomes *actual*: three credentials in three places, and the
  entity's own trajectory shows three different credential ids for draft, review, and publish.
- "Who published this?" has an answer that names a person, and "who reviewed it?" names a session that
  can be shown not to be the drafter.
- The gap in the history is written down, in the repo, next to the decision that closes it.

**Negative**

- **Throughput drops.** Publishing waits for a person to read findings and fire an action. A spec drafted
  overnight is Published the next time the owner sits down, not before.
- **Two sessions per spec, not one.** The reviewer must be started separately, with a different key in
  its environment. Until the reviewer runs as a TemperPaw `Session` spawned on `UnderReview` (ADR-0002
  Phase 1 named this job and it was never built), starting it is a manual step.
- **Enforcement is by placement, not by the kernel.** Nothing stops the owner from exporting all three
  keys in one shell again. The check is that the findings line and the trajectory's credential ids
  disagree with the seats, and that someone looks.
- **Reviewer independence is not machine-checked.** The findings header is self-reported by the
  reviewing session. A drafter that lies about being a different session is caught only if a person
  compares session ids.

**Known gap**

The reviewer-as-TemperPaw-`Session` path, which would let the kernel spawn the reviewer with the
reviewer credential and no other, is not built. Until it is, the reviewer seat is a second Claude Code
session that a person starts by hand. That path is the next growth step, and its own ADR.

## Alternatives considered

- **Kernel-enforced human approval on `Publish`** (route `Publish` through a pending decision that a
  second credential approves). Rejected for now: the operator cannot approve its own denial (Temper
  ADR-0172), so a second credential is required anyway, and that credential is the publisher key.
  Routing through a decision adds a step without adding a distinction the kernel can make.
- **Reviewer as a subagent of the drafter, prompted to be adversarial.** This is what ran until now.
  Rejected: it shares the drafter's working tree and receives the drafter's framing of what to check.
  Independence of context is the property; a prompt cannot supply it.
- **Drop the publisher seat and let the PR merge be the only human gate.** Rejected: the entity store
  and the repo would drift, with entities Published that no person had read and markdown merged that no
  entity backed. The two-track problem ADR-0002 already names.
- **Retroactive re-review of the five published specs.** Rejected as a blocking step: five full fidelity
  reviews before any new work. The mark in the target list, cleared on the next re-pin, records the
  state without stopping the library.

# zygos

A library of complete AI agent harness specs, researched and maintained by agents. This glossary
defines the vocabulary zygos uses for its own work — not general research or software terms, and not
the internal vocabulary of any harness being studied (a harness's own terms belong in its spec, not here).

## Language

**FORMAT.md**:
zygos's own root document — the spec format, provenance rules, and scope, formerly (wrongly) named
`DESIGN.md`. Renamed because `DESIGN.md` is a reserved filename in this exact ecosystem: it's Google's
own format spec ([google-labs-code/design.md](https://github.com/google-labs-code/design.md)) for
describing a *visual design system* (color/typography/spacing/component tokens) to coding agents —
katagami generates one per design language, and the name means that specifically, not "this repo's
design document" generically. zygos studies harnesses, not visual identities; nothing here should ever
produce an actual `DESIGN.md`, so the name was free to misuse and easy to misuse. Don't reclaim it.
_Avoid_: naming any zygos file `DESIGN.md`, even informally, even in a code comment.

**spec**:
The one document zygos writes about one harness — every required section (`FORMAT.md` §4.1) plus
frontmatter, filed at `docs/research/harnesses/<slug>.md`. Chosen over "record" specifically: earlier
drafts used both interchangeably, and "spec" also collides with the internal artifact some harnesses
call their own "spec" (Temper's IOA/CSDL/Cedar specs, for one) — when both senses appear in the same
sentence, disambiguate explicitly ("Temper's spec" vs. "the zygos spec").
_Avoid_: record, entry, write-up, article.

**harness**:
The runtime layer that assembles a turn, dispatches tools, and decides what state a model call may
touch — zygos's subject, not a single thing. The word denotes several related objects; `kind`
disambiguates which one a given spec studies rather than picking one meaning and dropping the others.
_Avoid_: using "harness" unqualified when `kind` is what's actually meant.

**kind**:
Frontmatter field classifying *what kind of thing* a harness is, so the library doesn't compare
things that aren't comparable. Three values so far: `agent-harness` (runs the agent loop itself),
`agent-substrate` (the trusted layer a loop reaches into, but does not run the loop — Temper, exo's
own exoharness), `inference-paradigm` (replaces the model call outright, rather than orchestrating
around it — RLM's shape, expected). Not the same question as Axis.

**Axis**:
Frontmatter field and spec section classifying what a harness's design actually addresses — not a
verdict on quality. **Axis A** (structural soundness): can the system enter a broken state? **Axis
B** (factual truth): is the claim the system makes about the world correct? A harness can sit on
either, both, or neither; "trusts the model" on Axis B is itself the finding, not a gap in the write-up.
_Avoid_: "safety" unqualified — see prevention / recovery below.

**prevention** / **recovery**:
The two properties Axis A splits into once a harness claims it. *Prevention* stops the system from
entering a broken state at all (Temper's proof-before-deploy). *Recovery* guarantees a way back out of
one after it happens (exo's rewind). Both get called "safety" in the wild; conflating them is the most
common error this distinction exists to catch. Neither implies the other, and — per the Temper spec's
own correction — a prevention mechanism that relies on a finite test suite generally needs a scoped
recovery backstop for exactly what that suite can't cover.
_Avoid_: "safe" / "safety" as a standalone claim without saying which of the two is meant.

**gate** / **report**:
What a verification mechanism actually does with its own result. A mechanism *gates* when a failure
blocks the change from taking effect (Temper's cascade rejecting a spec at startup). A mechanism only
*reports* when a failure is visible but nothing stops the change (exo's telemetry, which the agent must
act on itself). Don't infer which one a mechanism is from its name — confirm it against what the source
says happens on failure.

**primitive**:
A noun a user or agent actually manipulates when working with a harness — event log, sandbox, capability,
checkpoint. Listed per spec in the `primitives` frontmatter field and the Primitives section. Not every
implementation detail qualifies: if a primitive's "why it matters" cell just restates its "what it is"
cell, it likely isn't one.
_Avoid_: using "primitive" for a general programming concept (a data type, a function) that isn't
specific to how this harness's design commits to a vocabulary.

**embodiment**:
A canonical task actually run on an installed harness, with a trace — this spec's own behavioral
evidence, distinct from anything the studied project claims about itself. Optional in v1;
`embodiment: none` is an honest frontmatter value, not a gap to explain away. Promotes to required once
the library holds 4+ specs, or once a spec makes a claim only a run could confirm (`FORMAT.md` §4.3).
_Avoid_: treating a project's own disclosed benchmarks (however rigorous) as this spec's embodiment —
they're evidence about the project, not about zygos's own verification of it.

**provenance** / **verified_at** / **lifecycle**:
The three required frontmatter fields, none substitutable for the others (`docs/adrs/0001`).
`provenance` answers *are we repeating someone* (`primary` / `secondary` / `relayed` — opening one link
further up a citation chain does not promote it). `verified_at` answers *when did someone look*.
`lifecycle` answers *does this still exist* (`current` / `version-changing` / `retired`) — independent
of how recently it was checked. All three are author-asserted; see "fidelity review" for what actually
checks them.

**fidelity review**:
The adversarial re-check that runs on a spec before merge, by an agent that did not write the draft:
every quote re-verified against its source, every non-quoted claim re-checked for being backwards, the
Limits section's own claims about what wasn't read spot-checked. Distinct from a **presence check**
(does every section exist, is the frontmatter well-formed) — a presence check would pass a wrong spec
outright, which is exactly what happened once already (`temper.md`, PR #1) before this step existed as
a named, required part of the process.
_Avoid_: "review" alone, which doesn't distinguish this from a presence check or a casual read-through.

**re-pin**:
Moving an existing spec's pinned commit forward. Diff every cited source between the two pins; re-read
the ones that changed and carry the rest forward; read what is new (commits, ADRs, self-verification
material); fold the result into the body; update `verified_at` and every pinned link; then run a
fidelity review scoped per `docs/adrs/0003`.
Distinct from **fidelity review**, which checks the draft against its pinned sources: a re-pin checks
the pinned sources against the world. Procedure in `docs/research/SKILL.md` §6.
_Avoid_: "refresh" (sounds like a link check) and "update" (says nothing about what was re-read).

**operator key** / **reviewer key** / **publisher key**:
The three credentials the curation pipeline holds against the local TemperPaw, each an
`AgentCredential` whose agent type decides what Cedar permits it: the operator key drafts and
manages policies, the reviewer key records fidelity reviews, the publisher key publishes and
archives. Authority is resolved from the credential by the kernel, never declared by the caller.
Rationale and the full grant table: `docs/adrs/0004`, `tools/temper/README.md`.
_Avoid_: "admin key" or "the API key" — there is no admin principal over HTTP, and "the" key hides which of the three is meant.

**target list**:
The table in `docs/research/README.md` — one row per harness, `kind`, a pinned commit SHA, and a status
(`not-started` / `done` / `blocked`). A row is not a spec; it's the queue entry that becomes one.

**concept document**:
A cross-cutting finding lifted out of `docs/research/harnesses/` into `docs/concepts/` once it recurs
across three or more specs, citing each occurrence. The durable output of the library — individual
specs age as their subjects change version; a concept, once verified across several, ages more slowly.
None written yet as of this glossary; `docs/concepts/README.md` tracks candidates.

**ADR** (in this repo):
A decision about **zygos itself** — its spec format, scope, or process. Never about a harness being
studied; a finding about a harness belongs in that harness's spec, not an ADR. Lives in `docs/adrs/`
(plural — note this differs from some other repos' `docs/adr/` singular convention; zygos's own is
established and stays as-is).

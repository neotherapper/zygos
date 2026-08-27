# zygos Phase 1: Temper-Backed Curation Pipeline — Implementation Plan

> **Phase 1 complete — merged to `main` at `6b3408c` (2026-08-27).** DeepSeek Harness (`en-01a014ba-3158-7320-9c35-5153a73b525a` `Published`) via PR #5 and RLM (`en-01a04501-8081-7730-b6ce-852b67b7d524` `Published`) via PR #6 are both merged; `docs/research/harnesses/` now holds 4 specs (exo, temper, deepseek-harness, rlm). Next step per `docs/adrs/0002-temper-backed-curation-pipeline.md:Addendum 2026-08-27` is backfilling `exo`/`temper` into entities, not a 5th net-new harness. A fresh agent should start from that ADR addendum and `docs/research/README.md`, not from the checkboxes below (kept for audit).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Get one harness spec (DeepSeek Harness) through a real Temper-backed pipeline end to end —
entity created, sections written by an agent skill, a `SubmitForReview` guard enforcing presence,
an automated fidelity-review job, `Publish` generating the same markdown export readers see today.

**Architecture:** Two Temper apps in this repo, `zygos-commons/` (the `HarnessSpec` entity: CSDL data
model + I/O Automaton state machine + Cedar policy) and `zygos-curation/` (two agent skills:
`synthesize-harness`, `fidelity-review`), running inside a local TemperPaw server with the apps
symlinked into its `os-apps/` directory — the exact mechanism katagami itself uses, confirmed against
katagami's own README before writing this plan.

**Tech Stack:** Rust (Temper/TemperPaw, built from source), TOML (I/O Automaton specs), XML (CSDL data
model), Cedar (authorization policy), Markdown+Python-style tool calls (curation agent skills), Docker
(Postgres for TemperPaw's event store).

**Spec:** `docs/adrs/0002-temper-backed-curation-pipeline.md`

## Global Constraints

- Pin `nerdsane/temperpaw` at commit `75cc6c52218a7698baf517a94070c92f3c2222fe` and `nerdsane/temper`
  at `2f43ecefaa00bf2e9d75c6b67c2ddf8857821400` — the same SHA already cited throughout this repo's
  Temper spec, so the running server matches what was researched. Do not build against `main`.
- `HarnessSpec`'s state machine is `Draft → UnderReview → Published → Archived` — exactly katagami's
  `design_language` shape (`FORMAT.md` §4.2, ADR-0002), not a new one invented for this app.
- Every `HarnessSpec` field name mirrors an existing zygos vocabulary term from `CONTEXT.md` and
  `FORMAT.md` §4 — do not invent new names for concepts that already have one.
- `Publish` must produce a markdown file byte-shape-compatible with `docs/research/_template.md` and
  the two existing specs (`exo.md`, `temper.md`) — section order, heading text, frontmatter field
  order. A reader must not be able to tell a Published-then-exported spec from a hand-merged one.
- No task in this plan touches `docs/research/harnesses/exo.md` or `temper.md` — Phase 1's proof target
  is a **third**, new spec (DeepSeek Harness), per ADR-0002's stated success criterion. Migrating the
  first two into entities is explicitly out of scope here.
- Follow `docs/research/SKILL.md` for *what* to research and how to fill each section — this plan does
  not redefine that; it wires an agent to execute it through Temper instead of by hand.
- **Guard scope, stated honestly, not implied.** IOA's guard language, per the only syntax evidenced
  in Temper's reference app (`is_true`, `items > 0` — boolean and numeric comparisons over state, no
  string-format or regex predicates), can express "all sections present" and "identity fields present."
  It cannot express "`artifact_url` matches a 40-hex SHA" or "every quote has a resolving source anchor"
  without inventing guard syntax no primary source has shown. Those two items from ADR-0001's mechanical
  column are routed to Task 4's fidelity-review check instead, not silently dropped and not faked into
  the guard. This is a real, disclosed narrowing of ADR-0002 line 65's "every required frontmatter field"
  language — recorded here and again in Task 6's addendum, not hidden.
- **Frontmatter list fields are YAML arrays, not scalars, everywhere else in this repo** (`axis: [A]`,
  `primitives: [...]` — confirmed against `_template.md`, `exo.md`, `temper.md`). `Axis` and `Primitives`
  are `Collection(Edm.String)` in the CSDL below, not `Edm.String` — a scalar would silently violate this
  plan's own byte-shape-compatible-export constraint.

---

### Task 1: Stand up TemperPaw locally and confirm the app-loading mechanism

**Files:**
- Create (outside this repo): `~/Developer/projects/temperpaw/` — a fresh clone
- Create: `docs/superpowers/plans/2026-08-16-temper-backed-pipeline-phase1-findings.md` — Task 1's
  investigative output, referenced by every later task

**Interfaces:**
- Produces: confirmation (or correction) of every assumption Tasks 2–6 depend on — the exact
  `os-apps/` symlink mechanism, the exact command that loads and serves symlinked apps, and how a
  curation-agent skill actually gets dispatched against a running server. Later tasks cite this file
  for anything not already confirmed by primary source in this plan.

This is the one investigative task in the plan. Katagami's own README was read before writing this
plan and gives the mechanism in outline (`ln -s ... os-apps/<app> && cargo run`), but this repo has
never run Temper or TemperPaw, and the exact CurationJob/skill-dispatch machinery katagami-curation
relies on (its `wasm/build_session_message` and `wasm/finalize_spawned_session` crates) has not been
read. Tasks 3–4 assume a working dispatch path exists; this task proves it does, or reports precisely
what's missing before any entity/skill code is written against an assumption.

- [ ] **Step 1: Install the Rust toolchain**

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"
rustc --version   # expect: rustc 1.92 or newer, per Temper's README badge
cargo --version
```

- [ ] **Step 2: Clone TemperPaw at the pinned commit and build it**

```bash
mkdir -p ~/Developer/projects
git clone https://github.com/nerdsane/temperpaw.git ~/Developer/projects/temperpaw
cd ~/Developer/projects/temperpaw
git checkout 75cc6c52218a7698baf517a94070c92f3c2222fe
cargo build --release
```

Expected: builds without error. This is the first real signal — if the pinned SHA doesn't build, stop
and record why in the findings file before going further; do not silently switch to `main`.

- [ ] **Step 3: Run it and get through first-run setup**

```bash
./target/release/temperpaw doctor
./target/release/temperpaw run
```

Expected, per TemperPaw's own README: an interactive CLI walkthrough (API key, messaging). Record in
the findings file exactly what it asks for and what's needed to get past it — if it hard-requires a
Discord/Slack connection to boot, that's a real constraint for Tasks 3–6's automation and needs to be
named, not worked around silently.

- [ ] **Step 4: Read TemperPaw's own architecture docs before touching os-apps/**

```bash
cat ~/Developer/projects/temperpaw/AGENTS.md
cat ~/Developer/projects/temperpaw/docs/development.md
```

Answer, and write into the findings file: (a) is `os-apps/` a TemperPaw-level concept or specific to
how katagami's own launcher wires it up — if TemperPaw itself doesn't have this directory by default,
find where it actually comes from; (b) what mechanism actually dispatches a curation-agent skill
against an entity — is it a Temper `reaction`, a WASM integration module, or something orchestrated
outside Temper entirely; (c) confirm the sandboxed Python REPL tool surface referenced in katagami's
skill files (`temper.create`, `temper.action`, `temper.get`, `sandbox.bash`, `sandbox.write`) is
reachable from TemperPaw, and how an agent gets access to it; (d) **specifically for Task 4**: does
Temper/TemperPaw expose a primitive that fires automatically when an entity enters a given state (a
`reaction`, a state-entry hook, katagami's `review-quality` job's own trigger mechanism) — ADR-0002 line
72-75 requires fidelity-review to run this way, "not as a manually-dispatched agent," and Task 4 below
is written conditionally on what this step finds. If no such primitive is exposed, that is itself the
finding — record it plainly rather than building the dispatched-skill shape and calling it equivalent;
(e) confirm IOA's actual effect-type vocabulary — every effect in `order.ioa.toml` is a literal
`{ type = "set_bool", var = "...", value = true }`, never parametric. Task 2's `RecordFidelityReview`
action needs its `Passed` input parameter to flow into the `fidelity_review_passed` state variable at
call time; the plan currently names this `set_bool_from_param` as a placeholder pending this check —
confirm the real name, or confirm no parametric effect exists and split the action into two literal
ones (`RecordFidelityReviewPassed` / `RecordFidelityReviewFailed`) before Task 2 is implemented.

- [ ] **Step 5: Smoke-test the OData surface**

```bash
curl -s http://localhost:3000/tdata/\$metadata | head -50
```

Expected: an empty or near-empty CSDL document (no apps loaded yet) — confirms the server is actually
serving before Task 2 adds an app to it.

- [x] **Step 6: Commit the findings file**

```bash
cd /Users/georgiospilitsoglou/Developer/projects/zygos
git add docs/superpowers/plans/2026-08-16-temper-backed-pipeline-phase1-findings.md
git commit -m "Task 1 findings: TemperPaw local setup, app-loading mechanism confirmed"
```

**If Step 4 reveals the dispatch mechanism is materially different from what Tasks 3–4 below assume**
(e.g., it requires a WASM integration crate rather than a markdown skill file), stop before Task 2 and
flag it — this plan's later tasks may need rewriting against what was actually found, the same way the
Temper spec itself was corrected after fidelity review found a primary source contradicted a first
draft. Do not proceed on the original assumption once evidence contradicts it.

---

### Task 2: Define the `HarnessSpec` entity — `zygos-commons`

**Files:**
- Create: `zygos-commons/specs/model.csdl.xml`
- Create: `zygos-commons/specs/harness_spec.ioa.toml`
- Create: `zygos-commons/specs/policies/harness_spec.cedar`

**Interfaces:**
- Produces: the `HarnessSpec` entity type, queryable at `/tdata/HarnessSpecs`, with bound actions
  `SetIdentity`, `WritePhilosophy`, `WritePrimitivesSection`, `WriteLoop`, `WriteBoundaries`,
  `WriteVerification`, `SetAxis`, `WriteEconomics`, `WriteTradeoffs`, `WriteWhatToSteal`,
  `WriteWhatNotTo`, `SetEmbodiment`, `WriteLimits`, `WriteSources`, `SubmitForReview`,
  `RecordFidelityReview`, `ReviseDraft`, `Publish`, `Revise`, `Archive` — consumed by Task 3's skill and
  Task 4's review job by exact action name. `ReviseDraft` (`UnderReview → Draft`) is the correction path
  a failed fidelity review takes — without it a `NEEDS REVISION` verdict has nowhere for the entity to
  go; `Revise` (`Published → UnderReview`) is the separate, later, already-published-content correction
  path and is unchanged.

- [ ] **Step 1: Write the CSDL data model**

```xml
<?xml version="1.0" encoding="utf-8"?>
<!--
  zygos-commons: HarnessSpec data model

  Mirrors the field names already established in FORMAT.md §4 and every
  existing spec's frontmatter. See docs/adrs/0002 for why this exists.
-->
<edmx:Edmx Version="4.0" xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx">
  <edmx:DataServices>

    <Schema Namespace="Temper.Vocab" xmlns="http://docs.oasis-open.org/odata/ns/edm">
      <Term Name="StateMachine.States" Type="Collection(Edm.String)" AppliesTo="EntityType"/>
      <Term Name="StateMachine.InitialState" Type="Edm.String" AppliesTo="EntityType"/>
      <Term Name="StateMachine.ValidFromStates" Type="Collection(Edm.String)" AppliesTo="Action"/>
      <Term Name="StateMachine.TargetState" Type="Edm.String" AppliesTo="Action"/>
      <Term Name="Agent.Hint" Type="Edm.String" AppliesTo="Action Function EntityType"/>
      <Term Name="ShardKey" Type="Edm.String" AppliesTo="EntityType"/>
      <Term Name="AuthZ.CedarPolicy" Type="Edm.String" AppliesTo="EntityType Action Function"/>
    </Schema>

    <Schema Namespace="Zygos" xmlns="http://docs.oasis-open.org/odata/ns/edm">

      <EnumType Name="HarnessKind">
        <Member Name="AgentHarness" Value="0"/>
        <Member Name="AgentSubstrate" Value="1"/>
        <Member Name="InferenceParadigm" Value="2"/>
      </EnumType>

      <EnumType Name="Lifecycle">
        <Member Name="Current" Value="0"/>
        <Member Name="VersionChanging" Value="1"/>
        <Member Name="Retired" Value="2"/>
      </EnumType>

      <EnumType Name="Provenance">
        <Member Name="Primary" Value="0"/>
        <Member Name="Secondary" Value="1"/>
        <Member Name="Relayed" Value="2"/>
      </EnumType>

      <EnumType Name="EmbodimentLevel">
        <Member Name="None" Value="0"/>
        <Member Name="Partial" Value="1"/>
        <Member Name="Full" Value="2"/>
      </EnumType>

      <EnumType Name="SpecStatus">
        <Member Name="Draft" Value="0"/>
        <Member Name="UnderReview" Value="1"/>
        <Member Name="Published" Value="2"/>
        <Member Name="Archived" Value="3"/>
      </EnumType>

      <EntityType Name="HarnessSpec">
        <Key><PropertyRef Name="Id"/></Key>
        <Property Name="Id" Type="Edm.Guid" Nullable="false"/>

        <!-- Frontmatter fields -->
        <Property Name="Slug" Type="Edm.String" Nullable="false"/>
        <Property Name="Title" Type="Edm.String"/>
        <Property Name="Url" Type="Edm.String"/>
        <Property Name="ArtifactUrl" Type="Edm.String"/>
        <Property Name="Commit" Type="Edm.String"/>
        <Property Name="Language" Type="Edm.String"/>
        <Property Name="Kind" Type="Zygos.HarnessKind"/>
        <Property Name="License" Type="Edm.String"/>
        <Property Name="ProjectStatus" Type="Edm.String"/>
        <Property Name="Lifecycle" Type="Zygos.Lifecycle"/>
        <Property Name="Provenance" Type="Zygos.Provenance"/>
        <Property Name="VerifiedAt" Type="Edm.DateTimeOffset"/>
        <Property Name="Axis" Type="Collection(Edm.String)"/>
        <Property Name="Primitives" Type="Collection(Edm.String)"/>
        <Property Name="Embodiment" Type="Zygos.EmbodimentLevel" DefaultValue="None"/>

        <!-- Body sections (FORMAT.md §4.1 order; heading text each maps to is fixed in Task 5 Step 1,
             not implied by these property names — "Verification" here is not "## Verification strategy",
             "WhichAxis" here is not "## Which axis") -->
        <Property Name="Philosophy" Type="Edm.String"/>
        <Property Name="PrimitivesSection" Type="Edm.String"/>
        <Property Name="Loop" Type="Edm.String"/>
        <Property Name="Boundaries" Type="Edm.String"/>
        <Property Name="Verification" Type="Edm.String"/>
        <Property Name="WhichAxis" Type="Edm.String"/>
        <Property Name="Economics" Type="Edm.String"/>
        <Property Name="Tradeoffs" Type="Edm.String"/>
        <Property Name="WhatToSteal" Type="Edm.String"/>
        <Property Name="WhatNotTo" Type="Edm.String"/>
        <Property Name="EmbodimentSection" Type="Edm.String"/>
        <Property Name="Limits" Type="Edm.String"/>
        <Property Name="Sources" Type="Edm.String"/>

        <!-- Presence flags — the guard's mechanical checklist, per ADR-0001's left column, narrowed to
             what IOA's evidenced boolean-guard syntax can express (see Global Constraints above) -->
        <Property Name="HasIdentity" Type="Edm.Boolean" DefaultValue="false"/>
        <Property Name="HasPhilosophy" Type="Edm.Boolean" DefaultValue="false"/>
        <Property Name="HasPrimitivesSection" Type="Edm.Boolean" DefaultValue="false"/>
        <Property Name="HasLoop" Type="Edm.Boolean" DefaultValue="false"/>
        <Property Name="HasBoundaries" Type="Edm.Boolean" DefaultValue="false"/>
        <Property Name="HasVerification" Type="Edm.Boolean" DefaultValue="false"/>
        <Property Name="HasAxis" Type="Edm.Boolean" DefaultValue="false"/>
        <Property Name="HasEconomics" Type="Edm.Boolean" DefaultValue="false"/>
        <Property Name="HasTradeoffs" Type="Edm.Boolean" DefaultValue="false"/>
        <Property Name="HasWhatToSteal" Type="Edm.Boolean" DefaultValue="false"/>
        <Property Name="HasWhatNotTo" Type="Edm.Boolean" DefaultValue="false"/>
        <Property Name="HasLimits" Type="Edm.Boolean" DefaultValue="false"/>
        <Property Name="HasSources" Type="Edm.Boolean" DefaultValue="false"/>

        <!-- Fidelity review outcome, set by Task 4's job -->
        <Property Name="FidelityReviewPassed" Type="Edm.Boolean" DefaultValue="false"/>
        <Property Name="FidelityFindings" Type="Edm.String"/>

        <Property Name="Status" Type="Zygos.SpecStatus" Nullable="false" DefaultValue="Draft"/>
        <Property Name="Version" Type="Edm.Int32" DefaultValue="0"/>

        <Annotation Term="Temper.Vocab.StateMachine.States">
          <Collection>
            <String>Draft</String><String>UnderReview</String>
            <String>Published</String><String>Archived</String>
          </Collection>
        </Annotation>
        <Annotation Term="Temper.Vocab.StateMachine.InitialState" String="Draft"/>
        <Annotation Term="Temper.Vocab.ShardKey" String="Id"/>
        <Annotation Term="Temper.Vocab.AuthZ.CedarPolicy" String="policies/harness_spec.cedar"/>
      </EntityType>

      <Action Name="SetIdentity" IsBound="true">
        <Parameter Name="bindingParameter" Type="Zygos.HarnessSpec"/>
        <Parameter Name="Title" Type="Edm.String" Nullable="false"/>
        <Parameter Name="Url" Type="Edm.String" Nullable="false"/>
        <Parameter Name="ArtifactUrl" Type="Edm.String" Nullable="false"/>
        <Parameter Name="Commit" Type="Edm.String" Nullable="false"/>
        <Parameter Name="Language" Type="Edm.String"/>
        <Parameter Name="Kind" Type="Zygos.HarnessKind" Nullable="false"/>
        <Parameter Name="License" Type="Edm.String"/>
        <Parameter Name="ProjectStatus" Type="Edm.String"/>
        <Parameter Name="Lifecycle" Type="Zygos.Lifecycle" Nullable="false"/>
        <Parameter Name="Provenance" Type="Zygos.Provenance" Nullable="false"/>
        <Parameter Name="VerifiedAt" Type="Edm.DateTimeOffset" Nullable="false"/>
        <ReturnType Type="Zygos.HarnessSpec"/>
        <Annotation Term="Temper.Vocab.StateMachine.ValidFromStates">
          <Collection><String>Draft</String></Collection>
        </Annotation>
        <Annotation Term="Temper.Vocab.Agent.Hint"
          String="Title/Url/ArtifactUrl/Commit/Kind/Lifecycle/Provenance/VerifiedAt are Nullable=false —
          the eight-field identity core the SubmitForReview guard's has_identity flag depends on."/>
      </Action>

      <Action Name="WritePhilosophy" IsBound="true">
        <Parameter Name="bindingParameter" Type="Zygos.HarnessSpec"/>
        <Parameter Name="Text" Type="Edm.String" Nullable="false"/>
        <ReturnType Type="Zygos.HarnessSpec"/>
        <Annotation Term="Temper.Vocab.StateMachine.ValidFromStates">
          <Collection><String>Draft</String></Collection>
        </Annotation>
        <Annotation Term="Temper.Vocab.Agent.Hint"
          String="Quote the project's own words per FORMAT.md §4.1 — paraphrase loses the position."/>
      </Action>

      <!-- WriteLoop, WriteBoundaries, WriteVerification, WriteEconomics, WriteTradeoffs,
           WriteWhatToSteal, WriteWhatNotTo, WriteLimits, WriteSources: identical shape to
           WritePhilosophy above, one Text parameter each, bound to Draft. Write each one
           following this exact pattern before Step 2.

           WritePrimitivesSection is the ONE exception — it also carries the frontmatter list,
           see Step 2 below. -->

      <Action Name="WritePrimitivesSection" IsBound="true">
        <Parameter Name="bindingParameter" Type="Zygos.HarnessSpec"/>
        <Parameter Name="Text" Type="Edm.String" Nullable="false"/>
        <Parameter Name="Primitives" Type="Collection(Edm.String)" Nullable="false"/>
        <ReturnType Type="Zygos.HarnessSpec"/>
        <Annotation Term="Temper.Vocab.StateMachine.ValidFromStates">
          <Collection><String>Draft</String></Collection>
        </Annotation>
        <Annotation Term="Temper.Vocab.Agent.Hint"
          String="Text is the '## Primitives' body table; Primitives is the short-slug frontmatter list
          (e.g. [event-log, artifact, sandbox]) — both are authored in the same pass, so both are set by
          this one action, the same reasoning as SetAxis bundling Axis with Analysis."/>
      </Action>

      <Action Name="SetAxis" IsBound="true">
        <Parameter Name="bindingParameter" Type="Zygos.HarnessSpec"/>
        <Parameter Name="Axis" Type="Collection(Edm.String)" Nullable="false"/>
        <Parameter Name="Analysis" Type="Edm.String" Nullable="false"/>
        <ReturnType Type="Zygos.HarnessSpec"/>
        <Annotation Term="Temper.Vocab.StateMachine.ValidFromStates">
          <Collection><String>Draft</String></Collection>
        </Annotation>
        <Annotation Term="Temper.Vocab.Agent.Hint"
          String="Axis sets the frontmatter axis: [...] list (e.g. [A]); Analysis is the '## Which axis'
          body prose, stored in the WhichAxis property — the two are written together, not separately,
          because the frontmatter tag and its justification are always authored in the same pass."/>
      </Action>

      <Action Name="SetEmbodiment" IsBound="true">
        <Parameter Name="bindingParameter" Type="Zygos.HarnessSpec"/>
        <Parameter Name="Level" Type="Zygos.EmbodimentLevel" Nullable="false"/>
        <Parameter Name="Text" Type="Edm.String"/>
        <ReturnType Type="Zygos.HarnessSpec"/>
        <Annotation Term="Temper.Vocab.StateMachine.ValidFromStates">
          <Collection><String>Draft</String></Collection>
        </Annotation>
      </Action>

      <Action Name="SubmitForReview" IsBound="true">
        <Parameter Name="bindingParameter" Type="Zygos.HarnessSpec"/>
        <ReturnType Type="Zygos.HarnessSpec"/>
        <Annotation Term="Temper.Vocab.StateMachine.ValidFromStates">
          <Collection><String>Draft</String></Collection>
        </Annotation>
        <Annotation Term="Temper.Vocab.StateMachine.TargetState" String="UnderReview"/>
      </Action>

      <Action Name="RecordFidelityReview" IsBound="true">
        <Parameter Name="bindingParameter" Type="Zygos.HarnessSpec"/>
        <Parameter Name="Passed" Type="Edm.Boolean" Nullable="false"/>
        <Parameter Name="Findings" Type="Edm.String"/>
        <ReturnType Type="Zygos.HarnessSpec"/>
        <Annotation Term="Temper.Vocab.StateMachine.ValidFromStates">
          <Collection><String>UnderReview</String></Collection>
        </Annotation>
      </Action>

      <Action Name="ReviseDraft" IsBound="true">
        <Parameter Name="bindingParameter" Type="Zygos.HarnessSpec"/>
        <Parameter Name="Reason" Type="Edm.String" Nullable="false"/>
        <ReturnType Type="Zygos.HarnessSpec"/>
        <Annotation Term="Temper.Vocab.StateMachine.ValidFromStates">
          <Collection><String>UnderReview</String></Collection>
        </Annotation>
        <Annotation Term="Temper.Vocab.StateMachine.TargetState" String="Draft"/>
        <Annotation Term="Temper.Vocab.Agent.Hint"
          String="The correction path for a NEEDS REVISION fidelity-review verdict — distinct from
          Revise (Published to UnderReview), which corrects already-published content instead. Existing
          Write* calls stay true in has_* flags; only the sections named in Reason need re-writing before
          SubmitForReview is called again."/>
      </Action>

      <Action Name="Publish" IsBound="true">
        <Parameter Name="bindingParameter" Type="Zygos.HarnessSpec"/>
        <ReturnType Type="Zygos.HarnessSpec"/>
        <Annotation Term="Temper.Vocab.StateMachine.ValidFromStates">
          <Collection><String>UnderReview</String></Collection>
        </Annotation>
        <Annotation Term="Temper.Vocab.StateMachine.TargetState" String="Published"/>
      </Action>

      <Action Name="Revise" IsBound="true">
        <Parameter Name="bindingParameter" Type="Zygos.HarnessSpec"/>
        <Parameter Name="Reason" Type="Edm.String" Nullable="false"/>
        <ReturnType Type="Zygos.HarnessSpec"/>
        <Annotation Term="Temper.Vocab.StateMachine.ValidFromStates">
          <Collection><String>Published</String></Collection>
        </Annotation>
        <Annotation Term="Temper.Vocab.StateMachine.TargetState" String="UnderReview"/>
      </Action>

      <Action Name="Archive" IsBound="true">
        <Parameter Name="bindingParameter" Type="Zygos.HarnessSpec"/>
        <Parameter Name="Reason" Type="Edm.String" Nullable="false"/>
        <ReturnType Type="Zygos.HarnessSpec"/>
        <Annotation Term="Temper.Vocab.StateMachine.TargetState" String="Archived"/>
      </Action>

      <EntityContainer Name="ZygosContainer">
        <EntitySet Name="HarnessSpecs" EntityType="Zygos.HarnessSpec"/>
      </EntityContainer>

    </Schema>
  </edmx:DataServices>
</edmx:Edmx>
```

- [ ] **Step 2: Write the remaining `Write*` actions by the `WritePhilosophy` pattern**

Add `WriteLoop`, `WriteBoundaries`, `WriteVerification`, `WriteEconomics`, `WriteTradeoffs`,
`WriteWhatToSteal`, `WriteWhatNotTo`, `WriteLimits`, `WriteSources` to the `<Schema Namespace="Zygos">`
block — each identical in shape to `WritePhilosophy`: one `Text` parameter, bound from `Draft`,
returning `Zygos.HarnessSpec`. Nine actions, same three lines each as the template above.
`WritePrimitivesSection` is already written in full above (Step 1) — it takes a second `Primitives`
parameter and is not part of this batch.

- [ ] **Step 3: Write the I/O Automaton behavioral spec**

```toml
# HarnessSpec — I/O Automaton Specification
# States mirror katagami's design_language.ioa.toml exactly (Draft/UnderReview/Published/Archived).

[automaton]
name = "HarnessSpec"
states = ["Draft", "UnderReview", "Published", "Archived"]
initial = "Draft"

# --- State Variables: one boolean per required section, mirroring the
# CSDL Has* properties. The IOA guard reads these; the CSDL properties
# are what an agent actually sets via the Write* actions' effects. ---

[[state]]
name = "has_identity"
type = "bool"
initial = "false"

[[state]]
name = "has_philosophy"
type = "bool"
initial = "false"

[[state]]
name = "has_primitives_section"
type = "bool"
initial = "false"

[[state]]
name = "has_loop"
type = "bool"
initial = "false"

[[state]]
name = "has_boundaries"
type = "bool"
initial = "false"

[[state]]
name = "has_verification"
type = "bool"
initial = "false"

[[state]]
name = "has_axis"
type = "bool"
initial = "false"

[[state]]
name = "has_economics"
type = "bool"
initial = "false"

[[state]]
name = "has_tradeoffs"
type = "bool"
initial = "false"

[[state]]
name = "has_what_to_steal"
type = "bool"
initial = "false"

[[state]]
name = "has_what_not_to"
type = "bool"
initial = "false"

[[state]]
name = "has_limits"
type = "bool"
initial = "false"

[[state]]
name = "has_sources"
type = "bool"
initial = "false"

[[state]]
name = "fidelity_review_passed"
type = "bool"
initial = "false"

# --- Actions ---

[[action]]
name = "WritePhilosophy"
kind = "input"
from = ["Draft"]
effect = [{ type = "set_bool", var = "has_philosophy", value = true }]
hint = "Quote the project's own words per FORMAT.md §4.1 — paraphrase loses the position."

[[action]]
name = "WritePrimitivesSection"
kind = "input"
from = ["Draft"]
effect = [{ type = "set_bool", var = "has_primitives_section", value = true }]

[[action]]
name = "WriteLoop"
kind = "input"
from = ["Draft"]
effect = [{ type = "set_bool", var = "has_loop", value = true }]

[[action]]
name = "WriteBoundaries"
kind = "input"
from = ["Draft"]
effect = [{ type = "set_bool", var = "has_boundaries", value = true }]

[[action]]
name = "WriteVerification"
kind = "input"
from = ["Draft"]
effect = [{ type = "set_bool", var = "has_verification", value = true }]

[[action]]
name = "SetAxis"
kind = "input"
from = ["Draft"]
effect = [{ type = "set_bool", var = "has_axis", value = true }]

[[action]]
name = "WriteEconomics"
kind = "input"
from = ["Draft"]
effect = [{ type = "set_bool", var = "has_economics", value = true }]

[[action]]
name = "WriteTradeoffs"
kind = "input"
from = ["Draft"]
effect = [{ type = "set_bool", var = "has_tradeoffs", value = true }]

[[action]]
name = "WriteWhatToSteal"
kind = "input"
from = ["Draft"]
effect = [{ type = "set_bool", var = "has_what_to_steal", value = true }]

[[action]]
name = "WriteWhatNotTo"
kind = "input"
from = ["Draft"]
effect = [{ type = "set_bool", var = "has_what_not_to", value = true }]

[[action]]
name = "SetEmbodiment"
kind = "input"
from = ["Draft"]

[[action]]
name = "WriteLimits"
kind = "input"
from = ["Draft"]
effect = [{ type = "set_bool", var = "has_limits", value = true }]

[[action]]
name = "WriteSources"
kind = "input"
from = ["Draft"]
effect = [{ type = "set_bool", var = "has_sources", value = true }]

[[action]]
name = "SetIdentity"
kind = "input"
from = ["Draft"]
effect = [{ type = "set_bool", var = "has_identity", value = true }]
hint = "Sets has_identity — the eight Nullable=false CSDL parameters (Title/Url/ArtifactUrl/Commit/Kind/Lifecycle/Provenance/VerifiedAt) are the guard's frontmatter check, per ADR-0002 line 65."

# --- The guard that makes ADR-0001's left column real ---

[[action]]
name = "SubmitForReview"
kind = "internal"
from = ["Draft"]
to = "UnderReview"
guard = [
  { type = "is_true", var = "has_identity" },
  { type = "is_true", var = "has_philosophy" },
  { type = "is_true", var = "has_primitives_section" },
  { type = "is_true", var = "has_loop" },
  { type = "is_true", var = "has_boundaries" },
  { type = "is_true", var = "has_verification" },
  { type = "is_true", var = "has_axis" },
  { type = "is_true", var = "has_economics" },
  { type = "is_true", var = "has_tradeoffs" },
  { type = "is_true", var = "has_what_to_steal" },
  { type = "is_true", var = "has_what_not_to" },
  { type = "is_true", var = "has_limits" },
  { type = "is_true", var = "has_sources" },
]
hint = "Requires identity fields and all eleven required sections present. Embodiment is optional per FORMAT.md §4.3 — not gated here. Does NOT check artifact_url's SHA format or quote-source anchors — IOA's boolean/comparator guard syntax can't express those; Task 4's fidelity-review job covers them instead (see Global Constraints)."

[[action]]
name = "RecordFidelityReview"
kind = "input"
from = ["UnderReview"]
# set_bool_from_param binds the state variable to the action's own Passed parameter at call time —
# this exact effect-type name is NOT confirmed against any primitive syntax this plan has actually
# seen (order.ioa.toml's effects are all literal `value = true/false`, never parametric). Task 1 (or
# a direct read of Temper's own IOA effect-type reference, if one exists) needs to confirm the real
# name/shape before this compiles; if none exists, RecordFidelityReview's caller must instead invoke
# two literal actions (e.g. RecordFidelityReviewPassed / RecordFidelityReviewFailed) and this action
# and its guard below (line ~662) get split accordingly. Flagged here rather than left implicit,
# same discipline as Task 1's other open primitive questions.
effect = [{ type = "set_bool_from_param", var = "fidelity_review_passed", param = "Passed" }]

[[action]]
name = "Publish"
kind = "internal"
from = ["UnderReview"]
to = "Published"
guard = [{ type = "is_true", var = "fidelity_review_passed" }]
hint = "Only publishes once the automated fidelity-review job has recorded a pass."

[[action]]
name = "ReviseDraft"
kind = "input"
from = ["UnderReview"]
to = "Draft"
effect = [{ type = "set_bool", var = "fidelity_review_passed", value = false }]
hint = "The path a NEEDS REVISION fidelity-review verdict takes. has_* flags are untouched — only the sections named in Reason need re-writing via their Write* action before SubmitForReview runs again."

[[action]]
name = "Revise"
kind = "input"
from = ["Published"]
to = "UnderReview"
effect = [{ type = "set_bool", var = "fidelity_review_passed", value = false }]

[[action]]
name = "Archive"
kind = "input"
from = ["Draft", "UnderReview", "Published"]
to = "Archived"

# --- Safety Invariants ---

[[invariant]]
name = "PublishRequiresFidelityReview"
when = ["Published"]
assert = "fidelity_review_passed"

[[invariant]]
name = "ArchivedIsFinal"
when = ["Archived"]
assert = "no_further_transitions"
```

- [ ] **Step 4: Write the Cedar authorization policy**

```
// Cedar ABAC policies for HarnessSpec
// Principal types: Agent, Admin. Public read — this repo is public by design (FORMAT.md §6).
//
// Every one of the 20 HarnessSpec actions (Task 2 Step 1-3) gets an explicit rule below — no generic
// "write"/"create"/"update" bucket, because unlike the Temper reference app's Order entity, HarnessSpec
// has no single generic write action: SetIdentity and the eleven Write*/Set* authoring actions are
// each their own named action, so each is named here (the reference app's own convention — see
// permit(...action in [Action::"create", Action::"update", Action::"submitOrder", ...])... — of listing
// every action a rule actually covers, applied literally instead of assumed).

permit(
    principal,
    action == Action::"read",
    resource is HarnessSpec
);

// Drafting actions — every action bound from Draft in the IOA (Task 2 Step 3): identity, all eleven
// Write*/Set* section actions, and submitting for review.
permit(
    principal is Agent,
    action in [
        Action::"setIdentity", Action::"writePhilosophy", Action::"writePrimitivesSection",
        Action::"writeLoop", Action::"writeBoundaries", Action::"writeVerification",
        Action::"setAxis", Action::"writeEconomics", Action::"writeTradeoffs",
        Action::"writeWhatToSteal", Action::"writeWhatNotTo", Action::"setEmbodiment",
        Action::"writeLimits", Action::"writeSources", Action::"submitForReview"
    ],
    resource is HarnessSpec
) when {
    resource.status == "Draft"
};

// The correction path back from a failed review — same drafting agent, from UnderReview only.
permit(
    principal is Agent,
    action == Action::"reviseDraft",
    resource is HarnessSpec
) when {
    resource.status == "UnderReview"
};

permit(
    principal is Agent,
    action == Action::"recordFidelityReview",
    resource is HarnessSpec
) when {
    resource.status == "UnderReview"
};

permit(
    principal is Admin,
    action == Action::"publish",
    resource is HarnessSpec
) when {
    resource.status == "UnderReview" &&
    resource.fidelityReviewPassed == true
};

permit(
    principal is Admin,
    action == Action::"revise",
    resource is HarnessSpec
) when {
    resource.status == "Published"
};

permit(
    principal is Admin,
    action == Action::"archive",
    resource is HarnessSpec
);
```

- [ ] **Step 5: Symlink into the local TemperPaw checkout and verify**

```bash
ln -s /Users/georgiospilitsoglou/Developer/projects/zygos/zygos-commons \
      ~/Developer/projects/temperpaw/os-apps/zygos-commons
cd ~/Developer/projects/temperpaw
cargo run
```

In a second terminal:

```bash
curl -s http://localhost:3000/tdata/\$metadata | grep -A2 "EntityType Name=\"HarnessSpec\""
```

Expected: the `HarnessSpec` entity type appears in the served metadata. If Task 1's Step 4 found a
different loading mechanism than a symlink, use that instead and note the deviation in the findings
file.

- [x] **Step 6: Commit**

```bash
cd /Users/georgiospilitsoglou/Developer/projects/zygos
git add zygos-commons/
git commit -m "zygos-commons: HarnessSpec entity, guard, and Cedar policy"
```

---

### Task 3: `synthesize-harness` skill — write DeepSeek Harness through the entity

**Files:**
- Create: `zygos-curation/agents/curator/AGENT.md`
- Create: `zygos-curation/agents/curator/skills/synthesize-harness/SKILL.md`

**Interfaces:**
- Consumes: `HarnessSpec` action names from Task 2 (`SetIdentity`, `WritePhilosophy`, ...,
  `SubmitForReview`) exactly as defined there.
- Produces: one `HarnessSpec` entity in `UnderReview` state, for DeepSeek Harness, consumed by Task 4's
  review skill by its entity `Id`.

- [x] **Step 1: Write the curator agent's top-level instructions**

```markdown
# zygos curator

You research AI agent harnesses and write structured specs through the HarnessSpec entity in Temper —
never by editing markdown directly. `docs/research/SKILL.md` in the zygos repo (read it in full before
starting any skill below) defines what to research and how; skills in this directory define how to
execute that research through `temper.*` calls instead of a text editor.

## Available skills

- `synthesize-harness` — research one target from the target list and write it into a Draft HarnessSpec
- `fidelity-review` — re-check an UnderReview HarnessSpec against its own cited sources, adversarially

## Tools

`temper.create(entity_type, fields)`, `temper.action(entity_type, entity_id, action_name, params)`,
`temper.get(entity_type, entity_id)`, `temper.list(entity_type, filter)` — the Temper OData surface.
`sandbox.bash(cmd)`, `sandbox.write(path, content)`, `sandbox.read(path)` — the sandboxed shell, for
fetching primary sources and eventually writing the published markdown export.
```

- [x] **Step 2: Write the synthesize-harness skill**

```markdown
---
name: synthesize-harness
description: Research one harness from the zygos target list and write it into a Draft HarnessSpec entity
---

# synthesize-harness

Follow `docs/research/SKILL.md` §1–§3 for fetch order and what fills each section well — this skill
does not repeat that guidance, only how to execute it against the entity.

## Steps

1. Branch first, per `docs/research/SKILL.md` §0 — the drafting work below is entity API calls, not git
   commits, but the PR the branch is for opens in step 6 below and must exist before Task 4's review
   starts, per SKILL.md §4 step 1:

```python
sandbox.bash("cd /Users/georgiospilitsoglou/Developer/projects/zygos && git checkout -b research/<target-slug>")
```

2. Read `docs/research/README.md`'s target list (`sandbox.read`), **in full, including the prose below
   the table** — not just the table's `status`/priority columns. A target can carry a load-bearing
   question stated only in that prose (DeepSeek Harness does: "Economics is load-bearing... this spec's
   Economics section either confirms or kills pavlos's R8"). Missing that note because only the table
   was read is exactly the failure mode a literal table-scan risks. Pick the row with `status:
   not-started` and the highest triage priority. Confirm its pinned SHA resolves
   (`sandbox.bash("curl -sI https://raw.githubusercontent.com/<org>/<repo>/<sha>/README.md")`)
   before doing anything else — a relayed SHA with no working coordinate has happened twice in this
   library's history.

3. Create the entity:

```python
spec = temper.create('HarnessSpecs', {'slug': '<target-slug>'})
spec_id = spec['id']
temper.action('HarnessSpecs', spec_id, 'SetIdentity', {
    'title': '<Title>', 'url': '<durable url>', 'artifactUrl': '<pinned tree url>',
    'commit': '<sha>', 'language': '<language>', 'kind': '<AgentHarness|AgentSubstrate|InferenceParadigm>',
    'license': '<license>', 'projectStatus': '<project\'s own stated maturity>',
    'lifecycle': '<Current|VersionChanging|Retired>', 'provenance': 'Primary',
    'verifiedAt': '<today, ISO date>'
})
```

4. Fetch primary sources per `docs/research/SKILL.md` §1 (repo tree via GitHub API, README, deep
   architecture docs, anything the studied repo itself calls a "harness" — read it fully before citing
   it, per §2's name-vs-thing trap). For DeepSeek Harness specifically, read the compaction/caching
   material with the R8 question open per step 2's note — this is the one target on the current list
   where Economics is the point of the pass, not a section filled in afterward.

5. Write each section as its own action call, in the order FORMAT.md §4.1 lists them. `axis` and
   `primitives` are lists (frontmatter is `axis: [A]`, `primitives: [...]`, never a bare string), and
   `WritePrimitivesSection` sets both the body text and the frontmatter slug list in one call:

```python
temper.action('HarnessSpecs', spec_id, 'WritePhilosophy', {'text': '<philosophy prose, with direct quotes>'})
temper.action('HarnessSpecs', spec_id, 'WritePrimitivesSection', {
    'text': '<primitives table as markdown>',
    'primitives': ['<slug-1>', '<slug-2>', '...']
})
temper.action('HarnessSpecs', spec_id, 'WriteLoop', {'text': '<loop prose>'})
temper.action('HarnessSpecs', spec_id, 'WriteBoundaries', {'text': '<boundaries prose + state table>'})
temper.action('HarnessSpecs', spec_id, 'WriteVerification', {'text': '<verification table + gate/report analysis>'})
temper.action('HarnessSpecs', spec_id, 'SetAxis', {'axis': ['<A|B|both|neither>'], 'analysis': '<which-axis prose>'})
temper.action('HarnessSpecs', spec_id, 'WriteEconomics', {'text': '<economics prose>'})
temper.action('HarnessSpecs', spec_id, 'WriteTradeoffs', {'text': '<buys/pays>'})
temper.action('HarnessSpecs', spec_id, 'WriteWhatToSteal', {'text': '<numbered list>'})
temper.action('HarnessSpecs', spec_id, 'WriteWhatNotTo', {'text': '<bulleted list>'})
temper.action('HarnessSpecs', spec_id, 'SetEmbodiment', {'level': 'None', 'text': None})  # or Partial/Full with a trace
temper.action('HarnessSpecs', spec_id, 'WriteLimits', {'text': '<what was not checked>'})
temper.action('HarnessSpecs', spec_id, 'WriteSources', {'text': '<sources table>'})
```

6. Submit for review:

```python
temper.action('HarnessSpecs', spec_id, 'SubmitForReview', {})
```

Expected: succeeds if every `Write*` call above landed; the guard rejects with a clear error naming
which `has_*` flag is still false if any section was skipped. Report the resulting `spec_id` and status
— do not proceed to `fidelity-review` yourself; that is a separate skill run by a separate agent.

7. Open the PR — required before Task 4's review starts, per `docs/research/SKILL.md` §4 step 1 ("Open
   a PR from the research branch. Never merge a research branch without one — the PR body and its
   comments are the audit trail"). There's no markdown file to commit yet (`Publish` in Task 5 generates
   it) — open the PR against the branch as-is, body linking the entity's `spec_id`, so the branch and its
   future commits (Task 5's markdown export) have a home from the start rather than being retrofitted
   into a PR opened after the review already ran:

```python
sandbox.bash("cd /Users/georgiospilitsoglou/Developer/projects/zygos && "
             "git commit --allow-empty -m 'Research: DeepSeek Harness (entity spec_id: <spec_id>)' && "
             "git push -u origin research/<target-slug> && "
             "gh pr create --base main --head research/<target-slug> "
             "--title 'Research: DeepSeek Harness — via the Temper-backed pipeline' "
             "--body 'HarnessSpec entity <spec_id>, UnderReview. See docs/adrs/0002.'")
```
```

- [x] **Step 3: Symlink `zygos-curation` alongside `zygos-commons`**

```bash
ln -s /Users/georgiospilitsoglou/Developer/projects/zygos/zygos-curation \
      ~/Developer/projects/temperpaw/os-apps/zygos-curation
```

Restart the TemperPaw server (`cargo run`) if it doesn't hot-reload the new app automatically —
confirm which is true from Task 1's findings and note it here if it differs.

- [x] **Step 4: Dispatch the skill against DeepSeek Harness**

Run `synthesize-harness` (via whatever dispatch mechanism Task 1 Step 4 confirmed — an agent CLI
command, an MCP call, or a direct API invocation; record the exact command used). Expect a `HarnessSpec`
entity in `UnderReview` state at the end.

- [x] **Step 5: Verify via the OData API**

```bash
curl -s "http://localhost:3000/tdata/HarnessSpecs?\$filter=slug eq 'deepseek-harness'" | python3 -m json.tool
```

Expected: one entity, `status: "UnderReview"`, all `has_*` fields `true`.

- [x] **Step 6: Commit**

```bash
cd /Users/georgiospilitsoglou/Developer/projects/zygos
git add zygos-curation/
git commit -m "zygos-curation: synthesize-harness skill; DeepSeek Harness through to UnderReview"
```

---

### Task 4: `fidelity-review` — automate the adversarial check

**This task is conditional on Task 1 Step 4(d)'s finding — read that before starting.** ADR-0002 lines
72-75 specify this runs "as a Temper job on `UnderReview`, not as a manually-dispatched agent" — an
automatic trigger, the same shape as katagami's own `review-quality` job. Two branches:

- **If Task 1 confirmed an automatic state-entry trigger primitive** (a `reaction` or equivalent):
  build `zygos-commons/reactions/fidelity_review.toml` (or whatever the confirmed primitive's actual
  file shape is — Task 1's findings file has the real answer) bound to `HarnessSpec` entering
  `UnderReview`, and the review logic below runs inside that, not as a dispatched skill.
- **If Task 1 found no such primitive exposed by TemperPaw**, build the skill file below instead —
  but this is then a **confirmed, disclosed deviation from ADR-0002's Decision section**, not Phase 1
  satisfying it. Say so in this task's outcome and again in Task 6's addendum; do not present a
  dispatched skill as equivalent to an automatic job.

The steps below write the skill-file version (the fallback), since it's the only shape that doesn't
depend on Task 1's still-open answer. If Task 1 confirms a reaction primitive exists, port the same
Steps 1-6 logic into that primitive's shape instead — the adversarial-check content doesn't change,
only what triggers it.

**Files:**
- Create: `zygos-curation/agents/curator/skills/fidelity-review/SKILL.md`

**Interfaces:**
- Consumes: `temper.action('HarnessSpecs', id, 'RecordFidelityReview', {passed, findings})` and
  `temper.action('HarnessSpecs', id, 'ReviseDraft', {reason})` from Task 2.
- Produces: a `HarnessSpec` in `UnderReview` with `fidelity_review_passed = true`, or a `HarnessSpec`
  moved back to `Draft` via `ReviseDraft` on a `NEEDS REVISION` verdict, with findings posted as a PR
  comment either way (per `docs/research/SKILL.md` §4 step 3) — not a retry loop in Phase 1; a human (or
  a second `synthesize-harness` pass) does the actual correction, matching how the Temper spec's own
  fidelity review was handled by hand.

- [x] **Step 1: Write the fidelity-review skill**

```markdown
---
name: fidelity-review
description: Adversarially re-check an UnderReview HarnessSpec against its own cited primary sources
---

# fidelity-review

Port of `docs/research/SKILL.md` §4, automated. Read that section in full first — this skill executes
it, not a separate process.

## Steps

1. Fetch the entity: `spec = temper.get('HarnessSpecs', spec_id)`. Read `spec['sources']` for the
   pinned URLs to re-fetch.

2. Re-fetch every source cited in `spec['sources']` independently — do not reuse anything from the
   draft's own working notes.

3. Check three things, adversarially, with intent to refute:
   - Every direct quote in `philosophy`, `loop`, `boundaries`, `verification`, `tradeoffs` resolves
     verbatim (or near-verbatim, unreversed by truncation) against the source it's attributed to.
   - Every non-quoted factual claim is re-checked against the relevant source section — not accepted
     because it sounds plausible or a name implies it.
   - `spec['limits']`'s claims about what wasn't read are spot-checked for accuracy (counts, section
     numbers, scope statements).

4. Record the outcome:

```python
temper.action('HarnessSpecs', spec_id, 'RecordFidelityReview', {
    'passed': True,   # or False
    'findings': '<one finding per line: location, claim as written, what the source says, why it matters>'
})
```

5. Post the findings as a PR comment on the branch's PR (opened in Task 3 step 7), whatever the
   verdict — per `docs/research/SKILL.md` §4 step 3, a clean pass is worth recording as evidence the
   process works, not just a `NEEDS REVISION` verdict:

```python
sandbox.bash(f"cd /Users/georgiospilitsoglou/Developer/projects/zygos && "
             f"gh pr comment research/<target-slug> --body '<findings, verbatim>'")
```

6. If `passed` is `False`, move the entity back to `Draft` — do not call `Publish`:

```python
temper.action('HarnessSpecs', spec_id, 'ReviseDraft', {'reason': '<summary of what needs fixing>'})
```

Report the findings; a human (or a second `synthesize-harness` pass, corrected) fixes the named sections
via their `Write*` action while the entity is back in `Draft`, then calls `SubmitForReview` again and
this skill re-runs.

7. If `passed` is `True`:

```python
temper.action('HarnessSpecs', spec_id, 'Publish', {})
```
```

- [x] **Step 2: Run it against the DeepSeek Harness entity from Task 3**

Expect a real finding or a clean pass — treat either as valid Phase 1 evidence, the same way the Temper
spec's own review found and fixed real defects. Do not treat a clean pass on the first run as more
trustworthy than one that found something; a clean pass with no findings on the very first automated
run is itself worth a second look before trusting the mechanism.

Outcome: **fail** — a real finding. The independent review (agent with no prior view of the draft,
re-fetching all 15 pinned sources at `47f9438`) found F1–F10: one fabricated quote ("the log is the
program" — absent repo-wide), one splice quote ("Inference is cheap here — we are DeepSeek"), a Goal
durability claim contradicted by its own cited source, a self-skip-as-cost-signal claim the source
disclaims, plus misattribution, a wrong count, and imprecise source-table/limits rows. Recorded via
`RecordFidelityReviewFailed`, findings posted to PR #5, entity moved back to `Draft` via `ReviseDraft`.

- [x] **Step 3: Confirm `Publish` succeeded**

```bash
curl -s "http://localhost:3000/tdata/HarnessSpecs?\$filter=slug eq 'deepseek-harness'" | python3 -m json.tool
```

Expected: `status: "Published"`, `fidelityReviewPassed: true`.

**Not run — review verdict was fail, so `Publish` was deliberately not called.** Entity is back in
`Draft` with `fidelity_review_passed: false`. Publish will be confirmed on the re-run after a corrected
second `synthesize-harness` pass fixes F1–F10 and `SubmitForReview` re-triggers this review.

- [x] **Step 4: Commit**

```bash
git add zygos-curation/agents/curator/skills/fidelity-review/
git commit -m "zygos-curation: fidelity-review skill; DeepSeek Harness failed review, back to Draft"
```

The plan's suggested message assumed a pass; the committed message reflects the actual outcome.

---

### Task 5: Publish generates the markdown export

**Files:**
- Create: `zygos-curation/agents/curator/skills/fidelity-review/SKILL.md` — extend Step 7 (above) with
  the export step, added here rather than as a separate skill since export only ever follows a real
  `Publish`
- Modify: `docs/research/README.md` — target-list status row for DeepSeek Harness

**Interfaces:**
- Produces: `docs/research/harnesses/deepseek-harness.md`, byte-shape-compatible with
  `docs/research/_template.md`'s section order and every existing spec's frontmatter shape, committed
  onto the branch and PR already opened in Task 3 step 7 — Task 5 does not open a second PR.

- [x] **Step 1: Extend the fidelity-review skill's Step 7 with the export**

```markdown
8. After `Publish` succeeds, render the markdown export. The mapping is fixed here, not left to
   whoever implements `render_harness_spec_markdown` to infer from property names — property names on
   `HarnessSpec` (Task 2) and the markdown shape they map to are not the same string:

   **Frontmatter, in this exact order** (`docs/research/_template.md` lines 1-17):
   `name` (= `spec['slug']`), `title`, `url`, `artifact_url` (= `artifactUrl`), `commit`, `language`,
   `kind` (enum → kebab-case: `AgentHarness`→`agent-harness`, `AgentSubstrate`→`agent-substrate`,
   `InferenceParadigm`→`inference-paradigm`), `license`, `status` (= `projectStatus`, the project's own
   stated maturity — **not** the `Status` state-machine property, which is always `Published` by the
   time this renders and is not a frontmatter field at all; conflating the two puts the entity's
   workflow state into the public file), `lifecycle` (enum → kebab-case, same rule as `kind`),
   `provenance` (enum → kebab-case), `verified_at` (= `verifiedAt`, ISO date only, not the full
   `DateTimeOffset`), `axis` (list, rendered `[A]` not `A` — same for multi-value), `primitives` (list,
   rendered `[slug-1, slug-2, ...]`), `embodiment` (enum → kebab-case: `None`→`none`, `Partial`→`partial`,
   `Full`→`full`).

   **Body, in this exact heading order and exact heading text** (`docs/research/_template.md` lines
   21-80 — the property name and the heading text differ; use the right column):

   | Property | Heading |
   |---|---|
   | `philosophy` | `## Philosophy` |
   | `primitivesSection` | `## Primitives` |
   | `loop` | `## Loop` |
   | `boundaries` | `## Boundaries` |
   | `verification` | `## Verification strategy` |
   | `whichAxis` | `## Which axis` |
   | `economics` | `## Economics` |
   | `tradeoffs` | `## Tradeoffs` |
   | `whatToSteal` | `## What to steal` |
   | `whatNotTo` | `## What not to` |
   | `embodimentSection` | `## Embodiment` |
   | `limits` | `## Limits of this spec` |
   | `sources` | `## Sources` |

```python
spec = temper.get('HarnessSpecs', spec_id)
markdown = render_harness_spec_markdown(spec)  # implements exactly the two tables above
sandbox.write(f"docs/research/harnesses/{spec['slug']}.md", markdown)
```

9. Commit onto the existing branch — do not open a new branch or a second PR; the one from Task 3
   step 7 already exists and is the audit trail Task 4's findings comment is attached to:

```bash
sandbox.bash("cd /Users/georgiospilitsoglou/Developer/projects/zygos && "
             "git add docs/research/harnesses/deepseek-harness.md docs/research/README.md && "
             "git commit -m 'Research: DeepSeek Harness spec, via Temper-backed pipeline' && "
             "git push")
```

10. Update the target-list row (`docs/research/README.md`) to `status: done` with a link to the new
    file, in the same commit as the markdown export.
```

- [x] **Step 2: Run the full pipeline once more, end to end, from a clean Draft** — done as RLM (PR #6, `caf0bffa` `Published`)

This is the actual proof, not a re-run of Task 4's output: create a fresh entity, run
`synthesize-harness` (branch + PR opened per its step 1 and step 7), then `fidelity-review` including
the export, and confirm the PR now carries both the findings comment and the markdown commit.

- [x] **Step 3: Check the generated file against the two existing specs** — frontmatter order diff vs `temper.md` empty

```bash
cd /Users/georgiospilitsoglou/Developer/projects/zygos
gh pr view research/deepseek-harness  # confirm it already exists, findings comment attached
diff <(head -20 docs/research/harnesses/temper.md) <(head -20 docs/research/harnesses/deepseek-harness.md)
```

The `diff` isn't expected to be empty — different content — but the frontmatter *field order* and
first-heading shape should match. If they don't, the render function has drifted from the two tables in
Step 1; fix it before merging.

- [x] **Step 4: Merge (after review — this is real research content, the fidelity-review gate already
  ran, but a human confirms readability of the actual generated file before it becomes the third public
  spec in the library)**

```bash
gh pr merge --merge --delete-branch
```

- [x] **Step 5: Commit the skill file changes**

```bash
git add zygos-curation/
git commit -m "fidelity-review: publish generates the markdown export"
```

---

### Task 6: Confirm Phase 1's success criterion and record what Phase 1 taught

**Files:**
- Modify: `docs/adrs/0002-temper-backed-curation-pipeline.md` — add a dated addendum, not a rewrite

**Interfaces:** None — this is the closing task, not a new interface.

- [x] **Step 1: Confirm the ADR-0002 success criterion**

Verify: DeepSeek Harness exists as (a) a `Published` `HarnessSpec` entity, queryable via
`/tdata/HarnessSpecs`, and (b) a merged `docs/research/harnesses/deepseek-harness.md`, indistinguishable
in shape from `exo.md` and `temper.md`. Also record explicitly, from Task 4: did fidelity-review run as
an automatic Temper job (satisfying ADR-0002 lines 72-75 as written) or as the dispatched-skill fallback
(a disclosed deviation from it)? This is a pass/fail-relevant fact for the success criterion, not a
footnote — state it plainly in the addendum below either way.

- [x] **Step 2: Write the addendum**

Append to ADR-0002, under a new `## Addendum — Phase 1 result (<date>)` heading: what worked as
designed, what Task 1's investigation found that this plan didn't anticipate, and — explicitly — a
recommendation on whether Phase 2 (target-discovery automation, taxonomy job, or the gallery UI
question named in ADR-0002 as deliberately unresolved) is worth pursuing next, based on what actually
running this taught, not on katagami's shape alone.

- [x] **Step 3: Commit and push**

```bash
git add docs/adrs/0002-temper-backed-curation-pipeline.md
git commit -m "ADR-0002 addendum: Phase 1 result"
git push
```

---

## Self-Review Notes

**Spec coverage against ADR-0002's Phase 1 list:** `zygos-commons` (Task 2) ✓, `zygos-curation` with
`synthesize-harness` (Task 3) and the fidelity-review job (Task 4) ✓, `SubmitForReview` guard (Task 2
Step 3) ✓, `Publish` generating the markdown export (Task 5) ✓. Explicitly deferred items
(target-discovery automation, taxonomy job, gallery UI) have no task here — correct, per ADR-0002.

**Known open risk, named rather than hidden:** Task 1 is genuinely investigative — the exact
skill-dispatch mechanism inside TemperPaw has not been confirmed by primary source before this plan was
written, unlike every other technical claim here (which cite real files fetched from Temper's and
katagami's own repos). Tasks 3–4's skill-file shape follows katagami's own `synthesize-language` and
`review-quality` skills closely, but the *harness* that actually invokes them — a CLI command, an MCP
tool, a webhook — is Task 1's job to pin down before those tasks' dispatch steps can be run as literally
written. If Task 1 finds a different mechanism, the `Step 4`/`Run it` instructions in Tasks 3–4 need a
one-line substitution, not a redesign — the entity, guard, and skill *content* stay valid either way.

**Revision log against the independent adversarial review (2026-08-16), verified before fixing, not
applied blind:**

Fixed, confirmed real by independently re-reading the plan against ADR-0001/ADR-0002/`SKILL.md`/the
template before touching anything:
- **A1/A2** (guard scope narrower than ADR-0002 states) — partially fixed: `has_identity` added and
  gated, but SHA-format and quote-anchor checks are explicitly *not* added to the guard (IOA's evidenced
  guard syntax can't express them without inventing syntax no primary source shows) — routed to Task 4
  instead and disclosed in Global Constraints, not silently dropped.
- **A3** (`axis`/`primitives` scalar vs. array) — fixed: both are now `Collection(Edm.String)`.
- **A4** (`Primitives` frontmatter never settable) — fixed: bundled into `WritePrimitivesSection`.
- **A5** (fidelity-review built as dispatched skill, not the automatic job ADR-0002 specifies) — made
  explicitly conditional on Task 1's finding, with the deviation-if-not-found made loud in both Task 4's
  intro and Task 6's closing check, rather than fixed outright — Task 1 hasn't run yet, so which shape is
  buildable isn't known until it does.
- **A6** (no correction path back to Draft) — fixed: `ReviseDraft` (`UnderReview → Draft`) added to CSDL,
  IOA, and Cedar; wired into the fidelity-review skill's fail branch.
- **A7/A9** (branch/PR timing vs. `SKILL.md` §0/§4) — fixed: branch moves to Task 3 step 1, PR opens at
  Task 3 step 7 (before Task 4's review, findings posted as a PR comment), Task 5 commits onto the
  existing PR instead of opening a second one.
- **B1** (`SetAxis`'s `Analysis` param has nowhere to persist) — fixed: `WhichAxis` property added.
- **B3** (Cedar covers 3 of 19 actions) — fixed: every action now has an explicit rule, following the
  reference app's own convention of naming every action a rule covers rather than a generic bucket that
  doesn't exist in this entity's action set.
- **C1/C2** (render function unspecified; heading-text drift risk) — fixed: Task 5 Step 1 now carries the
  literal frontmatter field list with enum→kebab-case rules and a property→heading-text table, checked
  against the real template headings (`## Verification strategy`, `## Which axis`, `## Limits of this
  spec`), not inferred from CSDL property names.
- **A8** (skill might miss the DeepSeek Harness R8/Economics flag) — fixed: Task 3 step 2 now requires
  reading the target-list prose in full, not just the table, and names the flag explicitly.

Checked and judged likely false positives, not applied — reasoning, not silence:
- **B4** (`resource.status` vs. `Status` casing) — the real Temper reference app's own `order.cedar`
  uses the identical pattern (lowercase Cedar attributes against PascalCase CSDL properties), which reads
  as a standard OData→Cedar serialization convention, not a bug specific to this plan.
- **B5** (`kind = "internal"` actions gated by Cedar) — the real reference app also Cedar-gates its own
  internal actions (`ConfirmOrder`, `ProcessOrder`, `ShipOrder`, all `kind = "internal"`, gated to
  `operations_agent`). "Internal" in Temper's actual model doesn't mean "no authorizable caller"; the
  review's premise here appears to not match the primitive it's checking against.

Not independently re-checked against primary source before this revision (B9, the finer points of A9):
flagged here so a fresh adversarial pass knows what's newly fixed, what was argued down, and what still
just carries the original review's word.

**Round 2 (second independent adversarial pass, same day):** 8 of 10 checks passed clean — the round-1
fixes above held. Two real findings, both confirmed by direct grep before fixing, both textual rather
than structural:

- **SetIdentity hint miscounted its own field list** — said "six-field identity core," the CSDL action
  actually declares eight `Nullable="false"` parameters (Title/Url/ArtifactUrl/Commit/Kind/Lifecycle/
  Provenance/VerifiedAt). Fixed: both hint occurrences now say "eight."
- **`RecordFidelityReview`'s IOA effect dropped its value** — every other `set_bool` effect in the file
  carries a literal `value = true/false`; this one didn't, so the `Passed` parameter had no documented
  way to reach `fidelity_review_passed`, and `Publish`'s guard could never fire. Fixed, but only as far
  as this plan can honestly go without inventing confirmed syntax: named the effect
  `set_bool_from_param` and marked it explicitly unconfirmed against any primitive this plan has
  actually seen (`order.ioa.toml`'s effects are all literal), with a fallback (split into two literal
  actions) if Task 1 finds no parametric effect exists. Added as Task 1 Step 4(e) — the same
  discipline already applied to A5's dispatch-mechanism question, now applied here too.

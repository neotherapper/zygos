# zygos Phase 1: Temper-Backed Curation Pipeline — Implementation Plan

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
reachable from TemperPaw, and how an agent gets access to it.

- [ ] **Step 5: Smoke-test the OData surface**

```bash
curl -s http://localhost:3000/tdata/\$metadata | head -50
```

Expected: an empty or near-empty CSDL document (no apps loaded yet) — confirms the server is actually
serving before Task 2 adds an app to it.

- [ ] **Step 6: Commit the findings file**

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
  `RecordFidelityReview`, `Publish`, `Revise`, `Archive` — consumed by Task 3's skill and Task 4's
  review job by exact action name.

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
        <Property Name="Axis" Type="Edm.String"/>
        <Property Name="Primitives" Type="Edm.String"/>
        <Property Name="Embodiment" Type="Zygos.EmbodimentLevel" DefaultValue="None"/>

        <!-- Body sections (FORMAT.md §4.1 order) -->
        <Property Name="Philosophy" Type="Edm.String"/>
        <Property Name="PrimitivesSection" Type="Edm.String"/>
        <Property Name="Loop" Type="Edm.String"/>
        <Property Name="Boundaries" Type="Edm.String"/>
        <Property Name="Verification" Type="Edm.String"/>
        <Property Name="Economics" Type="Edm.String"/>
        <Property Name="Tradeoffs" Type="Edm.String"/>
        <Property Name="WhatToSteal" Type="Edm.String"/>
        <Property Name="WhatNotTo" Type="Edm.String"/>
        <Property Name="EmbodimentSection" Type="Edm.String"/>
        <Property Name="Limits" Type="Edm.String"/>
        <Property Name="Sources" Type="Edm.String"/>

        <!-- Presence flags — the guard's mechanical checklist, per ADR-0001 -->
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
        <Parameter Name="Title" Type="Edm.String"/>
        <Parameter Name="Url" Type="Edm.String"/>
        <Parameter Name="ArtifactUrl" Type="Edm.String"/>
        <Parameter Name="Commit" Type="Edm.String"/>
        <Parameter Name="Language" Type="Edm.String"/>
        <Parameter Name="Kind" Type="Zygos.HarnessKind"/>
        <Parameter Name="License" Type="Edm.String"/>
        <Parameter Name="ProjectStatus" Type="Edm.String"/>
        <Parameter Name="Lifecycle" Type="Zygos.Lifecycle"/>
        <Parameter Name="Provenance" Type="Zygos.Provenance"/>
        <Parameter Name="VerifiedAt" Type="Edm.DateTimeOffset"/>
        <ReturnType Type="Zygos.HarnessSpec"/>
        <Annotation Term="Temper.Vocab.StateMachine.ValidFromStates">
          <Collection><String>Draft</String></Collection>
        </Annotation>
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

      <!-- WritePrimitivesSection, WriteLoop, WriteBoundaries, WriteVerification,
           WriteEconomics, WriteTradeoffs, WriteWhatToSteal, WriteWhatNotTo, WriteLimits,
           WriteSources: identical shape to WritePhilosophy above, one Text parameter each,
           bound to Draft. Write each one following this exact pattern before Step 2. -->

      <Action Name="SetAxis" IsBound="true">
        <Parameter Name="bindingParameter" Type="Zygos.HarnessSpec"/>
        <Parameter Name="Axis" Type="Edm.String" Nullable="false"/>
        <Parameter Name="Analysis" Type="Edm.String" Nullable="false"/>
        <ReturnType Type="Zygos.HarnessSpec"/>
        <Annotation Term="Temper.Vocab.StateMachine.ValidFromStates">
          <Collection><String>Draft</String></Collection>
        </Annotation>
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

Add `WritePrimitivesSection`, `WriteLoop`, `WriteBoundaries`, `WriteVerification`, `WriteEconomics`,
`WriteTradeoffs`, `WriteWhatToSteal`, `WriteWhatNotTo`, `WriteLimits`, `WriteSources` to the `<Schema
Namespace="Zygos">` block — each identical in shape to `WritePhilosophy`: one `Text` parameter, bound
from `Draft`, returning `Zygos.HarnessSpec`. Ten actions, same three lines each as the template above.

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

# --- The guard that makes ADR-0001's left column real ---

[[action]]
name = "SubmitForReview"
kind = "internal"
from = ["Draft"]
to = "UnderReview"
guard = [
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
hint = "Requires all eleven required sections present. Embodiment is optional per FORMAT.md §4.3 — not gated here."

[[action]]
name = "RecordFidelityReview"
kind = "input"
from = ["UnderReview"]
effect = [{ type = "set_bool", var = "fidelity_review_passed" }]

[[action]]
name = "Publish"
kind = "internal"
from = ["UnderReview"]
to = "Published"
guard = [{ type = "is_true", var = "fidelity_review_passed" }]
hint = "Only publishes once the automated fidelity-review job has recorded a pass."

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

permit(
    principal,
    action == Action::"read",
    resource is HarnessSpec
);

permit(
    principal is Agent,
    action in [Action::"create", Action::"write", Action::"submitForReview"],
    resource is HarnessSpec
) when {
    resource.status == "Draft"
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

- [ ] **Step 6: Commit**

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

- [ ] **Step 1: Write the curator agent's top-level instructions**

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

- [ ] **Step 2: Write the synthesize-harness skill**

```markdown
---
name: synthesize-harness
description: Research one harness from the zygos target list and write it into a Draft HarnessSpec entity
---

# synthesize-harness

Follow `docs/research/SKILL.md` §1–§3 for fetch order and what fills each section well — this skill
does not repeat that guidance, only how to execute it against the entity.

## Steps

1. Read `docs/research/README.md`'s target list (`sandbox.read`). Pick the row with
   `status: not-started` and the highest triage priority. Confirm its pinned SHA resolves
   (`sandbox.bash("curl -sI https://raw.githubusercontent.com/<org>/<repo>/<sha>/README.md")`)
   before doing anything else — a relayed SHA with no working coordinate has happened twice in this
   library's history.

2. Create the entity:

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

3. Fetch primary sources per `docs/research/SKILL.md` §1 (repo tree via GitHub API, README, deep
   architecture docs, anything the studied repo itself calls a "harness" — read it fully before citing
   it, per §2's name-vs-thing trap).

4. Write each section as its own action call, in the order FORMAT.md §4.1 lists them:

```python
temper.action('HarnessSpecs', spec_id, 'WritePhilosophy', {'text': '<philosophy prose, with direct quotes>'})
temper.action('HarnessSpecs', spec_id, 'WritePrimitivesSection', {'text': '<primitives table as markdown>'})
temper.action('HarnessSpecs', spec_id, 'WriteLoop', {'text': '<loop prose>'})
temper.action('HarnessSpecs', spec_id, 'WriteBoundaries', {'text': '<boundaries prose + state table>'})
temper.action('HarnessSpecs', spec_id, 'WriteVerification', {'text': '<verification table + gate/report analysis>'})
temper.action('HarnessSpecs', spec_id, 'SetAxis', {'axis': '<A|B|both|neither>', 'analysis': '<which-axis prose>'})
temper.action('HarnessSpecs', spec_id, 'WriteEconomics', {'text': '<economics prose>'})
temper.action('HarnessSpecs', spec_id, 'WriteTradeoffs', {'text': '<buys/pays>'})
temper.action('HarnessSpecs', spec_id, 'WriteWhatToSteal', {'text': '<numbered list>'})
temper.action('HarnessSpecs', spec_id, 'WriteWhatNotTo', {'text': '<bulleted list>'})
temper.action('HarnessSpecs', spec_id, 'SetEmbodiment', {'level': 'None', 'text': None})  # or Partial/Full with a trace
temper.action('HarnessSpecs', spec_id, 'WriteLimits', {'text': '<what was not checked>'})
temper.action('HarnessSpecs', spec_id, 'WriteSources', {'text': '<sources table>'})
```

5. Submit for review:

```python
temper.action('HarnessSpecs', spec_id, 'SubmitForReview', {})
```

Expected: succeeds if every `Write*` call above landed; the guard rejects with a clear error naming
which `has_*` flag is still false if any section was skipped. Report the resulting `spec_id` and status
— do not proceed to `fidelity-review` yourself; that is a separate skill run by a separate agent.
```

- [ ] **Step 3: Symlink `zygos-curation` alongside `zygos-commons`**

```bash
ln -s /Users/georgiospilitsoglou/Developer/projects/zygos/zygos-curation \
      ~/Developer/projects/temperpaw/os-apps/zygos-curation
```

Restart the TemperPaw server (`cargo run`) if it doesn't hot-reload the new app automatically —
confirm which is true from Task 1's findings and note it here if it differs.

- [ ] **Step 4: Dispatch the skill against DeepSeek Harness**

Run `synthesize-harness` (via whatever dispatch mechanism Task 1 Step 4 confirmed — an agent CLI
command, an MCP call, or a direct API invocation; record the exact command used). Expect a `HarnessSpec`
entity in `UnderReview` state at the end.

- [ ] **Step 5: Verify via the OData API**

```bash
curl -s "http://localhost:3000/tdata/HarnessSpecs?\$filter=slug eq 'deepseek-harness'" | python3 -m json.tool
```

Expected: one entity, `status: "UnderReview"`, all `has_*` fields `true`.

- [ ] **Step 6: Commit**

```bash
cd /Users/georgiospilitsoglou/Developer/projects/zygos
git add zygos-curation/
git commit -m "zygos-curation: synthesize-harness skill; DeepSeek Harness through to UnderReview"
```

---

### Task 4: `fidelity-review` skill — automate the adversarial check

**Files:**
- Create: `zygos-curation/agents/curator/skills/fidelity-review/SKILL.md`

**Interfaces:**
- Consumes: `temper.action('HarnessSpecs', id, 'RecordFidelityReview', {passed, findings})` from
  Task 2.
- Produces: a `HarnessSpec` in `UnderReview` with `fidelity_review_passed = true` (or a documented
  fail, requiring a `Revise` back to Draft — not built as an automated retry loop in Phase 1;
  a human re-runs `synthesize-harness` corrections manually on a `NEEDS REVISION` verdict, matching
  how the Temper spec's own fidelity review was handled).

- [ ] **Step 1: Write the fidelity-review skill**

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

5. If `passed` is `False`, stop — do not call `Publish`. Report the findings; a human (or a second
   `synthesize-harness` pass, corrected) fixes the draft and this skill runs again.

6. If `passed` is `True`:

```python
temper.action('HarnessSpecs', spec_id, 'Publish', {})
```
```

- [ ] **Step 2: Run it against the DeepSeek Harness entity from Task 3**

Expect a real finding or a clean pass — treat either as valid Phase 1 evidence, the same way the Temper
spec's own review found and fixed real defects. Do not treat a clean pass on the first run as more
trustworthy than one that found something; a clean pass with no findings on the very first automated
run is itself worth a second look before trusting the mechanism.

- [ ] **Step 3: Confirm `Publish` succeeded**

```bash
curl -s "http://localhost:3000/tdata/HarnessSpecs?\$filter=slug eq 'deepseek-harness'" | python3 -m json.tool
```

Expected: `status: "Published"`, `fidelityReviewPassed: true`.

- [ ] **Step 4: Commit**

```bash
git add zygos-curation/agents/curator/skills/fidelity-review/
git commit -m "zygos-curation: fidelity-review skill; DeepSeek Harness Published"
```

---

### Task 5: Publish generates the markdown export

**Files:**
- Create: `zygos-curation/agents/curator/skills/fidelity-review/SKILL.md` — extend Step 6 (above) with
  the export step, added here rather than as a separate skill since export only ever follows a real
  `Publish`
- Modify: `docs/research/README.md` — target-list status row for DeepSeek Harness

**Interfaces:**
- Produces: `docs/research/harnesses/deepseek-harness.md`, byte-shape-compatible with
  `docs/research/_template.md`'s section order and every existing spec's frontmatter shape.

- [ ] **Step 1: Extend the fidelity-review skill's Step 6 with the export**

```markdown
7. After `Publish` succeeds, render the markdown export:

```python
spec = temper.get('HarnessSpecs', spec_id)
markdown = render_harness_spec_markdown(spec)  # see below
sandbox.write(f"docs/research/harnesses/{spec['slug']}.md", markdown)
```

Where `render_harness_spec_markdown` produces exactly the shape `docs/research/_template.md` and every
existing spec share: YAML frontmatter (`name`, `title`, `url`, `artifact_url`, `commit`, `language`,
`kind`, `license`, `status`, `lifecycle`, `provenance`, `verified_at`, `axis`, `primitives`,
`embodiment`), then `## Philosophy` through `## Sources` in FORMAT.md §4.1's exact order, each heading
followed by that section's stored text verbatim.

8. Branch, commit, open a PR — the same workflow every prior spec has gone through, not a new one:

```bash
sandbox.bash("cd /Users/georgiospilitsoglou/Developer/projects/zygos && "
             "git checkout -b research/deepseek-harness && "
             "git add docs/research/harnesses/deepseek-harness.md docs/research/README.md && "
             "git commit -m 'Research: DeepSeek Harness spec, via Temper-backed pipeline' && "
             "git push -u origin research/deepseek-harness")
```

9. Update the target-list row (`docs/research/README.md`) to `status: done` with a link to the new
   file, in the same commit as the markdown export.
```

- [ ] **Step 2: Run the full pipeline once more, end to end, from a clean Draft**

This is the actual proof, not a re-run of Task 4's output: create a fresh entity, run
`synthesize-harness`, then `fidelity-review` including the export, and confirm a real PR exists.

- [ ] **Step 3: Open the PR and check it against the two existing specs**

```bash
cd /Users/georgiospilitsoglou/Developer/projects/zygos
gh pr create --base main --head research/deepseek-harness \
  --title "Research: DeepSeek Harness — via the Temper-backed pipeline" \
  --body "First spec through zygos-commons/zygos-curation end to end. See docs/adrs/0002."
diff <(head -20 docs/research/harnesses/temper.md) <(head -20 docs/research/harnesses/deepseek-harness.md)
```

The `diff` isn't expected to be empty — different content — but the frontmatter *field order* and
first-heading shape should match. If they don't, the render function has drifted from the template;
fix it before merging.

- [ ] **Step 4: Merge (after review — this is real research content, the fidelity-review gate already
  ran, but a human confirms readability of the actual generated file before it becomes the third public
  spec in the library)**

```bash
gh pr merge --merge --delete-branch
```

- [ ] **Step 5: Commit the skill file changes**

```bash
git add zygos-curation/
git commit -m "fidelity-review: publish generates the markdown export"
```

---

### Task 6: Confirm Phase 1's success criterion and record what Phase 1 taught

**Files:**
- Modify: `docs/adrs/0002-temper-backed-curation-pipeline.md` — add a dated addendum, not a rewrite

**Interfaces:** None — this is the closing task, not a new interface.

- [ ] **Step 1: Confirm the ADR-0002 success criterion**

Verify: DeepSeek Harness exists as (a) a `Published` `HarnessSpec` entity, queryable via
`/tdata/HarnessSpecs`, and (b) a merged `docs/research/harnesses/deepseek-harness.md`, indistinguishable
in shape from `exo.md` and `temper.md`.

- [ ] **Step 2: Write the addendum**

Append to ADR-0002, under a new `## Addendum — Phase 1 result (<date>)` heading: what worked as
designed, what Task 1's investigation found that this plan didn't anticipate, and — explicitly — a
recommendation on whether Phase 2 (target-discovery automation, taxonomy job, or the gallery UI
question named in ADR-0002 as deliberately unresolved) is worth pursuing next, based on what actually
running this taught, not on katagami's shape alone.

- [ ] **Step 3: Commit and push**

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

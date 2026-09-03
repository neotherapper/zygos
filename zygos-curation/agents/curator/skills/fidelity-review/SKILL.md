---
name: fidelity-review
description: Adversarially re-check an UnderReview HarnessSpec against its own cited primary sources
---

# fidelity-review

Port of `docs/research/SKILL.md` §4, automated. Read that section in full first — this skill executes
it, not a separate process.

The entity lives in `zygos-commons` (app dependency). All bound actions are invoked with the qualified
name `Zygos.<Action>` against the entity's base URL, e.g.
`POST /tdata/HarnessSpecs('<spec_id>')/Zygos.RecordFidelityReview`. The two platform rules from the
Phase 1 findings (temperpaw-findings.md §21) that govern the write-back calls:

- **Param keys must exactly match the CSDL parameter names** (`FidelityFindings`, `Reason`). The
  `RecordFidelityReview` action is split into `RecordFidelityReviewPassed` / `RecordFidelityReviewFailed`
  on the platform (no parametric `set_bool` effect), so dispatch the one matching the verdict — the verdict
  is the action name, `FidelityFindings` is a string with one finding per line, `Reason` is a short string
  (`zygos-commons/specs/model.csdl.xml`, verified live 2026-09-02).
- **Bound actions need a credential-resolved principal, and which key you hold decides what you may do.**
  Send `Authorization: Bearer <key>` plus `X-Tenant-Id: default` and nothing else — the kernel strips every
  `X-Temper-*` header at its edge (Temper ARN-170), so a self-declared principal kind or agent type is
  silently ignored and the call 403s. Three keys, all read from the shell, none in the repo
  (`tools/temper/README.md`): `$ZYGOS_KEY` (operator) for `GET`s; `$ZYGOS_REVIEWER_KEY` for
  `RecordFidelityReviewPassed` / `RecordFidelityReviewFailed` / `ReviseDraft`; `$ZYGOS_PUBLISHER_KEY` for
  `Publish` and `Archive`, held by a person and never by this skill (ADR-0005). In an agent shell, run `echo ${ZYGOS_REVIEWER_KEY:-missing}` — if `missing`, ask
  the human to export it (issued by `tools/temper/bootstrap_credentials.py`); do not invent a key or commit
  one. A 403 on a write is a Cedar denial recorded as a pending decision, not a transient error — report it.

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

4. Record the outcome — dispatch the pass or fail action per the verdict, one finding per line in
   `Findings`:

```bash
# POST /tdata/HarnessSpecs('<spec_id>')/Zygos.RecordFidelityReviewPassed  body: {"FidelityFindings": "reviewer: <tool>, <model>, <session id>\n<one finding per line: location, claim as written, what the source says, why it matters>"} (key: $ZYGOS_REVIEWER_KEY)
# or
# POST /tdata/HarnessSpecs('<spec_id>')/Zygos.RecordFidelityReviewFailed  body: {"FidelityFindings": "<same, one finding per line>"} (key: $ZYGOS_REVIEWER_KEY)
```

5. Post the findings as a PR comment on the branch's PR, whatever the verdict — per
   `docs/research/SKILL.md` §4 step 3, a clean pass is worth recording as evidence the process works,
   not just a `NEEDS REVISION` verdict:

```bash
cd /Users/georgiospilitsoglou/Developer/projects/zygos && \
  gh pr comment research/<target-slug> --body '<findings, verbatim>'
```

6. If the verdict is fail, move the entity back to `Draft` — do not call `Publish`:

```bash
# POST /tdata/HarnessSpecs('<spec_id>')/Zygos.ReviseDraft  body: {"Reason": "<summary of what needs fixing>"} (key: $ZYGOS_REVIEWER_KEY)
```

Report the findings; a human (or a second `synthesize-harness` pass, corrected) fixes the named
sections via their `Write*` action while the entity is back in `Draft`, then calls `SubmitForReview`
again and this skill re-runs.

7. If the verdict is pass, stop. Report the entity id and the findings and say that the entity is
   `UnderReview` with `fidelity_review_passed: true`. Do not call `Publish`. The publisher seat is a
   person holding `$ZYGOS_PUBLISHER_KEY` in their own shell (ADR-0005); if that key is present in
   your environment, report it as a fault in key placement rather than using it.

```bash
# The publisher runs this, by hand, after reading FidelityFindings:
# POST /tdata/HarnessSpecs('<spec_id>')/Zygos.Publish  body {} (key: $ZYGOS_PUBLISHER_KEY)
```

8. After the publisher's `Publish` succeeds, render the markdown export. The mapping is fixed here, not left to
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

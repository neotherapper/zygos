// zygos-commons — HarnessSpec Authorization Policies
//
// Human-in-the-loop model: the curator drafts, the reviewer runs the fidelity
// review, and only an Admin publishes, revises, or archives.
// Action names are the exact IOA action names (PascalCase), matching the
// platform convention; resource attributes use the CSDL property names.

// Any authenticated principal can create, read, and list HarnessSpecs
permit(
    principal,
    action in [Action::"create", Action::"read", Action::"list"],
    resource is HarnessSpec
);

// The curator writes all sections and submits for review, while in Draft
permit(
    principal is Agent,
    action in [
        Action::"SetIdentity",
        Action::"WritePhilosophy",
        Action::"WritePrimitivesSection",
        Action::"WriteLoop",
        Action::"WriteBoundaries",
        Action::"WriteVerification",
        Action::"SetAxis",
        Action::"WriteEconomics",
        Action::"WriteTradeoffs",
        Action::"WriteWhatToSteal",
        Action::"WriteWhatNotTo",
        Action::"SetEmbodiment",
        Action::"WriteLimits",
        Action::"WriteSources",
        Action::"SubmitForReview"
    ],
    resource is HarnessSpec
) when {
    resource.Status == "Draft"
};

// The reviewer (or a system agent) records the fidelity review, while in UnderReview
permit(
    principal is Agent,
    action in [Action::"RecordFidelityReviewPassed", Action::"RecordFidelityReviewFailed"],
    resource is HarnessSpec
) when {
    resource.Status == "UnderReview" &&
    (principal.agent_type == "reviewer" || principal.agent_type == "system")
};

// The reviewer sends a spec back to Draft, while in UnderReview
permit(
    principal is Agent,
    action == Action::"ReviseDraft",
    resource is HarnessSpec
) when {
    resource.Status == "UnderReview" &&
    (principal.agent_type == "reviewer" || principal.agent_type == "system")
};

// Only an Admin publishes. Fidelity enforcement lives in the IOA guard
// (`Publish` requires `is_true fidelity_review_passed`) plus the
// `PublishRequiresFidelityReview` invariant — Cedar sees only entity fields,
// not automaton state booleans, so fidelity cannot be evaluated reliably here
// (platform limitation; see temperpaw-findings.md §19).
permit(
    principal is Admin,
    action == Action::"Publish",
    resource is HarnessSpec
) when {
    resource.Status == "UnderReview"
};

// An Admin can send a published spec back to UnderReview for a new fidelity pass
permit(
    principal is Admin,
    action == Action::"Revise",
    resource is HarnessSpec
) when {
    resource.Status == "Published"
};

// An Admin can archive any spec
permit(
    principal is Admin,
    action == Action::"Archive",
    resource is HarnessSpec
);
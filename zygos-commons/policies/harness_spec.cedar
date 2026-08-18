// zygos-commons — HarnessSpec Authorization Policies
//
// Governs who can read, write, and transition HarnessSpec entities.

// Any authenticated principal can read HarnessSpecs
permit(
    principal,
    action in [Action::"read", Action::"list"],
    resource is HarnessSpec
);

// Only the curator agent can write sections and submit for review
permit(
    principal == Agent::"service:curator",
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
);

// Reviewers (sre, convergence-analyst) can approve, request changes, or retire
permit(
    principal is Agent,
    action in [Action::"Approve", Action::"RequestChanges", Action::"Retire"],
    resource is HarnessSpec
) when {
    principal.agent_type == "reviewer" || principal.agent_type == "system"
};

// System agents can retire specs
permit(
    principal is Agent,
    action == Action::"Retire",
    resource is HarnessSpec
) when {
    principal.agent_type == "system"
};
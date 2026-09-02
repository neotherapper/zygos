// zygos-commons — HarnessSpec Authorization Policies
//
// Credential-bound model (Temper ARN-170 / ADR-0157, zygos ADR-0004): every HTTP
// caller is an Agent principal resolved from an AgentCredential. Authority comes
// from the credential's AgentType name (`principal.agent_type`) — never from a
// header the caller declares. `principal is Admin` is unreachable over HTTP on
// this kernel, so the publish gate is the `publisher` agent type, not Admin.
// `agentTypeVerified` is set only on credential-resolved principals; requiring
// it defeats TemperPaw's header-only loopback branch (unverified principals).
//
// Action names are the exact IOA action names (PascalCase); resource attributes
// use the CSDL property names.

// Any credential-resolved principal can create, read, and list HarnessSpecs
permit(
    principal is Agent,
    action in [Action::"create", Action::"read", Action::"list"],
    resource is HarnessSpec
) when {
    principal has agentTypeVerified && principal.agentTypeVerified == true
};

// The curator (any verified agent credential, including the operator key) writes
// all sections and submits for review, while in Draft
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
    resource.Status == "Draft" &&
    principal has agentTypeVerified && principal.agentTypeVerified == true
};

// The reviewer credential records the fidelity review, while in UnderReview
permit(
    principal is Agent,
    action in [Action::"RecordFidelityReviewPassed", Action::"RecordFidelityReviewFailed"],
    resource is HarnessSpec
) when {
    resource.Status == "UnderReview" &&
    principal has agent_type && principal.agent_type == "reviewer" &&
    principal has agentTypeVerified && principal.agentTypeVerified == true
};

// The reviewer credential sends a spec back to Draft, while in UnderReview
permit(
    principal is Agent,
    action == Action::"ReviseDraft",
    resource is HarnessSpec
) when {
    resource.Status == "UnderReview" &&
    principal has agent_type && principal.agent_type == "reviewer" &&
    principal has agentTypeVerified && principal.agentTypeVerified == true
};

// Only the publisher credential publishes. Fidelity enforcement lives in the IOA
// guard (`Publish` requires `is_true fidelity_review_passed`) plus the
// `PublishRequiresFidelityReview` invariant — Cedar sees only entity fields.
permit(
    principal is Agent,
    action == Action::"Publish",
    resource is HarnessSpec
) when {
    resource.Status == "UnderReview" &&
    principal has agent_type && principal.agent_type == "publisher" &&
    principal has agentTypeVerified && principal.agentTypeVerified == true
};

// The publisher credential can send a published spec back to UnderReview
permit(
    principal is Agent,
    action == Action::"Revise",
    resource is HarnessSpec
) when {
    resource.Status == "Published" &&
    principal has agent_type && principal.agent_type == "publisher" &&
    principal has agentTypeVerified && principal.agentTypeVerified == true
};

// The publisher credential can archive any spec
permit(
    principal is Agent,
    action == Action::"Archive",
    resource is HarnessSpec
) when {
    principal has agent_type && principal.agent_type == "publisher" &&
    principal has agentTypeVerified && principal.agentTypeVerified == true
};

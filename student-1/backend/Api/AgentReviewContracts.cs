namespace Accommodation.Backend.Api;

// Shapes shared with the Multi-Agent Server (see ai-services/multi-agent-server/README.md).
// Stage metadata supports cloud evidence checks; raw model output is not mapped.

public sealed record EvidenceEntry(string Id, string Title, string Text);

public sealed record WorkflowStarted(string? Id, string? Status);

public sealed record WorkflowSummary(
    string? Id,
    string? Feature,
    string? Task,
    string? Status,
    string? CreatedAt,
    string? UpdatedAt);

public sealed record WorkflowRecord(
    string? Id,
    string? Feature,
    string? Task,
    string? Status,
    string? CreatedAt,
    string? UpdatedAt,
    IReadOnlyList<EvidenceEntry>? Evidence,
    WorkflowPlan? Plan,
    WorkerOutput? Work,
    WorkflowReview? Review,
    HumanDecision? HumanDecision,
    WorkerOutput? FinalOutput,
    WorkflowError? Error,
    IReadOnlyList<WorkflowStage>? History = null);

public sealed record WorkflowStage(string? Stage, bool? Ok);

public sealed record WorkflowPlan(
    string Objective,
    IReadOnlyList<PlanStep> Steps,
    IReadOnlyList<string> RequiredEvidenceIds,
    IReadOnlyList<string> SuccessCriteria);

public sealed record PlanStep(string Id, string Description);

public sealed record WorkerOutput(string Summary, IReadOnlyList<WorkItem> Items);

public sealed record WorkItem(string Id, string Subject, string Detail, IReadOnlyList<string> EvidenceIds);

public sealed record WorkflowReview(
    string Verdict,
    string ModelVerdict,
    bool Degraded,
    IReadOnlyList<ReviewFinding> Findings,
    IReadOnlyList<string> Recommendations);

public sealed record ReviewFinding(string Severity, string? ItemId, string Message);

public sealed record HumanDecision(
    string Decision,
    string Notes,
    string DecidedBy,
    string DecidedAt,
    IReadOnlyList<string>? AcceptedItemIds);

public sealed record WorkflowError(string Code, string Message, string? Stage);

public sealed record ReviewDecisionRequest(
    string? Decision,
    string? Notes,
    WorkerOutput? CorrectedOutput,
    IReadOnlyList<string>? AcceptedItemIds);

using System.Globalization;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;
using BudgetTracker.Backend.Clients;
using BudgetTracker.Backend.Services;
using Microsoft.AspNetCore.DataProtection;

namespace BudgetTracker.Backend.Api;

public static class WhatIfEndpoints
{
    internal const long MaxSafeAmount = 9_007_199_254_740_991;
    internal static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        PropertyNameCaseInsensitive = false,
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        MaxDepth = 32
    };

    public static void MapWhatIfEndpoints(this WebApplication app)
    {
        app.MapPost("/api/what-if/preview", async (HttpContext context, IDatabaseApiClient database, IExchangeRateProvider rates, CancellationToken cancellationToken) =>
        {
            var request = await ReadProposalAsync(context.Request, false, cancellationToken);
            return Results.Ok(await PreviewAsync(request, database, rates, cancellationToken));
        });
        app.MapPost("/api/what-if/workflows", StartAsync);
        app.MapGet("/api/what-if/workflows/{id}", PollAsync);
        app.MapPost("/api/what-if/workflows/{id}/decision", DecideAsync);
    }

    private static async Task<IResult> StartAsync(HttpContext context, FeatureModeSettings modes, IDatabaseApiClient database, IExchangeRateProvider rates, MultiAgentClient multiAgent, IDataProtectionProvider protection, CancellationToken cancellationToken)
    {
        EnsureEnabled(modes);
        var request = await ReadProposalAsync(context.Request, true, cancellationToken);
        var preview = await PreviewAsync(request, database, rates, cancellationToken);
        if (request.SnapshotHash != preview.SnapshotHash) throw Stale();
        var evidence = Evidence(preview);
        var id = await multiAgent.StartAsync(evidence, cancellationToken);
        var binding = new WhatIfBinding(id, MultiAgentClient.Feature, preview.Original.JourneyLabel, preview.SnapshotHash, EvidenceDigest(evidence));
        var token = Protector(protection).Protect(JsonSerializer.Serialize(binding, JsonOptions), TimeSpan.FromHours(2));
        try
        {
            var workflow = await multiAgent.GetAsync(id, cancellationToken);
            var bound = BoundPreview(workflow, binding);
            return Results.Json(new { id, status = workflow.GetProperty("status").GetString(), token, preview = bound, workflow }, statusCode: 202);
        }
        catch (WhatIfFailure exception)
        {
            throw new WhatIfFailure(exception.StatusCode, exception.Code, exception.Message + " Start was accepted. Poll this ID with this token; do not start again.", new { id, token });
        }
    }

    private static async Task<IResult> PollAsync(string id, HttpContext context, FeatureModeSettings modes, MultiAgentClient multiAgent, IDataProtectionProvider protection, CancellationToken cancellationToken)
    {
        EnsureEnabled(modes);
        var binding = ReadBinding(id, context.Request, protection);
        if (context.Request.ContentLength is > 0 || context.Request.Headers.ContainsKey("Transfer-Encoding")) throw InvalidRequest();
        var workflow = await multiAgent.GetAsync(id, cancellationToken);
        return Envelope(id, workflow, BoundPreview(workflow, binding));
    }

    private static async Task<IResult> DecideAsync(string id, HttpContext context, FeatureModeSettings modes, IDatabaseApiClient database, IExchangeRateProvider rates, MultiAgentClient multiAgent, IDataProtectionProvider protection, CancellationToken cancellationToken)
    {
        EnsureEnabled(modes);
        var binding = ReadBinding(id, context.Request, protection);
        var body = await ReadBodyAsync(context.Request, cancellationToken);
        if (body.ValueKind != JsonValueKind.Object || !new[] { "decision", "notes", "decidedBy" }.All(name => body.TryGetProperty(name, out _)) ||
            body.EnumerateObject().Any(property => !new[] { "decision", "notes", "decidedBy", "acceptedItemIds", "correctedOutput" }.Contains(property.Name))) throw InvalidDecision();
        WhatIfDecision decision;
        try { decision = body.Deserialize<WhatIfDecision>(JsonOptions) ?? throw InvalidDecision(); }
        catch (JsonException) { throw InvalidDecision(); }
        if (decision.Decision is null || MultiAgentClient.DecisionStatus(decision.Decision) is null || !MultiAgentClient.ValidHumanName(decision.DecidedBy) ||
            decision.Notes is null || decision.Notes.Length > 1000 || decision.Notes.Any(character => char.IsControl(character) && character is not ('\r' or '\n' or '\t')) ||
            decision.Decision == "reject" && string.IsNullOrWhiteSpace(decision.Notes)) throw InvalidDecision();
        if (decision.Decision == "partial")
        {
            if (decision.CorrectedOutput is not null || decision.AcceptedItemIds is null || decision.AcceptedItemIds.Count is < 1 or > 8 ||
                decision.AcceptedItemIds.Any(value => value is null || !System.Text.RegularExpressions.Regex.IsMatch(value, "\\Ai[0-9]{1,2}\\z")) ||
                decision.AcceptedItemIds.Distinct(StringComparer.Ordinal).Count() != decision.AcceptedItemIds.Count) throw InvalidDecision();
        }
        else if (decision.AcceptedItemIds is not null || (decision.Decision == "correct" ? decision.CorrectedOutput is null : decision.CorrectedOutput is not null)) throw InvalidDecision();
        decision = decision with { DecidedBy = decision.DecidedBy!.Trim() };
        var current = await multiAgent.GetAsync(id, cancellationToken);
        var preview = BoundPreview(current, binding);
        if (current.GetProperty("status").GetString() != "awaiting_human_review") throw new WhatIfFailure(409, "not_awaiting_review", "The workflow is not awaiting human review. Poll its current state.");
        var evidence = MultiAgentClient.ReadEvidence(current.GetProperty("evidence"));
        if (decision.Decision == "correct" && !MultiAgentClient.ValidWork(decision.CorrectedOutput!.Value, evidence)) throw InvalidDecision();
        if (decision.Decision == "partial")
        {
            var known = current.GetProperty("work").GetProperty("items").EnumerateArray().Select(value => value.GetProperty("id").GetString()).ToArray();
            if (decision.AcceptedItemIds!.Any(value => !known.Contains(value))) throw InvalidDecision();
        }
        WhatIfPreview fresh;
        try { fresh = await PreviewAsync(new(binding.Journey, preview.Proposed.Categories.Select(value => new WhatIfLimit(value.Category, value.PlannedAmountMinor)).ToArray()), database, rates, cancellationToken); }
        catch (WhatIfFailure exception) when (exception.StatusCode is 400 or 404) { throw Stale(); }
        if (fresh.SnapshotHash != binding.SnapshotHash) throw Stale();
        var workflow = await multiAgent.DecideAsync(id, new { decision = decision.Decision, notes = decision.Notes, decided_by = decision.DecidedBy, accepted_item_ids = decision.AcceptedItemIds, corrected_output = decision.CorrectedOutput }, cancellationToken);
        var bound = BoundPreview(workflow, binding);
        var human = workflow.GetProperty("human_decision");
        MultiAgentClient.Require(workflow.GetProperty("status").GetString() == MultiAgentClient.DecisionStatus(decision.Decision) &&
            human.GetProperty("decision").GetString() == decision.Decision && human.GetProperty("notes").GetString() == decision.Notes && human.GetProperty("decided_by").GetString() == decision.DecidedBy);
        foreach (var field in new[] { "plan", "work", "review", "created_at" }) MultiAgentClient.Require(MultiAgentClient.Equivalent(current.GetProperty(field), workflow.GetProperty(field)));
        if (decision.Decision == "partial") MultiAgentClient.Require(human.GetProperty("accepted_item_ids").EnumerateArray().Select(value => value.GetString()).SequenceEqual(decision.AcceptedItemIds!));
        if (decision.Decision == "correct") MultiAgentClient.Require(MultiAgentClient.Equivalent(workflow.GetProperty("final_output"), decision.CorrectedOutput!.Value));
        return Envelope(id, workflow, bound);
    }

    private static IResult Envelope(string id, JsonElement workflow, WhatIfPreview preview) => Results.Ok(new { id, status = workflow.GetProperty("status").GetString(), preview, workflow });
    private static void EnsureEnabled(FeatureModeSettings modes) { if (!modes.MultiAgentEnabled) throw new WhatIfFailure(503, "feature_disabled", "What-If workflows are disabled. The deterministic preview remains available."); }
    private static WhatIfFailure Stale() => new(409, "snapshot_stale", "The financial snapshot changed. Request a fresh preview and start a new workflow; no financial changes were saved.");
    private static WhatIfFailure InvalidDecision() => new(400, "validation_error", "Supply a valid explicit human decision, name (1 to 60 characters), notes (up to 1000), and decision-specific commentary or item IDs. Rejection requires notes.");
    private static ITimeLimitedDataProtector Protector(IDataProtectionProvider provider) => provider.CreateProtector("student-4.what-if.binding.v1").ToTimeLimitedDataProtector();

    private static WhatIfBinding ReadBinding(string id, HttpRequest request, IDataProtectionProvider protection)
    {
        if (!MultiAgentClient.ValidId(id)) throw InvalidRequest();
        var tokens = request.Headers["X-WhatIf-Token"];
        if (tokens.Count != 1 || tokens[0] is not { Length: > 0 and <= 4096 }) throw InvalidToken();
        try
        {
            var binding = JsonSerializer.Deserialize<WhatIfBinding>(Protector(protection).Unprotect(tokens[0]!), JsonOptions);
            if (binding is null || binding.Id != id || binding.Feature != MultiAgentClient.Feature || !ValidText(binding.Journey, 80) || !ValidHash(binding.SnapshotHash) || !ValidHash(binding.EvidenceDigest)) throw InvalidToken();
            return binding;
        }
        catch (CryptographicException) { throw InvalidToken(); }
        catch (JsonException) { throw InvalidToken(); }
    }

    private static WhatIfFailure InvalidToken() => new(403, "invalid_workflow_token", "The workflow token is missing, tampered, expired or belongs to a different workflow. Tokens expire after two hours or a backend restart.");
    private static string EvidenceDigest(IReadOnlyList<WhatIfEvidence> evidence) => Hash(JsonSerializer.Serialize(evidence.OrderBy(value => value.Id, StringComparer.Ordinal), JsonOptions));

    private static WhatIfEvidence[] Evidence(WhatIfPreview preview)
    {
        var snapshot = new WhatIfSnapshot(preview.Original.BaseCurrency, Totals(preview.Original), Totals(preview.Proposed), preview.SnapshotHash);
        var evidence = new List<WhatIfEvidence> { new("snapshot", "Journey budget snapshot", JsonSerializer.Serialize(snapshot, JsonOptions)) };
        foreach (var original in preview.Original.Categories)
        {
            var proposed = preview.Proposed.Categories.Single(value => value.Category == original.Category);
            var display = $"{preview.Original.BaseCurrency} limits {Major(original.PlannedAmountMinor)} -> {Major(proposed.PlannedAmountMinor)}; actual {Major(proposed.ActualAmountMinor)}; proposed remaining {Major(proposed.RemainingAmountMinor)}";
            evidence.Add(new("category:" + original.Category, "Category: " + original.Category, JsonSerializer.Serialize(new WhatIfCategory(original, proposed, proposed.PlannedAmountMinor < proposed.ActualAmountMinor, display), JsonOptions)));
        }
        if (evidence.Any(value => value.Text.Length > 800)) throw MultiAgentClient.InvalidResponse();
        return evidence.ToArray();
    }

    private static WhatIfPreview BoundPreview(JsonElement workflow, WhatIfBinding binding)
    {
        try
        {
            var evidence = MultiAgentClient.ReadEvidence(workflow.GetProperty("evidence"));
            MultiAgentClient.Require(EvidenceDigest(evidence) == binding.EvidenceDigest);
            var snapshot = JsonSerializer.Deserialize<WhatIfSnapshot>(evidence.Single(value => value.Id == "snapshot").Text, JsonOptions)!;
            MultiAgentClient.Require(snapshot is not null && snapshot.SnapshotHash == binding.SnapshotHash);
            var categories = evidence.Where(value => value.Id != "snapshot").Select(value => JsonSerializer.Deserialize<WhatIfCategory>(value.Text, JsonOptions)!).OrderBy(value => value.Original.Category, StringComparer.Ordinal).ToArray();
            var original = Dashboard(binding.Journey, snapshot!, snapshot!.Original, categories.Select(value => value.Original).ToArray());
            var proposed = Dashboard(binding.Journey, snapshot, snapshot.Proposed, categories.Select(value => value.Proposed).ToArray());
            var calculatedOriginal = DashboardCalculator.CalculateWhatIf(original, original.Categories.Select(value => new WhatIfLimit(value.Category, value.PlannedAmountMinor)).ToArray());
            var calculatedProposed = DashboardCalculator.CalculateWhatIf(original, proposed.Categories.Select(value => new WhatIfLimit(value.Category, value.PlannedAmountMinor)).ToArray());
            MultiAgentClient.Require(MultiAgentClient.Equivalent(JsonSerializer.SerializeToElement(original, JsonOptions), JsonSerializer.SerializeToElement(calculatedOriginal, JsonOptions)) &&
                MultiAgentClient.Equivalent(JsonSerializer.SerializeToElement(proposed, JsonOptions), JsonSerializer.SerializeToElement(calculatedProposed, JsonOptions)));
            var preview = new WhatIfPreview(original, proposed, Hash(JsonSerializer.Serialize(new { original, proposed }, JsonOptions)));
            MultiAgentClient.Require(preview.SnapshotHash == binding.SnapshotHash && EvidenceDigest(Evidence(preview)) == binding.EvidenceDigest);
            return preview;
        }
        catch (Exception exception) when (exception is JsonException or InvalidOperationException or ArgumentException or DashboardDataException or OverflowException or NullReferenceException)
        {
            throw MultiAgentClient.InvalidResponse();
        }
    }

    private static WhatIfTotals Totals(DashboardResponse value) => new(value.PlannedAmountMinor, value.ActualAmountMinor, value.RemainingAmountMinor, value.PercentageUsed);
    private static string Major(long minor) => (minor / 100m).ToString("F2", CultureInfo.InvariantCulture);
    private static DashboardResponse Dashboard(string journey, WhatIfSnapshot snapshot, WhatIfTotals totals, IReadOnlyList<CategoryDashboardResponse> categories) => new(journey, snapshot.BaseCurrency, totals.PlannedAmountMinor, totals.ActualAmountMinor, totals.RemainingAmountMinor, totals.PercentageUsed, categories);
    private sealed record WhatIfBinding(string Id, string Feature, string Journey, string SnapshotHash, string EvidenceDigest);
    private sealed record WhatIfTotals(long PlannedAmountMinor, long ActualAmountMinor, long RemainingAmountMinor, decimal PercentageUsed);
    private sealed record WhatIfSnapshot(string BaseCurrency, WhatIfTotals Original, WhatIfTotals Proposed, string SnapshotHash);
    private sealed record WhatIfCategory(CategoryDashboardResponse Original, CategoryDashboardResponse Proposed, bool BelowSpent, string Display);
    private sealed record WhatIfDecision(string? Decision, string? Notes, string? DecidedBy, IReadOnlyList<string>? AcceptedItemIds = null, JsonElement? CorrectedOutput = null);

    internal static async Task<WhatIfProposal> ReadProposalAsync(HttpRequest request, bool starting, CancellationToken cancellationToken)
    {
        var body = await ReadBodyAsync(request, cancellationToken);
        if (!HasProperties(body, starting ? ["journeyLabel", "limits", "snapshotHash"] : ["journeyLabel", "limits"])) throw InvalidRequest();
        WhatIfProposal proposal;
        try { proposal = body.Deserialize<WhatIfProposal>(JsonOptions) ?? throw InvalidRequest(); }
        catch (JsonException) { throw InvalidRequest(); }
        var label = proposal.JourneyLabel?.Trim();
        if (!ValidText(label, 80) || proposal.Limits is null || proposal.Limits.Count is < 1 or > 6) throw InvalidRequest();
        var categories = new HashSet<string>(StringComparer.Ordinal);
        long total = 0;
        foreach (var limit in proposal.Limits)
        {
            var category = limit?.Category?.Trim().ToLowerInvariant();
            if (category is null || !Validation.Categories.Contains(category) || !categories.Add(category) ||
                limit!.LimitAmountMinor is <= 0 or > MaxSafeAmount || limit.LimitAmountMinor > MaxSafeAmount - total) throw InvalidRequest();
            total += limit.LimitAmountMinor;
        }
        if (starting && !ValidHash(proposal.SnapshotHash)) throw InvalidRequest();
        return proposal with { JourneyLabel = label, Limits = proposal.Limits.Select(value => value with { Category = value.Category!.Trim().ToLowerInvariant() }).OrderBy(value => value.Category, StringComparer.Ordinal).ToArray() };
    }

    internal static async Task<WhatIfPreview> PreviewAsync(WhatIfProposal request, IDatabaseApiClient database, IExchangeRateProvider rates, CancellationToken cancellationToken)
    {
        var budgets = await database.ListBudgetsAsync(request.JourneyLabel, null, cancellationToken);
        if (budgets.Count == 0) throw new WhatIfFailure(404, "journey_not_found", "The journey was not found.");
        if (budgets.Any(value => value is null || value.Id <= 0 || !string.Equals(value.JourneyLabel, request.JourneyLabel, StringComparison.OrdinalIgnoreCase) ||
            value.Category is null || !Validation.Categories.Contains(value.Category.Trim().ToLowerInvariant()) ||
            value.LimitAmountMinor is <= 0 or > MaxSafeAmount || !rates.Supports(value.BaseCurrency)) || budgets.Select(value => value.Id).Distinct().Count() != budgets.Count) throw new DashboardDataException();
        var expenses = await database.ListExpensesAsync(null, request.JourneyLabel, null, cancellationToken);
        if (expenses.Any(value => value is null || value.ConvertedAmountMinor is < 0 or > MaxSafeAmount) || expenses.Select(value => value.Id).Distinct().Count() != expenses.Count) throw new DashboardDataException();
        try
        {
            var normalized = budgets.Select(value => value with { Category = value.Category.Trim().ToLowerInvariant() }).ToArray();
            var original = DashboardCalculator.Calculate(budgets[0].JourneyLabel, normalized, expenses);
            var proposed = DashboardCalculator.CalculateWhatIf(original, request.Limits!);
            return new(original, proposed, Hash(JsonSerializer.Serialize(new { original, proposed }, JsonOptions)));
        }
        catch (OverflowException) { throw new DashboardDataException(); }
        catch (ArgumentException) { throw InvalidRequest(); }
    }

    internal static async Task<JsonElement> ReadBodyAsync(HttpRequest request, CancellationToken cancellationToken)
    {
        const int maximum = 16 * 1024;
        if (request.ContentLength > maximum) throw InvalidRequest();
        using var stream = new MemoryStream();
        var buffer = new byte[4096];
        while (true)
        {
            var count = await request.Body.ReadAsync(buffer.AsMemory(0, Math.Min(buffer.Length, maximum + 1 - (int)stream.Length)), cancellationToken);
            if (count == 0) break;
            stream.Write(buffer, 0, count);
            if (stream.Length > maximum) throw InvalidRequest();
        }
        try
        {
            using var document = JsonDocument.Parse(stream.ToArray(), new JsonDocumentOptions { MaxDepth = 32 });
            if (!UniqueProperties(document.RootElement)) throw InvalidRequest();
            return document.RootElement.Clone();
        }
        catch (JsonException) { throw InvalidRequest(); }
    }

    internal static bool UniqueProperties(JsonElement value) => value.ValueKind switch
    {
        JsonValueKind.Object => value.EnumerateObject().Select(property => property.Name).Distinct(StringComparer.Ordinal).Count() == value.EnumerateObject().Count() && value.EnumerateObject().All(property => UniqueProperties(property.Value)),
        JsonValueKind.Array => value.EnumerateArray().All(UniqueProperties),
        _ => true
    };

    internal static bool HasProperties(JsonElement value, params string[] properties) => value.ValueKind == JsonValueKind.Object &&
        value.EnumerateObject().Select(property => property.Name).Order(StringComparer.Ordinal).SequenceEqual(properties.Order(StringComparer.Ordinal));
    internal static bool ValidText(string? value, int maximum) => !string.IsNullOrWhiteSpace(value) && value.Length <= maximum && !value.Any(char.IsControl);
    internal static bool ValidNarrative(string? value, int maximum) => !string.IsNullOrWhiteSpace(value) && value.Length <= maximum && !value.Any(character => char.IsControl(character) && character is not ('\r' or '\n' or '\t'));
    internal static bool ValidHash(string? value) => value is { Length: 64 } && value.All(character => character is >= '0' and <= '9' or >= 'a' and <= 'f');
    internal static string Hash(string value) => Convert.ToHexString(SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(value))).ToLowerInvariant();
    internal static WhatIfFailure InvalidRequest() => new(400, "validation_error", "The What-If request is invalid. Supply a journey and the complete existing category limits.");
}

public sealed record WhatIfProposal(string? JourneyLabel, IReadOnlyList<WhatIfLimit>? Limits, string? SnapshotHash = null);
public sealed record WhatIfPreview(DashboardResponse Original, DashboardResponse Proposed, string SnapshotHash);
public sealed class WhatIfFailure(int statusCode, string code, string message, object? fields = null) : Exception(message)
{
    public int StatusCode { get; } = statusCode;
    public string Code { get; } = code;
    public object? Fields { get; } = fields;
}
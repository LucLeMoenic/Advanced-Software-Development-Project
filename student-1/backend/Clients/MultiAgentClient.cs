using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using Accommodation.Backend.Api;

namespace Accommodation.Backend.Clients;

public interface IMultiAgentClient
{
    Task<WorkflowStarted> StartAsync(
        IReadOnlyList<EvidenceEntry> evidence,
        string task,
        CancellationToken cancellationToken);

    Task<IReadOnlyList<WorkflowSummary>> ListAsync(CancellationToken cancellationToken);

    Task<WorkflowRecord> GetAsync(string workflowId, CancellationToken cancellationToken);

    Task<WorkflowRecord> DecideAsync(
        string workflowId,
        ReviewDecisionRequest decision,
        CancellationToken cancellationToken);
}

/// <summary>
/// Calls the shared native Multi-Agent Server. Only Student 1 workflows are returned:
/// records for any other feature are treated as not found.
/// </summary>
public sealed partial class MultiAgentClient(HttpClient client) : IMultiAgentClient
{
    public const string Feature = "student-1";

    // The server's wire format is snake_case; public DTOs are written camelCase by ASP.NET Core.
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
    };

    private static readonly HashSet<string> Statuses =
    [
        "queued", "planning", "working", "reviewing", "awaiting_human_review",
        "approved", "corrected", "partially_accepted", "rejected", "failed"
    ];

    public static bool IsWorkflowId(string value) => WorkflowIdPattern().IsMatch(value);

    public async Task<WorkflowStarted> StartAsync(
        IReadOnlyList<EvidenceEntry> evidence,
        string task,
        CancellationToken cancellationToken)
    {
        var started = await SendAsync<WorkflowStarted>(
            HttpMethod.Post,
            "/workflows",
            new { feature = Feature, task, evidence, submitted_by = "student-1-frontend" },
            HttpStatusCode.Accepted,
            cancellationToken);
        if (started.Id is null || !IsWorkflowId(started.Id) || started.Status is null)
        {
            throw new MultiAgentException(MultiAgentFailure.InvalidResponse);
        }

        return started;
    }

    public async Task<IReadOnlyList<WorkflowSummary>> ListAsync(CancellationToken cancellationToken)
    {
        var summaries = await SendAsync<WorkflowSummary[]>(
            HttpMethod.Get,
            "/workflows",
            null,
            HttpStatusCode.OK,
            cancellationToken);
        if (summaries.Any(summary => summary?.Id is null || summary.Feature is null
                || summary.Task is null || summary.Status is null))
        {
            throw new MultiAgentException(MultiAgentFailure.InvalidResponse);
        }

        return summaries.Where(summary => summary.Feature == Feature).ToArray();
    }

    public async Task<WorkflowRecord> GetAsync(string workflowId, CancellationToken cancellationToken)
    {
        var record = await SendAsync<WorkflowRecord>(
            HttpMethod.Get,
            $"/workflows/{workflowId}",
            null,
            HttpStatusCode.OK,
            cancellationToken);
        return OwnRecord(record, workflowId);
    }

    public async Task<WorkflowRecord> DecideAsync(
        string workflowId,
        ReviewDecisionRequest decision,
        CancellationToken cancellationToken)
    {
        // Confirm ownership first so a Student 1 route cannot decide another feature's workflow.
        await GetAsync(workflowId, cancellationToken);
        var record = await SendAsync<WorkflowRecord>(
            HttpMethod.Post,
            $"/workflows/{workflowId}/decision",
            new
            {
                decision = decision.Decision,
                notes = decision.Notes ?? string.Empty,
                decided_by = "traveller",
                corrected_output = decision.CorrectedOutput,
                accepted_item_ids = decision.AcceptedItemIds
            },
            HttpStatusCode.OK,
            cancellationToken);
        return OwnRecord(record, workflowId);
    }

    private static WorkflowRecord OwnRecord(WorkflowRecord record, string workflowId)
    {
        if (record.Id != workflowId || record.Task is null || record.Status is null
            || !Statuses.Contains(record.Status) || record.Evidence is null)
        {
            throw new MultiAgentException(MultiAgentFailure.InvalidResponse);
        }

        return record.Feature == Feature
            ? record
            : throw new MultiAgentException(MultiAgentFailure.NotFound);
    }

    private async Task<T> SendAsync<T>(
        HttpMethod method,
        string path,
        object? body,
        HttpStatusCode expectedStatus,
        CancellationToken cancellationToken)
    {
        using var request = new HttpRequestMessage(method, path)
        {
            Content = body is null ? null : JsonContent.Create(body, options: JsonOptions)
        };

        HttpResponseMessage response;
        try
        {
            response = await client.SendAsync(request, cancellationToken);
        }
        catch (TaskCanceledException exception) when (!cancellationToken.IsCancellationRequested)
        {
            throw new MultiAgentException(MultiAgentFailure.Unavailable, inner: exception);
        }
        catch (HttpRequestException exception)
        {
            throw new MultiAgentException(MultiAgentFailure.Unavailable, inner: exception);
        }

        using (response)
        {
            if (response.StatusCode != expectedStatus)
            {
                throw await ToFailureAsync(response, cancellationToken);
            }

            try
            {
                return await response.Content.ReadFromJsonAsync<T>(JsonOptions, cancellationToken)
                    ?? throw new MultiAgentException(MultiAgentFailure.InvalidResponse);
            }
            catch (JsonException exception)
            {
                throw new MultiAgentException(MultiAgentFailure.InvalidResponse, inner: exception);
            }
        }
    }

    private static async Task<MultiAgentException> ToFailureAsync(
        HttpResponseMessage response,
        CancellationToken cancellationToken)
    {
        var status = (int)response.StatusCode;
        if (response.StatusCode == HttpStatusCode.NotFound)
        {
            return new MultiAgentException(MultiAgentFailure.NotFound);
        }

        ServerErrorEnvelope? envelope = null;
        try
        {
            envelope = await response.Content.ReadFromJsonAsync<ServerErrorEnvelope>(JsonOptions, cancellationToken);
        }
        catch (JsonException)
        {
            // Treated below as an unusable or unavailable response.
        }

        var code = envelope?.Error?.Code;
        var message = envelope?.Error?.Message;
        if (status == 503 && code == "busy")
        {
            return new MultiAgentException(MultiAgentFailure.Busy);
        }

        if (status is 400 or 409 && code is not null && message is not null)
        {
            return new MultiAgentException(MultiAgentFailure.Rejected, status, code, message);
        }

        return status >= 500
            ? new MultiAgentException(MultiAgentFailure.Unavailable)
            : new MultiAgentException(MultiAgentFailure.InvalidResponse);
    }

    [GeneratedRegex(@"^wf-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}\z")]
    private static partial Regex WorkflowIdPattern();

    private sealed record ServerErrorEnvelope(ServerError? Error);

    private sealed record ServerError(string? Code, string? Message);
}

public enum MultiAgentFailure
{
    Unavailable,
    Busy,
    NotFound,
    Rejected,
    InvalidResponse
}

public sealed class MultiAgentException(
    MultiAgentFailure failure,
    int status = 0,
    string? code = null,
    string? message = null,
    Exception? inner = null)
    : Exception(message ?? $"Multi-Agent Server failure: {failure}.", inner)
{
    public MultiAgentFailure Failure { get; } = failure;

    /// <summary>For <see cref="MultiAgentFailure.Rejected"/>: the server's 400 or 409 status and error code.</summary>
    public int Status { get; } = status;

    public string? Code { get; } = code;
}

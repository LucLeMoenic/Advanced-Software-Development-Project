using System.Net;
using System.Text;
using System.Text.Json;
using Accommodation.Backend.Api;
using Accommodation.Backend.Clients;

namespace Accommodation.Backend.Tests;

public sealed class MultiAgentClientTests
{
    private const string WorkflowId = "wf-20261021T010203Z-0123abcd";

    [Fact]
    public async Task StartPostsStudentOneEvidenceInServerFormat()
    {
        var handler = new StubHandler(_ => Json(HttpStatusCode.Accepted, $$"""{"id":"{{WorkflowId}}","status":"queued"}"""));
        var client = CreateClient(handler);

        var started = await client.StartAsync(
            [new EvidenceEntry("stay-7", "Harbour Stay", "Rank 1 of 1.")],
            "Recommend stays.",
            CancellationToken.None);

        Assert.Equal(new WorkflowStarted(WorkflowId, "queued"), started);
        var request = Assert.Single(handler.Requests);
        Assert.Equal("POST /workflows", request.Line);
        using var body = JsonDocument.Parse(request.Body!);
        Assert.Equal("student-1", body.RootElement.GetProperty("feature").GetString());
        Assert.Equal("Recommend stays.", body.RootElement.GetProperty("task").GetString());
        Assert.Equal("student-1-frontend", body.RootElement.GetProperty("submitted_by").GetString());
        var evidence = Assert.Single(body.RootElement.GetProperty("evidence").EnumerateArray());
        Assert.Equal("stay-7", evidence.GetProperty("id").GetString());
        Assert.Equal("Harbour Stay", evidence.GetProperty("title").GetString());
        Assert.Equal("Rank 1 of 1.", evidence.GetProperty("text").GetString());
    }

    [Fact]
    public async Task ListReturnsOnlyStudentOneWorkflows()
    {
        var client = CreateClient(new StubHandler(_ => Json(HttpStatusCode.OK, $$"""
            [
              {"id":"{{WorkflowId}}","feature":"student-1","task":"Mine","status":"approved","created_at":"a","updated_at":"b"},
              {"id":"wf-20261021T010203Z-ffffffff","feature":"student-2","task":"Theirs","status":"queued","created_at":"a","updated_at":"b"}
            ]
            """)));

        var summaries = await client.ListAsync(CancellationToken.None);

        var summary = Assert.Single(summaries);
        Assert.Equal(new WorkflowSummary(WorkflowId, "student-1", "Mine", "approved", "a", "b"), summary);
    }

    [Fact]
    public async Task GetMapsSnakeCaseRecordFields()
    {
        var client = CreateClient(new StubHandler(_ => Json(HttpStatusCode.OK, RecordJson("partially_accepted", """
            "human_decision":{"decision":"partial","notes":"Kept one","decided_by":"traveller","decided_at":"t","accepted_item_ids":["i1"]},
            "final_output":{"summary":"S","items":[{"id":"i1","subject":"Harbour Stay","detail":"D","evidence_ids":["stay-7"]}]}
            """))));

        var record = await client.GetAsync(WorkflowId, CancellationToken.None);

        Assert.Equal("partially_accepted", record.Status);
        Assert.Equal(["stay-7"], record.Plan!.RequiredEvidenceIds);
        Assert.Equal(["stay-7"], record.Work!.Items[0].EvidenceIds);
        Assert.Equal("concerns", record.Review!.ModelVerdict);
        Assert.Equal("i1", record.Review.Findings[0].ItemId);
        Assert.Equal(["i1"], record.HumanDecision!.AcceptedItemIds);
        Assert.Equal("Harbour Stay", record.FinalOutput!.Items[0].Subject);
    }

    [Fact]
    public async Task GetTreatsAnotherFeaturesWorkflowAsNotFound()
    {
        var client = CreateClient(new StubHandler(_ => Json(
            HttpStatusCode.OK,
            RecordJson("approved", feature: "student-2"))));

        var exception = await Assert.ThrowsAsync<MultiAgentException>(
            () => client.GetAsync(WorkflowId, CancellationToken.None));

        Assert.Equal(MultiAgentFailure.NotFound, exception.Failure);
    }

    [Fact]
    public async Task DecideChecksOwnershipThenPostsDecisionInServerFormat()
    {
        var handler = new StubHandler(request => request.Method == HttpMethod.Get
            ? Json(HttpStatusCode.OK, RecordJson("awaiting_human_review"))
            : Json(HttpStatusCode.OK, RecordJson("corrected")));
        var client = CreateClient(handler);
        var corrected = new WorkerOutput("Fixed", [new WorkItem("i1", "Harbour Stay", "Better detail.", ["stay-7"])]);

        var record = await client.DecideAsync(
            WorkflowId,
            new ReviewDecisionRequest("correct", "Clarified", corrected, null),
            CancellationToken.None);

        Assert.Equal("corrected", record.Status);
        Assert.Equal(
            [$"GET /workflows/{WorkflowId}", $"POST /workflows/{WorkflowId}/decision"],
            handler.Requests.Select(request => request.Line));
        using var body = JsonDocument.Parse(handler.Requests[1].Body!);
        Assert.Equal("correct", body.RootElement.GetProperty("decision").GetString());
        Assert.Equal("Clarified", body.RootElement.GetProperty("notes").GetString());
        Assert.Equal("traveller", body.RootElement.GetProperty("decided_by").GetString());
        var item = body.RootElement.GetProperty("corrected_output").GetProperty("items")[0];
        Assert.Equal("stay-7", item.GetProperty("evidence_ids")[0].GetString());
        Assert.False(body.RootElement.TryGetProperty("accepted_item_ids", out _));
    }

    [Fact]
    public async Task DecideDoesNotPostWhenTheWorkflowBelongsToAnotherFeature()
    {
        var handler = new StubHandler(_ => Json(HttpStatusCode.OK, RecordJson("awaiting_human_review", feature: "student-3")));
        var client = CreateClient(handler);

        var exception = await Assert.ThrowsAsync<MultiAgentException>(() => client.DecideAsync(
            WorkflowId,
            new ReviewDecisionRequest("approve", null, null, null),
            CancellationToken.None));

        Assert.Equal(MultiAgentFailure.NotFound, exception.Failure);
        Assert.Single(handler.Requests);
    }

    [Fact]
    public async Task ServerDecisionErrorIsReturnedWithItsStatusCodeAndMessage()
    {
        var client = CreateClient(new StubHandler(_ => Json(
            HttpStatusCode.Conflict,
            """{"error":{"code":"not_awaiting_review","message":"Workflow is approved, not awaiting human review.","fields":{}}}""")));

        var exception = await Assert.ThrowsAsync<MultiAgentException>(
            () => client.GetAsync(WorkflowId, CancellationToken.None));

        Assert.Equal(MultiAgentFailure.Rejected, exception.Failure);
        Assert.Equal(409, exception.Status);
        Assert.Equal("not_awaiting_review", exception.Code);
        Assert.Equal("Workflow is approved, not awaiting human review.", exception.Message);
    }

    [Theory]
    [InlineData(HttpStatusCode.ServiceUnavailable, """{"error":{"code":"busy","message":"Busy.","fields":{}}}""", MultiAgentFailure.Busy)]
    [InlineData(HttpStatusCode.ServiceUnavailable, "not json", MultiAgentFailure.Unavailable)]
    [InlineData(HttpStatusCode.InternalServerError, "{}", MultiAgentFailure.Unavailable)]
    [InlineData(HttpStatusCode.NotFound, """{"error":{"code":"not_found","message":"Workflow not found.","fields":{}}}""", MultiAgentFailure.NotFound)]
    [InlineData(HttpStatusCode.OK, "{not json", MultiAgentFailure.InvalidResponse)]
    [InlineData(HttpStatusCode.OK, """{"id":"wf-other","feature":"student-1","task":"T","status":"queued","evidence":[]}""", MultiAgentFailure.InvalidResponse)]
    [InlineData(HttpStatusCode.OK, """{"id":"wf-20261021T010203Z-0123abcd","feature":"student-1","task":"T","status":"unknown","evidence":[]}""", MultiAgentFailure.InvalidResponse)]
    public async Task ServerResponsesMapToFailures(HttpStatusCode status, string body, MultiAgentFailure expected)
    {
        var client = CreateClient(new StubHandler(_ => Json(status, body)));

        var exception = await Assert.ThrowsAsync<MultiAgentException>(
            () => client.GetAsync(WorkflowId, CancellationToken.None));

        Assert.Equal(expected, exception.Failure);
    }

    [Fact]
    public async Task ConnectionFailureIsUnavailable()
    {
        var client = CreateClient(new StubHandler(_ => throw new HttpRequestException("refused")));

        var exception = await Assert.ThrowsAsync<MultiAgentException>(
            () => client.ListAsync(CancellationToken.None));

        Assert.Equal(MultiAgentFailure.Unavailable, exception.Failure);
    }

    [Fact]
    public async Task StartRejectsAnInvalidWorkflowId()
    {
        var client = CreateClient(new StubHandler(_ => Json(HttpStatusCode.Accepted, """{"id":"../etc","status":"queued"}""")));

        var exception = await Assert.ThrowsAsync<MultiAgentException>(() => client.StartAsync(
            [new EvidenceEntry("stay-7", "Harbour Stay", "Rank 1 of 1.")],
            "Recommend stays.",
            CancellationToken.None));

        Assert.Equal(MultiAgentFailure.InvalidResponse, exception.Failure);
    }

    private static string RecordJson(string status, string extra = "", string feature = "student-1")
    {
        var decisionFields = extra.Length == 0 ? "" : "," + extra;
        return $$"""
            {
              "id":"{{WorkflowId}}","feature":"{{feature}}","task":"Task","status":"{{status}}",
              "created_at":"c","updated_at":"u","submitted_by":"student-1-frontend",
              "evidence":[{"id":"stay-7","title":"Harbour Stay","text":"Rank 1 of 1."}],
              "plan":{"objective":"O","steps":[{"id":"s1","description":"D"}],"required_evidence_ids":["stay-7"],"success_criteria":["C"]},
              "work":{"summary":"S","items":[{"id":"i1","subject":"Harbour Stay","detail":"D","evidence_ids":["stay-7"]}]},
              "review":{"verdict":"concerns","model_verdict":"concerns","degraded":false,"automatic_findings":[],"model_findings":[],
                        "findings":[{"severity":"warning","item_id":"i1","message":"M"}],"recommendations":["R"]},
              "history":[{"stage":"planner","raw_output":"ignored"}],"error":null
              {{decisionFields}}
            }
            """;
    }

    private static HttpResponseMessage Json(HttpStatusCode status, string body)
    {
        return new HttpResponseMessage(status)
        {
            Content = new StringContent(body, Encoding.UTF8, "application/json")
        };
    }

    private static MultiAgentClient CreateClient(HttpMessageHandler handler)
    {
        return new MultiAgentClient(new HttpClient(handler) { BaseAddress = new Uri("http://multi-agent.test") });
    }

    private sealed record RecordedRequest(string Line, string? Body);

    private sealed class StubHandler(Func<HttpRequestMessage, HttpResponseMessage> respond) : HttpMessageHandler
    {
        public List<RecordedRequest> Requests { get; } = [];

        protected override async Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            var body = request.Content is null ? null : await request.Content.ReadAsStringAsync(cancellationToken);
            Requests.Add(new($"{request.Method} {request.RequestUri!.AbsolutePath}", body));
            return respond(request);
        }
    }
}

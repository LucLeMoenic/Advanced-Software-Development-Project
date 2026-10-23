using System.Net;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using BudgetTracker.Backend.Api;
using BudgetTracker.Backend.Clients;
using BudgetTracker.Backend.Services;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace BudgetTracker.Backend.Tests;

public sealed class EndpointTests
{
    [Fact]
    public async Task WhatIfPreviewUsesCurrentActualsAndDoesNotMutateSource()
    {
        var database = FakeDatabase.WithJourney(actual: 9000);
        using var client = CreateClient(database, new FakeAdvice());
        var before = await client.GetStringAsync("/api/dashboard?journeyLabel=Journey");
        using var response = await client.PostAsJsonAsync("/api/what-if/preview", new { journeyLabel = " Journey ", limits = new[] { new WhatIfLimit(" FOOD ", 8000) } });
        var preview = await response.Content.ReadFromJsonAsync<WhatIfPreview>();
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(10000, preview!.Original.PlannedAmountMinor);
        Assert.Equal(8000, preview.Proposed.PlannedAmountMinor);
        Assert.Equal(9000, preview.Proposed.ActualAmountMinor);
        Assert.Equal(-1000, preview.Proposed.RemainingAmountMinor);
        Assert.Equal("overspent", preview.Proposed.Categories.Single().Status);
        Assert.Matches("^[a-f0-9]{64}$", preview.SnapshotHash);
        using var repeated = await client.PostAsJsonAsync("/api/what-if/preview", new { journeyLabel = "Journey", limits = new[] { new WhatIfLimit("food", 8000) } });
        Assert.Equal(preview.SnapshotHash, (await repeated.Content.ReadFromJsonAsync<WhatIfPreview>())!.SnapshotHash);
        Assert.Equal(before, await client.GetStringAsync("/api/dashboard?journeyLabel=Journey"));
    }

    [Theory]
    [InlineData("{}")]
    [InlineData("{\"journeyLabel\":\"Journey\",\"limits\":[]}")]
    [InlineData("{\"journeyLabel\":\"Journey\",\"limits\":[{\"category\":\"food\",\"limitAmountMinor\":0}]}")]
    [InlineData("{\"journeyLabel\":\"Journey\",\"limits\":[{\"category\":\"unknown\",\"limitAmountMinor\":100}]}")]
    [InlineData("{\"journeyLabel\":\"Journey\",\"limits\":[{\"category\":\"food\",\"limitAmountMinor\":100}],\"url\":\"http://elsewhere\"}")]
    [InlineData("{\"journeyLabel\":\"Journey\",\"journeyLabel\":\"Other\",\"limits\":[{\"category\":\"food\",\"limitAmountMinor\":100}]}")]
    [InlineData("{\"journeyLabel\":\"Jour\\r\\n\\tney\",\"limits\":[{\"category\":\"food\",\"limitAmountMinor\":100}]}")]
    public async Task WhatIfInvalidProposalDoesNotReadDatabase(string json)
    {
        var database = FakeDatabase.WithJourney();
        using var client = CreateClient(database, new FakeAdvice());
        using var response = await client.PostAsync("/api/what-if/preview", new StringContent(json, Encoding.UTF8, "application/json"));
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, database.CallCount);
    }

    [Fact]
    public async Task WhatIfMissingJourneyReturns404()
    {
        using var client = CreateClient(new FakeDatabase(), new FakeAdvice());
        using var response = await client.PostAsJsonAsync("/api/what-if/preview", new { journeyLabel = "Missing", limits = new[] { new WhatIfLimit("food", 8000) } });
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Theory]
    [InlineData("approve", "approved")]
    [InlineData("reject", "rejected")]
    [InlineData("partial", "partially_accepted")]
    [InlineData("correct", "corrected")]
    public async Task WhatIfStartPollAndAllHumanDecisionsArePreviewOnly(string decision, string status)
    {
        var database = FakeDatabase.WithJourney(actual: 9000);
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(database, server);
        using var client = factory.CreateClient();
        var before = await client.GetStringAsync("/api/dashboard?journeyLabel=Journey");
        var started = await StartWhatIf(client);
        var preview = started["preview"]!.ToJsonString();
        Assert.Equal("queued", started["status"]!.GetValue<string>());
        Assert.Equal("student-4", server.LastStart!["feature"]!.GetValue<string>());
        Assert.Equal(MultiAgentClient.TaskDescription, server.LastStart["task"]!.GetValue<string>());
        Assert.DoesNotContain("Meals", server.LastStart.ToJsonString());
        Assert.All(server.LastStart["evidence"]!.AsArray(), value => Assert.InRange(value!["text"]!.GetValue<string>().Length, 1, 800));
        Assert.Contains("\"belowSpent\":true", server.LastStart["evidence"]![1]!["text"]!.GetValue<string>());
        server.AwaitReview();
        using var pollRequest = WhatIfRequest(started, HttpMethod.Get);
        using var poll = await client.SendAsync(pollRequest);
        var polled = JsonNode.Parse(await poll.Content.ReadAsStringAsync())!;
        Assert.Equal(HttpStatusCode.OK, poll.StatusCode);
        Assert.Equal(preview, polled["preview"]!.ToJsonString());
        Assert.Null(polled["workflow"]!["human_decision"]);
        var correction = JsonNode.Parse("{\"summary\":\"Human commentary only.\",\"items\":[{\"id\":\"i3\",\"subject\":\"Category: food\",\"detail\":\"Review the below-spent proposal before using it.\",\"evidence_ids\":[\"category:food\"]}]}");
        var body = new JsonObject { ["decision"] = decision, ["notes"] = "Reviewed the preview.", ["decidedBy"] = "Test Reviewer" };
        if (decision == "partial") body["acceptedItemIds"] = new JsonArray("i1");
        if (decision == "correct") body["correctedOutput"] = correction!.DeepClone();
        using var decide = WhatIfRequest(started, HttpMethod.Post, body);
        using var response = await client.SendAsync(decide);
        var result = JsonNode.Parse(await response.Content.ReadAsStringAsync())!;
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(status, result["status"]!.GetValue<string>());
        Assert.Equal(preview, result["preview"]!.ToJsonString());
        Assert.Equal("Test Reviewer", result["workflow"]!["human_decision"]!["decided_by"]!.GetValue<string>());
        Assert.Equal(decision, server.LastDecision!["decision"]!.GetValue<string>());
        Assert.Equal("Reviewed the preview.", server.LastDecision["notes"]!.GetValue<string>());
        Assert.Equal("Test Reviewer", server.LastDecision["decided_by"]!.GetValue<string>());
        Assert.Null(server.LastDecision["decidedBy"]);
        if (decision == "correct") Assert.True(JsonNode.DeepEquals(correction, server.LastDecision["corrected_output"]));
        if (decision == "partial") Assert.Equal("i1", server.LastDecision["accepted_item_ids"]![0]!.GetValue<string>());
        Assert.Equal(1, server.Decisions);
        Assert.Equal(0, database.WriteCount);
        Assert.Equal(before, await client.GetStringAsync("/api/dashboard?journeyLabel=Journey"));
    }

    [Fact]
    public async Task WhatIfDisabledRoutesDoNotCallDependenciesButPreviewWorks()
    {
        var database = FakeDatabase.WithJourney();
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(database, server, false);
        using var client = factory.CreateClient();
        foreach (var request in new[] { new HttpRequestMessage(HttpMethod.Post, "/api/what-if/workflows"), new HttpRequestMessage(HttpMethod.Get, $"/api/what-if/workflows/{WhatIfServer.Id}"), new HttpRequestMessage(HttpMethod.Post, $"/api/what-if/workflows/{WhatIfServer.Id}/decision") })
        {
            using var response = await client.SendAsync(request);
            Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
            Assert.Equal("feature_disabled", (await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>())!.Error.Code);
            request.Dispose();
        }
        Assert.Equal(0, database.CallCount);
        Assert.Equal(0, server.CallCount);
        using var preview = await client.PostAsJsonAsync("/api/what-if/preview", WhatIfProposalBody());
        Assert.Equal(HttpStatusCode.OK, preview.StatusCode);
        Assert.Equal(0, database.WriteCount);
    }

    [Fact]
    public async Task WhatIfStaleStartHashStopsBeforeSharedStart()
    {
        var database = FakeDatabase.WithJourney();
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(database, server);
        using var client = factory.CreateClient();
        var body = WhatIfProposalBody();
        body["snapshotHash"] = new string('0', 64);
        using var response = await client.PostAsJsonAsync("/api/what-if/workflows", body);
        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal(0, server.CallCount);
        Assert.Equal(0, database.WriteCount);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task WhatIfDecisionRejectsStaleFinancialSource(bool removed)
    {
        var database = FakeDatabase.WithJourney(actual: 9000);
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(database, server);
        using var client = factory.CreateClient();
        var started = await StartWhatIf(client);
        server.AwaitReview();
        if (removed) database._budgets.Clear();
        else database._expenses[0] = database._expenses[0] with { ConvertedAmountMinor = 9100 };
        using var request = WhatIfRequest(started, HttpMethod.Post, WhatIfDecisionBody());
        using var response = await client.SendAsync(request);
        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal("snapshot_stale", (await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>())!.Error.Code);
        Assert.Equal(0, server.Decisions);
        Assert.Equal(0, database.WriteCount);
    }

    [Fact]
    public async Task WhatIfDecisionRequiresAwaitingHumanBeforeReadingFinancialSource()
    {
        var database = FakeDatabase.WithJourney();
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(database, server);
        using var client = factory.CreateClient();
        var started = await StartWhatIf(client);
        var calls = database.CallCount;
        using var request = WhatIfRequest(started, HttpMethod.Post, WhatIfDecisionBody());
        using var response = await client.SendAsync(request);
        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal(calls, database.CallCount);
        Assert.Equal(0, server.Decisions);
    }

    [Theory]
    [InlineData("missing")]
    [InlineData("tampered")]
    [InlineData("other-id")]
    [InlineData("other-provider")]
    public async Task WhatIfTokenBindingRejectsUnauthorizedPollsBeforeSharedCalls(string mode)
    {
        var database = FakeDatabase.WithJourney();
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(database, server);
        using var client = factory.CreateClient();
        var started = await StartWhatIf(client);
        var calls = server.CallCount;
        using var request = WhatIfRequest(started, HttpMethod.Get);
        if (mode == "missing") request.Headers.Remove("X-WhatIf-Token");
        if (mode == "tampered")
        {
            request.Headers.Remove("X-WhatIf-Token");
            request.Headers.Add("X-WhatIf-Token", "tampered" + started["token"]!.GetValue<string>());
        }
        if (mode == "other-id") request.RequestUri = new Uri($"/api/what-if/workflows/wf-20261023T120000Z-ffffffff", UriKind.Relative);
        using var otherFactory = WhatIfFactory(database, server);
        using var otherClient = otherFactory.CreateClient();
        using var response = await (mode == "other-provider" ? otherClient : client).SendAsync(request);
        Assert.Equal(HttpStatusCode.Forbidden, response.StatusCode);
        Assert.Equal(calls, server.CallCount);
    }

    [Theory]
    [InlineData("foreign-feature")]
    [InlineData("foreign-task")]
    [InlineData("foreign-id")]
    [InlineData("foreign-evidence")]
    [InlineData("unknown-citation")]
    [InlineData("unknown-subject")]
    [InlineData("multiline-subject")]
    [InlineData("multiline-item-id")]
    [InlineData("multiline-step-id")]
    [InlineData("multiline-evidence-id")]
    [InlineData("multiline-required-evidence-id")]
    [InlineData("duplicate-item")]
    [InlineData("malformed-plan")]
    [InlineData("malformed-review")]
    [InlineData("malformed-history")]
    public async Task WhatIfPollAndDecisionRejectForeignOrInvalidSharedRecords(string mode)
    {
        var database = FakeDatabase.WithJourney();
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(database, server);
        using var client = factory.CreateClient();
        var started = await StartWhatIf(client);
        server.AwaitReview();
        switch (mode)
        {
            case "foreign-feature": server.Record!["feature"] = "student-1"; break;
            case "foreign-task": server.Record!["task"] = "Write financial changes."; break;
            case "foreign-id": server.Record!["id"] = "wf-20261023T120000Z-ffffffff"; break;
            case "foreign-evidence": server.Record!["evidence"]![0]!["text"] = "{}"; break;
            case "unknown-citation": server.Record!["work"]!["items"]![0]!["evidence_ids"] = new JsonArray("foreign"); break;
            case "unknown-subject": server.Record!["work"]!["items"]![0]!["subject"] = "Unknown category"; break;
            case "multiline-subject": server.Record!["work"]!["items"]![0]!["subject"] = "Category:\r\n\tfood"; break;
            case "multiline-item-id": server.Record!["work"]!["items"]![0]!["id"] = "i1\n"; break;
            case "multiline-step-id": server.Record!["plan"]!["steps"]![0]!["id"] = "s1\n"; break;
            case "multiline-evidence-id": server.Record!["work"]!["items"]![0]!["evidence_ids"] = new JsonArray("category:food\n"); break;
            case "multiline-required-evidence-id": server.Record!["plan"]!["required_evidence_ids"] = new JsonArray("category:food\n"); break;
            case "duplicate-item": server.Record!["work"]!["items"]![1]!["id"] = "i1"; break;
            case "malformed-plan": server.Record!["plan"]!["steps"] = new JsonArray(); break;
            case "malformed-review": server.Record!["review"]!["verdict"] = "automatic_approval"; break;
            case "malformed-history": server.Record!["history"]![0]!["duration_ms"] = "not-a-duration"; break;
        }
        if (mode != "malformed-history") server.RefreshHistory();
        var calls = database.CallCount;
        using var pollRequest = WhatIfRequest(started, HttpMethod.Get);
        using var poll = await client.SendAsync(pollRequest);
        using var decision = WhatIfRequest(started, HttpMethod.Post, WhatIfDecisionBody());
        using var response = await client.SendAsync(decision);
        Assert.Equal(HttpStatusCode.BadGateway, poll.StatusCode);
        Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
        Assert.Equal(calls, database.CallCount);
        Assert.Equal(0, server.Decisions);
    }

    [Theory]
    [InlineData("reject", "rejected")]
    [InlineData("approve", "approved")]
    [InlineData("partial", "partially_accepted")]
    public async Task WhatIfKnownSubjectCitationMismatchCanBePolledAndHumanDecidedWithoutFinancialChanges(string decision, string status)
    {
        var database = FakeDatabase.WithJourney(actual: 9000);
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(database, server);
        using var client = factory.CreateClient();
        var before = await client.GetStringAsync("/api/dashboard?journeyLabel=Journey");
        var started = await StartWhatIf(client);
        server.AwaitReview();
        var record = server.Record!;
        record["work"]!["items"]![0]!["subject"] = "Journey budget snapshot";
        record["work"]!["items"]!.AsArray().RemoveAt(1);
        var finding = new JsonObject { ["severity"] = "blocking", ["item_id"] = "i1", ["message"] = "Subject 'Journey budget snapshot' does not match any evidence entry this item cites." };
        record["review"]!["automatic_findings"] = new JsonArray(finding.DeepClone());
        record["review"]!["findings"] = new JsonArray(finding.DeepClone());
        record["review"]!["verdict"] = "fail";
        server.RefreshHistory();
        using var pollRequest = WhatIfRequest(started, HttpMethod.Get);
        using var poll = await client.SendAsync(pollRequest);
        Assert.Equal(HttpStatusCode.OK, poll.StatusCode);
        var polled = JsonNode.Parse(await poll.Content.ReadAsStringAsync())!;
        Assert.Equal("awaiting_human_review", polled["status"]!.GetValue<string>());
        Assert.True(JsonNode.DeepEquals(record["review"], polled["workflow"]!["review"]));
        Assert.Null(polled["workflow"]!["human_decision"]);
        var body = WhatIfDecisionBody();
        body["decision"] = decision;
        body["notes"] = "The cited evidence does not match the subject.";
        if (decision == "partial") body["acceptedItemIds"] = new JsonArray("i1");
        using var decisionRequest = WhatIfRequest(started, HttpMethod.Post, body);
        using var response = await client.SendAsync(decisionRequest);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var result = JsonNode.Parse(await response.Content.ReadAsStringAsync())!;
        Assert.Equal(status, result["status"]!.GetValue<string>());
        if (decision == "reject") Assert.Null(result["workflow"]!["final_output"]);
        else Assert.True(JsonNode.DeepEquals(record["work"], result["workflow"]!["final_output"]));
        Assert.True(JsonNode.DeepEquals(started["preview"], result["preview"]));
        Assert.Equal(1, server.Decisions);
        Assert.Equal(0, database.WriteCount);
        Assert.Equal(before, await client.GetStringAsync("/api/dashboard?journeyLabel=Journey"));
    }

    [Fact]
    public async Task WhatIfMultilineNativeNarrativesCanPollAndHumanCorrectionIsAccepted()
    {
        const string narrative = "Review the proposal.\r\n\tActual spending remains unchanged.";
        var database = FakeDatabase.WithJourney(actual: 9000);
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(database, server);
        using var client = factory.CreateClient();
        var before = await client.GetStringAsync("/api/dashboard?journeyLabel=Journey");
        var started = await StartWhatIf(client);
        server.AwaitReview();
        var record = server.Record!;
        record["plan"]!["objective"] = narrative;
        record["plan"]!["steps"]![0]!["description"] = narrative;
        record["plan"]!["success_criteria"]![0] = narrative;
        record["work"]!["summary"] = narrative;
        record["work"]!["items"]![0]!["detail"] = narrative;
        var finding = new JsonObject { ["severity"] = "warning", ["item_id"] = "i1", ["message"] = narrative };
        record["review"]!["automatic_findings"] = new JsonArray(finding.DeepClone());
        record["review"]!["model_findings"] = new JsonArray(finding.DeepClone());
        record["review"]!["findings"] = new JsonArray(finding.DeepClone(), finding.DeepClone());
        record["review"]!["recommendations"] = new JsonArray(narrative);
        record["review"]!["model_verdict"] = "concerns";
        record["review"]!["verdict"] = "concerns";
        server.RefreshHistory();
        using var pollRequest = WhatIfRequest(started, HttpMethod.Get);
        using var poll = await client.SendAsync(pollRequest);
        Assert.Equal(HttpStatusCode.OK, poll.StatusCode);
        var polled = JsonNode.Parse(await poll.Content.ReadAsStringAsync())!;
        Assert.True(JsonNode.DeepEquals(record, polled["workflow"]));
        var body = WhatIfDecisionBody();
        body["decision"] = "correct";
        body["notes"] = narrative;
        body["correctedOutput"] = record["work"]!.DeepClone();
        server.AfterDecision = result => result["human_decision"]!["correction_findings"] = new JsonArray(finding.DeepClone());
        using var decision = WhatIfRequest(started, HttpMethod.Post, body);
        using var response = await client.SendAsync(decision);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var corrected = JsonNode.Parse(await response.Content.ReadAsStringAsync())!;
        Assert.Equal("corrected", corrected["status"]!.GetValue<string>());
        Assert.True(JsonNode.DeepEquals(body["correctedOutput"], corrected["workflow"]!["final_output"]));
        Assert.True(JsonNode.DeepEquals(started["preview"], corrected["preview"]));
        Assert.Equal(1, server.Decisions);
        Assert.Equal(0, database.WriteCount);
        Assert.Equal(before, await client.GetStringAsync("/api/dashboard?journeyLabel=Journey"));
    }

    [Theory]
    [InlineData("plan/objective", 300)]
    [InlineData("plan/steps/0/description", 200)]
    [InlineData("plan/success_criteria/0", 2000)]
    [InlineData("work/summary", 400)]
    [InlineData("work/items/0/detail", 400)]
    [InlineData("review/automatic_findings/0/message", 300)]
    [InlineData("review/model_findings/0/message", 300)]
    [InlineData("review/recommendations/0", 2000)]
    public async Task WhatIfInvalidNativeNarrativesCannotPollOrReachHumanDecision(string path, int maximum)
    {
        var database = FakeDatabase.WithJourney();
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(database, server);
        using var client = factory.CreateClient();
        var started = await StartWhatIf(client);
        var invalid = new[] { "Review\0proposal", "Review\bproposal", "Review\vproposal", "Review\fproposal", "Review\u001bproposal", "Review\u007fproposal", "Review\u0085proposal", "Review\u009fproposal", "", " \r\n\t", new string('a', maximum + 1) };
        foreach (var narrative in invalid)
        {
            server.AwaitReview();
            var record = server.Record!;
            var review = record["review"]!;
            var finding = new JsonObject { ["severity"] = "warning", ["item_id"] = "i1", ["message"] = "Review the proposal." };
            review["automatic_findings"] = new JsonArray(finding.DeepClone());
            review["model_findings"] = new JsonArray(finding.DeepClone());
            review["recommendations"] = new JsonArray("Review the proposal.");
            review["model_verdict"] = "concerns";
            review["verdict"] = "concerns";
            var segments = path.Split('/');
            JsonNode parent = record;
            foreach (var segment in segments[..^1]) parent = parent is JsonArray array ? array[int.Parse(segment)]! : parent[segment]!;
            if (parent is JsonArray values) values[int.Parse(segments[^1])] = narrative;
            else parent[segments[^1]] = narrative;
            review["findings"] = new JsonArray(review["automatic_findings"]!.AsArray().Concat(review["model_findings"]!.AsArray()).Select(value => value!.DeepClone()).ToArray());
            server.RefreshHistory();
            var calls = database.CallCount;
            using var pollRequest = WhatIfRequest(started, HttpMethod.Get);
            using var poll = await client.SendAsync(pollRequest);
            using var decision = WhatIfRequest(started, HttpMethod.Post, WhatIfDecisionBody());
            using var response = await client.SendAsync(decision);
            Assert.Equal(HttpStatusCode.BadGateway, poll.StatusCode);
            Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
            Assert.Equal(calls, database.CallCount);
        }
        Assert.Equal(0, server.Decisions);
        Assert.Equal(0, database.WriteCount);
    }

    [Fact]
    public async Task WhatIfPolledHumanCorrectionStillRejectsMismatchedSubjectCitation()
    {
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(FakeDatabase.WithJourney(), server);
        using var client = factory.CreateClient();
        var started = await StartWhatIf(client);
        server.AwaitReview();
        var body = WhatIfDecisionBody();
        body["decision"] = "correct";
        body["correctedOutput"] = server.Record!["work"]!.DeepClone();
        using var decision = WhatIfRequest(started, HttpMethod.Post, body);
        using var response = await client.SendAsync(decision);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        server.Record["final_output"]!["items"]![0]!["subject"] = "Journey budget snapshot";
        using var pollRequest = WhatIfRequest(started, HttpMethod.Get);
        using var poll = await client.SendAsync(pollRequest);
        Assert.Equal(HttpStatusCode.BadGateway, poll.StatusCode);
        Assert.Equal(1, server.Decisions);
    }

    [Theory]
    [InlineData("name")]
    [InlineData("placeholder")]
    [InlineData("long-name")]
    [InlineData("multiline-name")]
    [InlineData("long-notes")]
    [InlineData("control-notes")]
    [InlineData("reject")]
    [InlineData("partial-duplicate")]
    [InlineData("partial-unknown")]
    [InlineData("correction-money")]
    [InlineData("correction-citation")]
    [InlineData("correction-subject")]
    [InlineData("correction-unknown-subject")]
    [InlineData("correction-control-summary")]
    [InlineData("correction-control-detail")]
    [InlineData("correction-long-summary")]
    [InlineData("correction-long-detail")]
    public async Task WhatIfInvalidHumanDecisionsNeverReachSharedDecision(string mode)
    {
        var database = FakeDatabase.WithJourney();
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(database, server);
        using var client = factory.CreateClient();
        var started = await StartWhatIf(client);
        server.AwaitReview();
        var body = WhatIfDecisionBody();
        switch (mode)
        {
            case "name": body["decidedBy"] = " "; break;
            case "placeholder": body["decidedBy"] = "human"; break;
            case "long-name": body["decidedBy"] = new string('a', 61); break;
            case "multiline-name": body["decidedBy"] = "Test\r\n\tReviewer"; break;
            case "long-notes": body["notes"] = new string('a', 1001); break;
            case "control-notes": body["notes"] = "Review\u001bproposal"; break;
            case "reject": body["decision"] = "reject"; body["notes"] = " "; break;
            case "partial-duplicate": body["decision"] = "partial"; body["acceptedItemIds"] = new JsonArray("i1", "i1"); break;
            case "partial-unknown": body["decision"] = "partial"; body["acceptedItemIds"] = new JsonArray("i9"); break;
            default:
                body["decision"] = "correct";
                body["correctedOutput"] = server.Record!["work"]!.DeepClone();
                if (mode == "correction-money") body["correctedOutput"]!["limitAmountMinor"] = 100;
                if (mode == "correction-citation") body["correctedOutput"]!["items"]![0]!["evidence_ids"] = new JsonArray("foreign");
                if (mode == "correction-subject") body["correctedOutput"]!["items"]![0]!["subject"] = "Journey budget snapshot";
                if (mode == "correction-unknown-subject") body["correctedOutput"]!["items"]![0]!["subject"] = "Unknown category";
                if (mode == "correction-control-summary") body["correctedOutput"]!["summary"] = "Review\u001bproposal";
                if (mode == "correction-control-detail") body["correctedOutput"]!["items"]![0]!["detail"] = "Review\0proposal";
                if (mode == "correction-long-summary") body["correctedOutput"]!["summary"] = new string('a', 401);
                if (mode == "correction-long-detail") body["correctedOutput"]!["items"]![0]!["detail"] = new string('a', 401);
                break;
        }
        using var request = WhatIfRequest(started, HttpMethod.Post, body);
        using var response = await client.SendAsync(request);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, server.Decisions);
        Assert.Equal(0, database.WriteCount);
    }

    [Theory]
    [InlineData("notes")]
    [InlineData("name")]
    [InlineData("decision")]
    [InlineData("correction")]
    [InlineData("selection")]
    public async Task WhatIfReturnedHumanDecisionMustMatchTheSubmittedDecision(string mode)
    {
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(FakeDatabase.WithJourney(), server);
        using var client = factory.CreateClient();
        var started = await StartWhatIf(client);
        server.AwaitReview();
        var body = WhatIfDecisionBody();
        if (mode == "correction") { body["decision"] = "correct"; body["correctedOutput"] = server.Record!["work"]!.DeepClone(); }
        if (mode == "selection") { body["decision"] = "partial"; body["acceptedItemIds"] = new JsonArray("i1"); }
        server.AfterDecision = record =>
        {
            if (mode == "notes") record["human_decision"]!["notes"] = "Different notes";
            if (mode == "name") record["human_decision"]!["decided_by"] = "Different Reviewer";
            if (mode == "decision") { record["human_decision"]!["decision"] = "reject"; record["status"] = "rejected"; record["final_output"] = null; }
            if (mode == "correction") record["final_output"]!["summary"] = "A substituted correction";
            if (mode == "selection")
            {
                record["human_decision"]!["accepted_item_ids"] = new JsonArray("i2");
                record["human_decision"]!["rejected_item_ids"] = new JsonArray("i1");
                record["final_output"]!["items"] = new JsonArray(record["work"]!["items"]![1]!.DeepClone());
            }
        };
        using var request = WhatIfRequest(started, HttpMethod.Post, body);
        using var response = await client.SendAsync(request);
        Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
        Assert.Equal(1, server.Decisions);
    }

    [Theory]
    [InlineData("busy", 503)]
    [InlineData("unavailable", 503)]
    [InlineData("timeout", 503)]
    [InlineData("malformed", 502)]
    [InlineData("oversized", 502)]
    [InlineData("deep", 502)]
    [InlineData("redirect", 502)]
    [InlineData("unavailable-array", 503)]
    public async Task WhatIfSharedFailuresAreBoundedAndNeverRetried(string mode, int status)
    {
        using var server = new WhatIfServer
        {
            Fault = (_, _) => mode switch
            {
                "busy" => Task.FromResult(WhatIfServer.Json(new JsonObject { ["error"] = new JsonObject { ["code"] = "busy" } }, HttpStatusCode.ServiceUnavailable)),
                "unavailable" => throw new HttpRequestException("offline"),
                "timeout" => throw new TaskCanceledException("timeout"),
                "oversized" => Task.FromResult(new HttpResponseMessage(HttpStatusCode.Accepted) { Content = new UnknownLengthContent(new string('x', 256 * 1024 + 1)) }),
                "deep" => Task.FromResult(new HttpResponseMessage(HttpStatusCode.Accepted) { Content = new UnknownLengthContent(new string('[', 33) + "0" + new string(']', 33)) }),
                "redirect" => Task.FromResult(new HttpResponseMessage(HttpStatusCode.TemporaryRedirect) { Content = new StringContent("{}") }),
                "unavailable-array" => Task.FromResult(new HttpResponseMessage(HttpStatusCode.ServiceUnavailable) { Content = new UnknownLengthContent("[]") }),
                _ => Task.FromResult(new HttpResponseMessage(HttpStatusCode.Accepted) { Content = new UnknownLengthContent("not-json") })
            }
        };
        var database = FakeDatabase.WithJourney();
        using var factory = WhatIfFactory(database, server);
        using var client = factory.CreateClient();
        var body = WhatIfProposalBody();
        using var preview = await client.PostAsJsonAsync("/api/what-if/preview", body);
        body["snapshotHash"] = JsonNode.Parse(await preview.Content.ReadAsStringAsync())!["snapshotHash"]!.GetValue<string>();
        using var response = await client.PostAsJsonAsync("/api/what-if/workflows", body);
        Assert.Equal(status, (int)response.StatusCode);
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();
        Assert.NotEmpty(error!.Error.CorrelationId);
        if (mode == "timeout") Assert.Contains("Poll", error.Error.Message);
        Assert.Equal(1, server.CallCount);
        Assert.Equal(0, database.WriteCount);
    }

    [Fact]
    public async Task WhatIfAcceptedStartReadFailureReturnsBindingForRecoveryPoll()
    {
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(FakeDatabase.WithJourney(), server);
        using var client = factory.CreateClient();
        var body = WhatIfProposalBody();
        using var preview = await client.PostAsJsonAsync("/api/what-if/preview", body);
        body["snapshotHash"] = JsonNode.Parse(await preview.Content.ReadAsStringAsync())!["snapshotHash"]!.GetValue<string>();
        server.Fault = (request, _) => request.Method == HttpMethod.Get ? throw new TaskCanceledException() : Task.FromResult<HttpResponseMessage>(null!);
        using var response = await client.PostAsJsonAsync("/api/what-if/workflows", body);
        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        var error = JsonNode.Parse(await response.Content.ReadAsStringAsync())!["error"]!;
        Assert.Equal(WhatIfServer.Id, error["fields"]!["id"]!.GetValue<string>());
        Assert.NotEmpty(error["fields"]!["token"]!.GetValue<string>());
        server.Fault = null;
        using var pollRequest = WhatIfRequest(error["fields"]!.AsObject(), HttpMethod.Get);
        using var poll = await client.SendAsync(pollRequest);
        Assert.Equal(HttpStatusCode.OK, poll.StatusCode);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task WhatIfOversizedRequestIsRejectedBeforeDependencies(bool streaming)
    {
        var database = FakeDatabase.WithJourney();
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(database, server);
        using var client = factory.CreateClient();
        var payload = new string(' ', 16 * 1024 + 1);
        using var content = streaming ? (HttpContent)new UnknownLengthContent(payload) : new StringContent(payload, Encoding.UTF8, "application/json");
        using var response = await client.PostAsync("/api/what-if/preview", content);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, database.CallCount);
        Assert.Equal(0, server.CallCount);
    }

    [Theory]
    [InlineData("negative")]
    [InlineData("unsafe")]
    [InlineData("overflow")]
    [InlineData("foreign-expense")]
    [InlineData("mixed-currency")]
    public async Task WhatIfUnsafeSourceReturns502WithoutSharedCalls(string mode)
    {
        var database = FakeDatabase.WithJourney(actual: 9000);
        if (mode == "negative") database._expenses[0] = database._expenses[0] with { ConvertedAmountMinor = -1 };
        if (mode == "unsafe") database._budgets[0] = database._budgets[0] with { LimitAmountMinor = 9_007_199_254_740_992 };
        if (mode == "overflow") database._budgets.AddRange(Enumerable.Range(2, 1024).Select(id => database._budgets[0] with { Id = id, LimitAmountMinor = 9_007_199_254_740_991 }));
        if (mode == "foreign-expense") database._expenses[0] = database._expenses[0] with { BudgetId = 999 };
        if (mode == "mixed-currency") database._budgets.Add(database._budgets[0] with { Id = 2, Category = "transport", BaseCurrency = "USD" });
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(database, server);
        using var client = factory.CreateClient();
        using var response = await client.PostAsJsonAsync("/api/what-if/preview", WhatIfProposalBody());
        Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
        Assert.Equal(0, server.CallCount);
        Assert.Equal(0, database.WriteCount);
    }

    [Theory]
    [InlineData(null, false)]
    [InlineData("true", true)]
    [InlineData("false", false)]
    public async Task WhatIfStrictFlagDefaultsAndCapabilities(string? flag, bool enabled)
    {
        using var factory = CreateFactory(new FakeDatabase(), new FakeAdvice(), new Dictionary<string, string?> { ["MULTI_AGENT_ENABLED"] = flag });
        using var client = factory.CreateClient();
        var capability = await client.GetFromJsonAsync<JsonElement>("/api/capabilities");
        Assert.Equal(enabled, capability.GetProperty("multiAgentEnabled").GetBoolean());
        Assert.Equal(enabled, factory.Services.GetRequiredService<FeatureModeSettings>().MultiAgentEnabled);
        Assert.False(new FeatureModeSettings(false, false, false).MultiAgentEnabled);
    }

    [Theory]
    [InlineData("True")]
    [InlineData("FALSE")]
    [InlineData(" true")]
    [InlineData("false ")]
    [InlineData("1")]
    [InlineData("")]
    public void WhatIfStrictFlagRejectsNoncanonicalValuesAtStartup(string flag)
    {
        using var factory = CreateFactory(new FakeDatabase(), new FakeAdvice(), new Dictionary<string, string?> { ["MULTI_AGENT_ENABLED"] = flag });
        Assert.Contains("MULTI_AGENT_ENABLED", Assert.ThrowsAny<Exception>(() => factory.CreateClient()).ToString());
    }

    [Theory]
    [InlineData("file:///tmp")]
    [InlineData("http://test-user@localhost:5600")]
    [InlineData("http://localhost:5600/foreign")]
    [InlineData("http://localhost:5600?url=foreign")]
    public void WhatIfConfiguredServerRejectsUnsafeUris(string url) => Assert.Throws<InvalidOperationException>(() => MultiAgentClient.ServerUri(url));

    [Fact]
    public async Task WhatIfExpiredTokenCannotPollOrDecide()
    {
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(FakeDatabase.WithJourney(), server);
        using var client = factory.CreateClient();
        var started = await StartWhatIf(client);
        var protector = factory.Services.GetRequiredService<IDataProtectionProvider>().CreateProtector("student-4.what-if.binding.v1").ToTimeLimitedDataProtector();
        var payload = protector.Unprotect(started["token"]!.GetValue<string>(), out var expiry);
        Assert.InRange(expiry - DateTimeOffset.UtcNow, TimeSpan.FromMinutes(119), TimeSpan.FromMinutes(121));
        started["token"] = protector.Protect(payload, DateTimeOffset.UtcNow.AddMinutes(-1));
        var calls = server.CallCount;
        using var pollRequest = WhatIfRequest(started, HttpMethod.Get);
        using var poll = await client.SendAsync(pollRequest);
        using var decideRequest = WhatIfRequest(started, HttpMethod.Post, WhatIfDecisionBody());
        using var decide = await client.SendAsync(decideRequest);
        Assert.Equal(HttpStatusCode.Forbidden, poll.StatusCode);
        Assert.Equal(HttpStatusCode.Forbidden, decide.StatusCode);
        Assert.Equal(calls, server.CallCount);
    }

    [Theory]
    [InlineData("not-a-workflow")]
    [InlineData("wf-20261023T120000Z-1234abcd%2F..")]
    [InlineData("wf-20261023T120000Z-1234abcd%3Fforeign")]
    public async Task WhatIfWorkflowPathInjectionNeverReachesSharedServer(string id)
    {
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(FakeDatabase.WithJourney(), server);
        using var client = factory.CreateClient();
        using var response = await client.GetAsync("/api/what-if/workflows/" + id);
        Assert.True(response.StatusCode is HttpStatusCode.BadRequest or HttpStatusCode.NotFound);
        Assert.Equal(0, server.CallCount);
    }

    [Fact]
    public async Task WhatIfSixCategoryEvidenceFitsAndHashIgnoresProposalAndSourceOrdering()
    {
        var database = FakeDatabase.WithJourney(actual: 9000);
        var label = string.Concat(Enumerable.Repeat("\U0001f30d", 40));
        database._budgets[0] = database._budgets[0] with { JourneyLabel = label };
        var names = new[] { "transport", "activities", "accommodation", "shopping", "other" };
        for (var index = 0; index < names.Length; index++) database._budgets.Add(database._budgets[0] with { Id = index + 2, Category = names[index] });
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(database, server);
        using var client = factory.CreateClient();
        var body = new JsonObject { ["journeyLabel"] = label, ["limits"] = JsonSerializer.SerializeToNode(database._budgets.Select(value => new WhatIfLimit(value.Category.ToUpperInvariant(), 1)), new JsonSerializerOptions(JsonSerializerDefaults.Web)) };
        using var previewResponse = await client.PostAsJsonAsync("/api/what-if/preview", body);
        Assert.Equal(HttpStatusCode.OK, previewResponse.StatusCode);
        var preview = JsonNode.Parse(await previewResponse.Content.ReadAsStringAsync())!;
        database._budgets.Reverse();
        body["limits"] = JsonSerializer.SerializeToNode(database._budgets.Select(value => new WhatIfLimit(value.Category, 1)), new JsonSerializerOptions(JsonSerializerDefaults.Web));
        using var reordered = await client.PostAsJsonAsync("/api/what-if/preview", body);
        Assert.Equal(preview["snapshotHash"]!.GetValue<string>(), JsonNode.Parse(await reordered.Content.ReadAsStringAsync())!["snapshotHash"]!.GetValue<string>());
        body["snapshotHash"] = preview["snapshotHash"]!.GetValue<string>();
        using var start = await client.PostAsJsonAsync("/api/what-if/workflows", body);
        Assert.Equal(HttpStatusCode.Accepted, start.StatusCode);
        var started = JsonNode.Parse(await start.Content.ReadAsStringAsync())!.AsObject();
        Assert.True(JsonNode.DeepEquals(preview, started["preview"]));
        Assert.Equal(7, server.LastStart!["evidence"]!.AsArray().Count);
        Assert.DoesNotContain("journeyLabel", server.LastStart["evidence"]!.ToJsonString());
        Assert.All(server.LastStart["evidence"]!.AsArray(), value => Assert.InRange(value!["text"]!.GetValue<string>().Length, 1, 800));
        foreach (var entry in server.LastStart["evidence"]!.AsArray().Where(value => value!["id"]!.GetValue<string>() != "snapshot"))
        {
            var category = JsonNode.Parse(entry!["text"]!.GetValue<string>())!;
            var original = category["original"]!;
            var proposed = category["proposed"]!;
            string Major(string field, JsonNode source) => (source[field]!.GetValue<long>() / 100m).ToString("F2", System.Globalization.CultureInfo.InvariantCulture);
            Assert.Equal($"AUD limits {Major("plannedAmountMinor", original)} -> {Major("plannedAmountMinor", proposed)}; actual {Major("actualAmountMinor", proposed)}; proposed remaining {Major("remainingAmountMinor", proposed)}", category["display"]!.GetValue<string>());
        }
    }

    [Fact]
    public async Task WhatIfStreamingResponseDeadlineIncludesBodyReads()
    {
        using var server = new WhatIfServer { Fault = (_, _) => Task.FromResult(new HttpResponseMessage(HttpStatusCode.Accepted) { Content = new BlockedContent() }) };
        using var factory = WhatIfFactory(FakeDatabase.WithJourney(), server);
        using var client = factory.CreateClient();
        var body = WhatIfProposalBody();
        using var preview = await client.PostAsJsonAsync("/api/what-if/preview", body);
        body["snapshotHash"] = JsonNode.Parse(await preview.Content.ReadAsStringAsync())!["snapshotHash"]!.GetValue<string>();
        var timer = System.Diagnostics.Stopwatch.StartNew();
        using var response = await client.PostAsJsonAsync("/api/what-if/workflows", body);
        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        Assert.Equal("multi_agent_timeout", (await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>())!.Error.Code);
        Assert.InRange(timer.Elapsed, TimeSpan.FromSeconds(8), TimeSpan.FromSeconds(25));
        Assert.Equal(1, server.CallCount);
    }

    [Fact]
    public async Task WhatIfDecisionTimeoutDoesNotRetryAndCanBeResolvedByPolling()
    {
        var database = FakeDatabase.WithJourney();
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(database, server);
        using var client = factory.CreateClient();
        var started = await StartWhatIf(client);
        server.AwaitReview();
        server.AfterDecision = _ => throw new TaskCanceledException("response lost after shared save");
        using var request = WhatIfRequest(started, HttpMethod.Post, WhatIfDecisionBody());
        using var response = await client.SendAsync(request);
        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        Assert.Contains("Poll", (await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>())!.Error.Message);
        using var pollRequest = WhatIfRequest(started, HttpMethod.Get);
        using var poll = await client.SendAsync(pollRequest);
        Assert.Equal(HttpStatusCode.OK, poll.StatusCode);
        Assert.Equal("approved", JsonNode.Parse(await poll.Content.ReadAsStringAsync())!["status"]!.GetValue<string>());
        Assert.Equal(1, server.Decisions);
        Assert.Equal(0, database.WriteCount);
    }

    [Theory]
    [InlineData("queued")]
    [InlineData("planning")]
    [InlineData("working")]
    [InlineData("reviewing")]
    [InlineData("awaiting_human_review")]
    [InlineData("failed")]
    [InlineData("degraded")]
    public async Task WhatIfPollingAcceptsSharedLifecycleRecordsWithoutInventingHumanDecisions(string status)
    {
        using var server = new WhatIfServer();
        using var factory = WhatIfFactory(FakeDatabase.WithJourney(), server);
        using var client = factory.CreateClient();
        var started = await StartWhatIf(client);
        server.AwaitReview();
        var record = server.Record!;
        record["status"] = status == "degraded" ? "awaiting_human_review" : status;
        if (status is "queued" or "planning") { record["plan"] = null; record["work"] = null; record["review"] = null; record["history"] = new JsonArray(); }
        if (status == "working") { record["work"] = null; record["review"] = null; record["history"]!.AsArray().RemoveAt(2); record["history"]!.AsArray().RemoveAt(1); }
        if (status == "reviewing") { record["review"] = null; record["history"]!.AsArray().RemoveAt(2); }
        if (status == "failed")
        {
            record["error"] = new JsonObject { ["code"] = "workflow_interrupted", ["stage"] = "reviewing", ["message"] = "The server restarted." };
            record["history"]!.AsArray().Add(new JsonObject { ["stage"] = "system", ["ok"] = false, ["error"] = record["error"]!.DeepClone() });
        }
        if (status == "degraded")
        {
            var finding = new JsonObject { ["severity"] = "warning", ["item_id"] = null, ["message"] = "Reviewer model unavailable; automatic checks only." };
            record["review"]!["degraded"] = true;
            record["review"]!["model_verdict"] = "concerns";
            record["review"]!["verdict"] = "concerns";
            record["review"]!["model_findings"] = new JsonArray(finding.DeepClone());
            record["review"]!["findings"] = new JsonArray(finding.DeepClone());
            record["history"]!.AsArray().RemoveAt(2);
            record["history"]!.AsArray().Add(new JsonObject { ["stage"] = "reviewer", ["ok"] = false, ["degraded"] = true, ["at"] = "2026-10-23T12:01:00.000Z", ["error"] = new JsonObject { ["code"] = "timeout", ["message"] = "Reviewer timed out.", ["detail"] = null, ["raw_output"] = null } });
        }
        using var request = WhatIfRequest(started, HttpMethod.Get);
        using var response = await client.SendAsync(request);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var result = JsonNode.Parse(await response.Content.ReadAsStringAsync())!;
        Assert.Null(result["workflow"]!["human_decision"]);
        Assert.Null(result["workflow"]!["final_output"]);
    }

    private static JsonObject WhatIfProposalBody() => new() { ["journeyLabel"] = "Journey", ["limits"] = new JsonArray(new JsonObject { ["category"] = "food", ["limitAmountMinor"] = 8000 }) };
    private static JsonObject WhatIfDecisionBody() => new() { ["decision"] = "approve", ["notes"] = "Reviewed the preview.", ["decidedBy"] = "Test Reviewer" };
    private static WebApplicationFactory<Program> WhatIfFactory(FakeDatabase database, WhatIfServer server, bool enabled = true) => CreateFactory(database, new FakeAdvice(), new Dictionary<string, string?> { ["MULTI_AGENT_ENABLED"] = enabled ? "true" : "false", ["MULTI_AGENT_SERVER_URL"] = "http://what-if.test:5600", ["Logging:LogLevel:Default"] = "Warning" }, server);

    private static async Task<JsonObject> StartWhatIf(HttpClient client)
    {
        var body = WhatIfProposalBody();
        using var preview = await client.PostAsJsonAsync("/api/what-if/preview", body);
        Assert.Equal(HttpStatusCode.OK, preview.StatusCode);
        body["snapshotHash"] = JsonNode.Parse(await preview.Content.ReadAsStringAsync())!["snapshotHash"]!.GetValue<string>();
        using var start = await client.PostAsJsonAsync("/api/what-if/workflows", body);
        Assert.Equal(HttpStatusCode.Accepted, start.StatusCode);
        return JsonNode.Parse(await start.Content.ReadAsStringAsync())!.AsObject();
    }

    private static HttpRequestMessage WhatIfRequest(JsonObject started, HttpMethod method, JsonObject? body = null)
    {
        var request = new HttpRequestMessage(method, $"/api/what-if/workflows/{started["id"]!.GetValue<string>()}" + (method == HttpMethod.Post ? "/decision" : ""));
        request.Headers.Add("X-WhatIf-Token", started["token"]!.GetValue<string>());
        if (body is not null) request.Content = JsonContent.Create(body);
        return request;
    }

    private sealed class WhatIfServer : HttpMessageHandler
    {
        public const string Id = "wf-20261023T120000Z-1234abcd";
        public int CallCount { get; private set; }
        public int Decisions { get; private set; }
        public JsonObject? Record { get; private set; }
        public JsonObject? LastStart { get; private set; }
        public JsonObject? LastDecision { get; private set; }
        public Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>>? Fault { get; set; }
        public Action<JsonObject>? AfterDecision { get; set; }

        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            CallCount++;
            Assert.Equal("what-if.test", request.RequestUri!.Host);
            if (Fault is not null)
            {
                var failure = await Fault(request, cancellationToken);
                if (failure is not null) return failure;
            }
            if (request.Method == HttpMethod.Post && request.RequestUri.AbsolutePath == "/workflows")
            {
                LastStart = JsonNode.Parse(await request.Content!.ReadAsStringAsync(cancellationToken))!.AsObject();
                Record = new JsonObject
                {
                    ["id"] = Id, ["feature"] = LastStart["feature"]!.DeepClone(), ["task"] = LastStart["task"]!.DeepClone(), ["submitted_by"] = LastStart["submitted_by"]!.DeepClone(),
                    ["status"] = "queued", ["created_at"] = "2026-10-23T12:00:00.000Z", ["updated_at"] = "2026-10-23T12:00:00.000Z", ["evidence"] = LastStart["evidence"]!.DeepClone(),
                    ["plan"] = null, ["work"] = null, ["review"] = null, ["human_decision"] = null, ["final_output"] = null, ["history"] = new JsonArray(), ["error"] = null
                };
                return Json(new JsonObject { ["id"] = Id, ["status"] = "queued" }, HttpStatusCode.Accepted);
            }
            Assert.NotNull(Record);
            if (request.Method == HttpMethod.Post)
            {
                Assert.Equal($"/workflows/{Id}/decision", request.RequestUri.AbsolutePath);
                Decisions++;
                LastDecision = JsonNode.Parse(await request.Content!.ReadAsStringAsync(cancellationToken))!.AsObject();
                var decision = LastDecision["decision"]!.GetValue<string>();
                Record["status"] = decision switch { "approve" => "approved", "reject" => "rejected", "partial" => "partially_accepted", _ => "corrected" };
                var human = new JsonObject { ["decision"] = decision, ["notes"] = LastDecision["notes"]!.DeepClone(), ["decided_by"] = LastDecision["decided_by"]!.DeepClone(), ["decided_at"] = "2026-10-23T12:01:00.000Z" };
                Record["final_output"] = decision == "reject" ? null : decision == "correct" ? LastDecision["corrected_output"]!.DeepClone() : Record["work"]!.DeepClone();
                if (decision == "correct") human["correction_findings"] = new JsonArray();
                if (decision == "partial")
                {
                    var accepted = LastDecision["accepted_item_ids"]!.AsArray().Select(value => value!.GetValue<string>()).ToArray();
                    human["accepted_item_ids"] = LastDecision["accepted_item_ids"]!.DeepClone();
                    human["rejected_item_ids"] = new JsonArray(Record["work"]!["items"]!.AsArray().Where(value => !accepted.Contains(value!["id"]!.GetValue<string>())).Select(value => (JsonNode?)JsonValue.Create(value!["id"]!.GetValue<string>())).ToArray());
                    Record["final_output"]!["items"] = new JsonArray(Record["work"]!["items"]!.AsArray().Where(value => accepted.Contains(value!["id"]!.GetValue<string>())).Select(value => value!.DeepClone()).ToArray());
                }
                Record["human_decision"] = human;
                AfterDecision?.Invoke(Record);
            }
            else Assert.Equal($"/workflows/{Id}", request.RequestUri.AbsolutePath);
            return Json(Record);
        }

        public void AwaitReview()
        {
            Record!["status"] = "awaiting_human_review";
            Record["plan"] = JsonNode.Parse("{\"objective\":\"Assess category limits.\",\"steps\":[{\"id\":\"s1\",\"description\":\"Compare supplied snapshots.\"}],\"required_evidence_ids\":[\"category:food\"],\"success_criteria\":[\"Preview only.\"]}");
            Record["work"] = JsonNode.Parse("{\"summary\":\"Review proposed limits.\",\"items\":[{\"id\":\"i1\",\"subject\":\"Category: food\",\"detail\":\"Review the category proposal.\",\"evidence_ids\":[\"category:food\"]},{\"id\":\"i2\",\"subject\":\"Journey budget snapshot\",\"detail\":\"Actual spending stays unchanged.\",\"evidence_ids\":[\"snapshot\"]}]}");
            Record["review"] = JsonNode.Parse("{\"verdict\":\"pass\",\"model_verdict\":\"pass\",\"degraded\":false,\"automatic_findings\":[],\"model_findings\":[],\"findings\":[],\"recommendations\":[]}");
            RefreshHistory();
        }

        public void RefreshHistory()
        {
            Record!["history"] = new JsonArray(new[] { "planner", "worker", "reviewer" }.Select(stage => (JsonNode)new JsonObject
            {
                ["stage"] = stage, ["agent"] = stage, ["prompt"] = stage == "planner" ? "multi-agent-planner-v1.txt" : stage == "worker" ? "multi-agent-worker-v2.txt" : "multi-agent-reviewer-v1.txt", ["model"] = "test-model",
                ["started_at"] = "2026-10-23T12:00:00.000Z", ["finished_at"] = "2026-10-23T12:00:01.000Z", ["duration_ms"] = 1000, ["ok"] = true, ["output"] = Record[stage == "planner" ? "plan" : stage == "worker" ? "work" : "review"]!.DeepClone()
            }).ToArray());
        }

        public static HttpResponseMessage Json(JsonNode value, HttpStatusCode status = HttpStatusCode.OK) => new(status) { Content = new StringContent(value.ToJsonString(), Encoding.UTF8, "application/json") };
    }

    private sealed class UnknownLengthContent : HttpContent
    {
        private readonly string _value;
        public UnknownLengthContent(string value) { _value = value; Headers.ContentType = new("application/json"); }
        protected override bool TryComputeLength(out long length) { length = 0; return false; }
        protected override Task SerializeToStreamAsync(Stream stream, TransportContext? context) => stream.WriteAsync(Encoding.UTF8.GetBytes(_value)).AsTask();
    }

    private sealed class BlockedContent : HttpContent
    {
        protected override bool TryComputeLength(out long length) { length = 0; return false; }
        protected override Task SerializeToStreamAsync(Stream stream, TransportContext? context) => Task.CompletedTask;
        protected override Task<Stream> CreateContentReadStreamAsync() => Task.FromResult<Stream>(new BlockedStream());
    }

    private sealed class BlockedStream : MemoryStream
    {
        public override async ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default)
        {
            await Task.Delay(Timeout.Infinite, cancellationToken);
            return 0;
        }
    }

    [Theory]
    [InlineData(false, false, false)]
    [InlineData(false, false, true)]
    [InlineData(false, true, false)]
    [InlineData(false, true, true)]
    [InlineData(true, false, false)]
    [InlineData(true, false, true)]
    [InlineData(true, true, false)]
    [InlineData(true, true, true)]
    public async Task CapabilitiesReportConfiguredModes(bool aiEnabled, bool mcpEnabled, bool ragEnabled)
    {
        var settings = new Dictionary<string, string?>
        {
            ["AI_ENABLED"] = aiEnabled ? "true" : "false",
            ["MCP_ENABLED"] = mcpEnabled ? "true" : "false",
            ["RAG_ENABLED"] = ragEnabled ? "true" : "false"
        };
        using var factory = CreateFactory(new FakeDatabase(), new FakeAdvice(), settings);
        using var client = factory.CreateClient();

        var response = await client.GetFromJsonAsync<CapabilitiesResponse>("/api/capabilities");

        Assert.Equal(new CapabilitiesResponse(aiEnabled, mcpEnabled, ragEnabled), response);
    }

    [Fact]
    public async Task CapabilitiesUseDocumentedDefaultsWhenFlagsAreMissing()
    {
        var settings = new Dictionary<string, string?>
        {
            ["AI_ENABLED"] = null,
            ["MCP_ENABLED"] = null,
            ["RAG_ENABLED"] = null
        };
        using var factory = CreateFactory(new FakeDatabase(), new FakeAdvice(), settings);
        using var client = factory.CreateClient();

        var response = await client.GetFromJsonAsync<CapabilitiesResponse>("/api/capabilities");

        Assert.Equal(new CapabilitiesResponse(true, false, false), response);
    }

    [Theory]
    [InlineData("AI_ENABLED")]
    [InlineData("MCP_ENABLED")]
    [InlineData("RAG_ENABLED")]
    public void InvalidModeFlagFailsApplicationStartup(string name)
    {
        var settings = new Dictionary<string, string?> { [name] = "True" };
        using var factory = CreateFactory(new FakeDatabase(), new FakeAdvice(), settings);

        var exception = Assert.ThrowsAny<Exception>(() => factory.CreateClient());

        Assert.Contains(name, exception.ToString(), StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("AI_ENABLED", "true", true)]
    [InlineData("AI_ENABLED", "false", false)]
    [InlineData("MCP_ENABLED", "true", true)]
    [InlineData("MCP_ENABLED", "false", false)]
    [InlineData("RAG_ENABLED", "true", true)]
    [InlineData("RAG_ENABLED", "false", false)]
    public void ModeFlagsAcceptOnlyExactBooleanSpellings(string name, string value, bool expected)
    {
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?> { [name] = value })
            .Build();

        var settings = FeatureModeSettings.FromConfiguration(configuration);

        Assert.Equal(expected, name switch
        {
            "AI_ENABLED" => settings.AiEnabled,
            "MCP_ENABLED" => settings.McpEnabled,
            _ => settings.RagEnabled
        });
    }

    [Theory]
    [InlineData("AI_ENABLED", "TRUE")]
    [InlineData("AI_ENABLED", "False")]
    [InlineData("AI_ENABLED", " true")]
    [InlineData("AI_ENABLED", "false ")]
    [InlineData("AI_ENABLED", "1")]
    [InlineData("AI_ENABLED", "")]
    [InlineData("MCP_ENABLED", "TRUE")]
    [InlineData("MCP_ENABLED", "False")]
    [InlineData("MCP_ENABLED", " true")]
    [InlineData("MCP_ENABLED", "false ")]
    [InlineData("MCP_ENABLED", "1")]
    [InlineData("MCP_ENABLED", "")]
    [InlineData("RAG_ENABLED", "TRUE")]
    [InlineData("RAG_ENABLED", "False")]
    [InlineData("RAG_ENABLED", " true")]
    [InlineData("RAG_ENABLED", "false ")]
    [InlineData("RAG_ENABLED", "1")]
    [InlineData("RAG_ENABLED", "")]
    public void ModeFlagsRejectNonCanonicalValues(string name, string value)
    {
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?> { [name] = value })
            .Build();

        Assert.Throws<InvalidOperationException>(() => FeatureModeSettings.FromConfiguration(configuration));
    }

    [Fact]
    public void McpEndpointUsesTheComposeConfigurationKey()
    {
        var configuration = new Dictionary<string, string?>
        {
            ["MCP_SERVER_URL"] = "http://host.docker.internal:5400/mcp"
        };
        using var factory = CreateFactory(new FakeDatabase(), new FakeAdvice(), configuration);

        var settings = factory.Services.GetRequiredService<McpBudgetCheckSettings>();

        Assert.Equal(new Uri("http://host.docker.internal:5400/mcp"), settings.Endpoint);
    }

    [Fact]
    public async Task ValidationHappensBeforeDatabaseCalls()
    {
        var database = new FakeDatabase();
        using var client = CreateClient(database, new FakeAdvice());

        var response = await client.PostAsJsonAsync("/api/budgets", new BudgetWriteRequest(" ", "bad", 0, "JPY", new(2026, 9, 2), new(2026, 9, 1)));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, database.CallCount);
        Assert.Equal("validation_error", (await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>())!.Error.Code);
    }

    [Fact]
    public async Task OmittedDatesAreRejectedBeforeDatabaseCalls()
    {
        var database = new FakeDatabase();
        using var client = CreateClient(database, new FakeAdvice());

        var budget = await client.PostAsJsonAsync("/api/budgets", new
        {
            journeyLabel = "Missing Dates",
            category = "food",
            limitAmountMinor = 1000,
            baseCurrency = "AUD"
        });
        var expense = await client.PostAsJsonAsync("/api/expenses", new
        {
            budgetId = 1,
            description = "Missing date",
            originalAmountMinor = 100,
            originalCurrency = "AUD"
        });

        Assert.Equal(HttpStatusCode.BadRequest, budget.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, expense.StatusCode);
        Assert.Equal(0, database.CallCount);
    }

    [Fact]
    public async Task BudgetCrudMapsThroughDatabaseBoundary()
    {
        var database = new FakeDatabase();
        using var client = CreateClient(database, new FakeAdvice());
        var request = new BudgetWriteRequest(" New Journey ", "FOOD", 20000, "aud", new(2026, 9, 1), new(2026, 9, 7));

        var create = await client.PostAsJsonAsync("/api/budgets", request);
        Assert.Equal(HttpStatusCode.Created, create.StatusCode);
        var budget = await create.Content.ReadFromJsonAsync<BudgetResponse>();
        Assert.Equal("New Journey", budget!.JourneyLabel);
        Assert.Equal("food", budget.Category);
        Assert.NotNull(await client.GetFromJsonAsync<BudgetResponse>($"/api/budgets/{budget.Id}"));
        Assert.Equal(HttpStatusCode.NoContent, (await client.DeleteAsync($"/api/budgets/{budget.Id}")).StatusCode);
    }

    [Fact]
    public async Task ExpenseSaveRecomputesAndReturnsConversionSnapshot()
    {
        var database = FakeDatabase.WithJourney();
        using var client = CreateClient(database, new FakeAdvice());

        var response = await client.PostAsJsonAsync("/api/expenses", new ExpenseWriteRequest(1, " Lunch ", 101, "usd", new(2026, 9, 2), null));

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        var expense = await response.Content.ReadFromJsonAsync<ExpenseResponse>();
        Assert.Equal(155, expense!.ConvertedAmountMinor);
        Assert.Equal(153846154, expense.ConversionRateScaled);
        Assert.Equal("AUD", expense.BaseCurrency);
        Assert.Equal(155, database.LastExpenseRequest!.ConvertedAmountMinor);
    }

    [Fact]
    public async Task ClientSuppliedConvertedAmountIsRejected()
    {
        var database = FakeDatabase.WithJourney();
        using var client = CreateClient(database, new FakeAdvice());
        var response = await client.PostAsJsonAsync("/api/expenses", new { budgetId = 1, description = "Lunch", originalAmountMinor = 100, originalCurrency = "AUD", convertedAmountMinor = 1, spentOn = "2026-09-02" });
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Null(database.LastExpenseRequest);
    }

    [Fact]
    public async Task DashboardAndAdviceUseDeterministicData()
    {
        var database = FakeDatabase.WithJourney(actual: 9000);
        var advice = new FakeAdvice();
        using var client = CreateClient(database, advice);

        var dashboard = await client.GetFromJsonAsync<DashboardResponse>("/api/dashboard?journeyLabel=Journey");
        var result = await (await client.PostAsJsonAsync("/api/insights", new InsightRequest("Journey"))).Content.ReadFromJsonAsync<AdviceResponse>();

        Assert.Equal(90, dashboard!.PercentageUsed);
        Assert.Equal("warning", dashboard.Categories.Single().Status);
        Assert.Equal("ai", result!.Source);
        Assert.Equal(1, advice.CallCount);
    }

    [Fact]
    public async Task BudgetCheckCallsOnlyTheFixedToolAndReturnsValidatedSummary()
    {
        var mcp = new FakeBudgetCheck(ValidBudgetSummary());
        using var client = CreateBudgetCheckClient(mcp);

        using var response = await client.PostAsJsonAsync("/api/budget-check", new { journeyLabel = "  Journey  " });
        var body = await response.Content.ReadFromJsonAsync<BudgetCheckResponse>();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("Journey", mcp.JourneyLabel);
        Assert.Equal("budget.get_summary", body!.Tool);
        Assert.True(body.Result.Ok);
        Assert.Equal(1000, body.Result.Summary.PlannedAmountMinor);
        Assert.Equal(1, mcp.CallCount);
    }

    [Fact]
    public async Task DisabledBudgetCheckDoesNotConnectToMcp()
    {
        var mcp = new FakeBudgetCheck(ValidBudgetSummary());
        using var client = CreateBudgetCheckClient(mcp, mcpEnabled: false);

        using var response = await client.PostAsJsonAsync("/api/budget-check", new { journeyLabel = "Journey" });
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        Assert.Equal("feature_disabled", error!.Error.Code);
        Assert.Equal(0, mcp.CallCount);
    }

    [Theory]
    [InlineData("{}")]
    [InlineData("{\"journeyLabel\":\"Journey\",\"url\":\"http://elsewhere\"}")]
    [InlineData("{\"journeyLabel\":\"Journey\",\"journeyLabel\":\"Other\"}")]
    [InlineData("{\"journeyLabel\":42}")]
    [InlineData("{\"journeyLabel\":\"   \"}")]
    [InlineData("{\"JourneyLabel\":\"Journey\"}")]
    public async Task BudgetCheckRejectsInvalidJsonContractsBeforeMcp(string json)
    {
        var mcp = new FakeBudgetCheck(ValidBudgetSummary());
        using var client = CreateBudgetCheckClient(mcp);

        using var response = await client.PostAsync("/api/budget-check", new StringContent(json, Encoding.UTF8, "application/json"));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, mcp.CallCount);
    }

    [Fact]
    public async Task BudgetCheckRejectsOversizedRequestBeforeMcp()
    {
        var mcp = new FakeBudgetCheck(ValidBudgetSummary());
        using var client = CreateBudgetCheckClient(mcp);
        var json = "{\"journeyLabel\":\"" + new string('x', 8193) + "\"}";

        using var response = await client.PostAsync("/api/budget-check", new StringContent(json, Encoding.UTF8, "application/json"));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, mcp.CallCount);
    }

    [Theory]
    [InlineData(HttpStatusCode.BadRequest, "validation_error")]
    [InlineData(HttpStatusCode.NotFound, "journey_not_found")]
    [InlineData(HttpStatusCode.ServiceUnavailable, "dependency_unavailable")]
    [InlineData(HttpStatusCode.GatewayTimeout, "dependency_timeout")]
    [InlineData(HttpStatusCode.BadGateway, "dependency_response_invalid")]
    public async Task BudgetCheckMapsStableMcpFailures(HttpStatusCode status, string expectedCode)
    {
        var mcp = new FakeBudgetCheck(ValidBudgetSummary()) { Failure = new BudgetCheckFailureException((int)status, expectedCode, "safe message") };
        using var client = CreateBudgetCheckClient(mcp);

        using var response = await client.PostAsJsonAsync("/api/budget-check", new { journeyLabel = "Journey" });
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(status, response.StatusCode);
        Assert.Equal(expectedCode, error!.Error.Code);
        Assert.Equal("safe message", error.Error.Message);
    }

    [Theory]
    [InlineData("\"JPY\"", "baseCurrency")]
    [InlineData("\"Other\"", "journeyLabel")]
    [InlineData("true", "plannedAmountMinor")]
    [InlineData("9007199254740992", "plannedAmountMinor")]
    [InlineData("1001", "remainingAmountMinor")]
    [InlineData("\"secret\"", "unexpected")]
    public async Task BudgetCheckRejectsMalformedOrUnsafeSummaries(string replacement, string field)
    {
        var summary = ValidBudgetSummary();
        using var document = JsonDocument.Parse(summary);
        var body = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(document.RootElement.GetRawText())!;
        body[field] = JsonDocument.Parse(replacement).RootElement.Clone();
        var mcp = new FakeBudgetCheck(JsonSerializer.Serialize(body));
        using var client = CreateBudgetCheckClient(mcp);

        using var response = await client.PostAsJsonAsync("/api/budget-check", new { journeyLabel = "Journey" });
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
        Assert.Equal(field == "plannedAmountMinor" && replacement == "9007199254740992" ? "summary_out_of_display_range" : "dependency_response_invalid", error!.Error.Code);
    }

    [Fact]
    public async Task BudgetCheckAcceptsSafeIntegerBoundaryAndNegativeRemainder()
    {
        const long safeMax = 9_007_199_254_740_991;
        var safeSummary = JsonSerializer.Serialize(new
        {
            journeyLabel = "Journey",
            baseCurrency = "AUD",
            plannedAmountMinor = safeMax,
            actualAmountMinor = 0,
            remainingAmountMinor = safeMax,
            percentageUsed = 0m,
            categories = new[] { new { category = "food", plannedAmountMinor = safeMax, actualAmountMinor = 0L, remainingAmountMinor = safeMax, percentageUsed = 0m, status = "within_budget" } }
        });
        var safeMcp = new FakeBudgetCheck(safeSummary);
        using var safeClient = CreateBudgetCheckClient(safeMcp);
        using var safeResponse = await safeClient.PostAsJsonAsync("/api/budget-check", new { journeyLabel = "Journey" });
        Assert.Equal(HttpStatusCode.OK, safeResponse.StatusCode);

        var overspentMcp = new FakeBudgetCheck(ValidBudgetSummary(planned: 1000, actual: 1001));
        using var overspentClient = CreateBudgetCheckClient(overspentMcp);
        using var overspentResponse = await overspentClient.PostAsJsonAsync("/api/budget-check", new { journeyLabel = "Journey" });
        var overspent = await overspentResponse.Content.ReadFromJsonAsync<BudgetCheckResponse>();
        Assert.Equal(HttpStatusCode.OK, overspentResponse.StatusCode);
        Assert.Equal(-1, overspent!.Result.Summary.RemainingAmountMinor);
        Assert.Equal("overspent", overspent.Result.Summary.Categories.Single().Status);
    }

    [Theory]
    [InlineData("duplicate")]
    [InlineData("unsupported")]
    [InlineData("incorrect-status")]
    public async Task BudgetCheckRejectsInvalidCategorySummaries(string mutation)
    {
        var summary = JsonNode.Parse(ValidBudgetSummary())!.AsObject();
        var categories = summary["categories"]!.AsArray();
        if (mutation == "duplicate") categories.Add(categories[0]!.DeepClone());
        if (mutation == "unsupported") categories[0]!["category"] = "medical";
        if (mutation == "incorrect-status") categories[0]!["status"] = "overspent";
        var mcp = new FakeBudgetCheck(summary.ToJsonString());
        using var client = CreateBudgetCheckClient(mcp);

        using var response = await client.PostAsJsonAsync("/api/budget-check", new { journeyLabel = "Journey" });
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
        Assert.Equal("dependency_response_invalid", error!.Error.Code);
    }

    [Fact]
    public async Task BudgetGuidanceReturnsValidatedCitationsFromTheStudent4Feature()
    {
        var rag = new FakeRag(GuidanceAnswer());
        using var client = CreateBudgetGuidanceClient(rag);

        using var response = await client.PostAsJsonAsync("/api/budget-guidance", new { question = "  How are category limits used?  " });
        var body = await response.Content.ReadFromJsonAsync<BudgetGuidanceResponse>();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("How are category limits used?", rag.Question);
        Assert.Equal("Budget status is based on actual spending. [category-budgets#1]", body!.Answer);
        Assert.Equal("high", body.Confidence);
        Assert.Equal("Category budgets and spending statuses", body.Citations.Single().Source);
        Assert.Equal("category-budgets#1", body.Citations.Single().ChunkId);
        Assert.Equal(0.45, body.Citations.Single().Score);
        Assert.Equal(1, rag.CallCount);
    }

    [Fact]
    public async Task BudgetGuidancePreservesTheExactStrictInsufficientResponse()
    {
        var rag = new FakeRag("""{"answer":"Not enough information in the knowledge base to answer this.","citations":[],"confidence":"insufficient"}""");
        using var client = CreateBudgetGuidanceClient(rag);

        using var response = await client.PostAsJsonAsync("/api/budget-guidance", new { question = "What is the current balance?" });
        var body = await response.Content.ReadFromJsonAsync<BudgetGuidanceResponse>();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("Not enough information in the knowledge base to answer this.", body!.Answer);
        Assert.Empty(body.Citations);
        Assert.Equal("insufficient", body.Confidence);
    }

    [Theory]
    [InlineData(0.3, "low")]
    [InlineData(0.4, "medium")]
    [InlineData(0.4, "high")]
    public async Task BudgetGuidanceAcceptsConfidenceConsistentWithRoundedBoundaryScore(double score, string confidence)
    {
        var json = JsonNode.Parse(GuidanceAnswer())!.AsObject();
        json["citations"]![0]!["score"] = score;
        json["confidence"] = confidence;
        var rag = new FakeRag(json.ToJsonString());
        using var client = CreateBudgetGuidanceClient(rag);

        using var response = await client.PostAsJsonAsync("/api/budget-guidance", new { question = "budget status" });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Theory]
    [InlineData("{}")]
    [InlineData("{\"question\":\"budget\",\"feature\":\"student-1\"}")]
    [InlineData("{\"question\":\"budget\",\"question\":\"other\"}")]
    [InlineData("{\"question\":42}")]
    [InlineData("{\"question\":\"   \"}")]
    [InlineData("{\"Question\":\"budget\"}")]
    public async Task BudgetGuidanceRejectsInvalidRequestsBeforeRag(string json)
    {
        var rag = new FakeRag(GuidanceAnswer());
        using var client = CreateBudgetGuidanceClient(rag);

        using var response = await client.PostAsync("/api/budget-guidance", new StringContent(json, Encoding.UTF8, "application/json"));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, rag.CallCount);
    }

    [Theory]
    [InlineData(1001)]
    [InlineData(8193)]
    public async Task BudgetGuidanceRejectsOversizedQuestionOrBodyBeforeRag(int length)
    {
        var rag = new FakeRag(GuidanceAnswer());
        using var client = CreateBudgetGuidanceClient(rag);
        var json = "{\"question\":\"" + new string('x', length) + "\"}";

        using var response = await client.PostAsync("/api/budget-guidance", new StringContent(json, Encoding.UTF8, "application/json"));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, rag.CallCount);
    }

    [Fact]
    public async Task DisabledBudgetGuidanceDoesNotCallRag()
    {
        var rag = new FakeRag(GuidanceAnswer());
        using var client = CreateBudgetGuidanceClient(rag, ragEnabled: false);

        using var response = await client.PostAsync("/api/budget-guidance", new StringContent("{}", Encoding.UTF8, "application/json"));
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        Assert.Equal("feature_disabled", error!.Error.Code);
        Assert.Equal(0, rag.CallCount);
    }

    [Theory]
    [InlineData("\"foreign#1\"", "Category budgets and spending statuses", "0.45", "high", "[foreign#1]")]
    [InlineData("\"category-budgets#1\"", "Other feature source", "0.45", "high", "[category-budgets#1]")]
    [InlineData("\"category-budgets#1\"", "Category budgets and spending statuses", "1.1", "high", "[category-budgets#1]")]
    [InlineData("\"category-budgets#1\"", "Category budgets and spending statuses", "0.45", "low", "[category-budgets#1]")]
    [InlineData("\"category-budgets#1\"", "Category budgets and spending statuses", "0.45", "high", "[other#1]")]
    public async Task BudgetGuidanceRejectsForeignOrMismatchedCitations(string chunkId, string source, string score, string confidence, string marker)
    {
        var json = $"{{\"answer\":\"Claim {marker}\",\"citations\":[{{\"source\":\"{source}\",\"chunk_id\":{chunkId},\"snippet\":\"A bounded source snippet.\",\"score\":{score}}}],\"confidence\":\"{confidence}\"}}";
        var rag = new FakeRag(json);
        using var client = CreateBudgetGuidanceClient(rag);

        using var response = await client.PostAsJsonAsync("/api/budget-guidance", new { question = "budget status" });
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
        Assert.Equal("dependency_response_invalid", error!.Error.Code);
    }

    [Fact]
    public async Task BudgetGuidanceRejectsDuplicateCitationIdsAndUnusableAbstention()
    {
        var duplicate = """{"answer":"One. [category-budgets#1]","citations":[{"source":"Category budgets and spending statuses","chunk_id":"category-budgets#1","snippet":"First.","score":0.45},{"source":"Category budgets and spending statuses","chunk_id":"category-budgets#1","snippet":"Second.","score":0.45}],"confidence":"high"}""";
        var invalidRefusal = """{"answer":"Not enough information in the knowledge base to answer this.","citations":[{"source":"Category budgets and spending statuses","chunk_id":"category-budgets#1","snippet":"A snippet.","score":0.45}],"confidence":"insufficient"}""";
        foreach (var json in new[] { duplicate, invalidRefusal })
        {
            var rag = new FakeRag(json);
            using var client = CreateBudgetGuidanceClient(rag);
            using var response = await client.PostAsJsonAsync("/api/budget-guidance", new { question = "budget" });
            Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
        }
    }

    [Theory]
    [InlineData(503, "dependency_unavailable")]
    [InlineData(504, "dependency_timeout")]
    [InlineData(502, "dependency_response_invalid")]
    public async Task BudgetGuidanceMapsRagFailuresToStableErrors(int statusCode, string code)
    {
        var rag = new FakeRag(GuidanceAnswer()) { Failure = new RagFailureException(statusCode, code, "safe message") };
        using var client = CreateBudgetGuidanceClient(rag);

        using var response = await client.PostAsJsonAsync("/api/budget-guidance", new { question = "budget" });
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal((HttpStatusCode)statusCode, response.StatusCode);
        Assert.Equal(code, error!.Error.Code);
        Assert.Equal("safe message", error.Error.Message);
    }

    private static string GuidanceAnswer() =>
        """{"answer":"Budget status is based on actual spending. [category-budgets#1]","citations":[{"source":"Category budgets and spending statuses","chunk_id":"category-budgets#1","snippet":"Set a positive limit for each budget category.","score":0.45}],"confidence":"high"}""";

    private static HttpClient CreateBudgetGuidanceClient(FakeRag rag, bool ragEnabled = true)
    {
        var factory = CreateFactory(new FakeDatabase(), new FakeAdvice(), new Dictionary<string, string?>
        {
            ["RAG_ENABLED"] = ragEnabled ? "true" : "false"
        }).WithWebHostBuilder(builder => builder.ConfigureTestServices(services =>
        {
            services.RemoveAll<IRagClient>();
            services.AddSingleton<IRagClient>(rag);
        }));
        return factory.CreateClient();
    }

    private sealed class FakeRag(string json) : IRagClient
    {
        public int CallCount { get; private set; }
        public string? Question { get; private set; }
        public RagFailureException? Failure { get; init; }

        public Task<JsonElement> AskAsync(string question, CancellationToken cancellationToken)
        {
            CallCount++;
            Question = question;
            if (Failure is not null) throw Failure;
            return Task.FromResult(JsonDocument.Parse(json).RootElement.Clone());
        }
    }

    private static HttpClient CreateBudgetCheckClient(FakeBudgetCheck mcp, bool mcpEnabled = true)
    {
        var factory = CreateFactory(new FakeDatabase(), new FakeAdvice(), new Dictionary<string, string?>
        {
            ["MCP_ENABLED"] = mcpEnabled ? "true" : "false"
        }).WithWebHostBuilder(builder => builder.ConfigureTestServices(services =>
        {
            services.RemoveAll<IMcpBudgetCheckClient>();
            services.AddSingleton<IMcpBudgetCheckClient>(mcp);
        }));
        return factory.CreateClient();
    }

    private static string ValidBudgetSummary(long planned = 1000, long actual = 800)
    {
        var remaining = planned - actual;
        var percentage = Math.Round(actual * 100m / planned, 2, MidpointRounding.AwayFromZero);
        var status = actual > planned ? "overspent" : actual * 100m / planned >= 80m ? "warning" : "within_budget";
        return JsonSerializer.Serialize(new
        {
            journeyLabel = "Journey",
            baseCurrency = "AUD",
            plannedAmountMinor = planned,
            actualAmountMinor = actual,
            remainingAmountMinor = remaining,
            percentageUsed = percentage,
            categories = new[] { new { category = "food", plannedAmountMinor = planned, actualAmountMinor = actual, remainingAmountMinor = remaining, percentageUsed = percentage, status } }
        });
    }

    private sealed class FakeBudgetCheck(string json) : IMcpBudgetCheckClient
    {
        public int CallCount { get; private set; }
        public string? JourneyLabel { get; private set; }
        public BudgetCheckFailureException? Failure { get; init; }

        public Task<JsonElement> CallAsync(string journeyLabel, CancellationToken cancellationToken)
        {
            CallCount++;
            JourneyLabel = journeyLabel;
            if (Failure is not null) throw Failure;
            return Task.FromResult(JsonDocument.Parse(json).RootElement.Clone());
        }
    }

    [Fact]
    public async Task NoBudgetDataDoesNotCallOllamaAdvice()
    {
        var advice = new FakeAdvice();
        using var client = CreateClient(new FakeDatabase(), advice);
        var response = await client.PostAsJsonAsync("/api/insights", new InsightRequest("Missing"));
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, advice.CallCount);
    }

    [Fact]
    public async Task DatabaseUnavailableMapsToStable503()
    {
        using var client = CreateClient(new UnavailableDatabase(), new FakeAdvice());
        var response = await client.GetAsync("/api/budgets");
        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        Assert.Equal("database_unavailable", (await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>())!.Error.Code);
    }

    [Fact]
    public async Task InconsistentDashboardDataMapsToStable502()
    {
        using var client = CreateClient(FakeDatabase.WithInconsistentJourney(), new FakeAdvice());
        var response = await client.GetAsync("/api/dashboard?journeyLabel=Journey");
        Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
        Assert.Equal("database_response_invalid", (await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>())!.Error.Code);
    }

    private static HttpClient CreateClient(IDatabaseApiClient database, IAdviceService advice) => CreateFactory(database, advice).CreateClient();

    private static WebApplicationFactory<Program> CreateFactory(IDatabaseApiClient database, IAdviceService advice, IDictionary<string, string?>? configuration = null, HttpMessageHandler? multiAgentHandler = null)
    {
        return new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            if (configuration is not null)
            {
                builder.ConfigureAppConfiguration((_, config) => config.AddInMemoryCollection(configuration));
            }
            builder.ConfigureTestServices(services =>
            {
                services.RemoveAll<IDatabaseApiClient>();
                services.RemoveAll<IAdviceService>();
                services.RemoveAll<IExchangeRateProvider>();
                services.AddSingleton(database);
                services.AddSingleton(advice);
                if (multiAgentHandler is not null) services.AddHttpClient<MultiAgentClient>().ConfigurePrimaryHttpMessageHandler(() => multiAgentHandler);
                services.AddSingleton<IExchangeRateProvider>(new FixedExchangeRateProvider(new ExchangeRateSettings("test", new(2026, 8, 1), "Demo", new Dictionary<string, decimal> { ["AUD"] = 1m, ["USD"] = 0.65m, ["EUR"] = 0.6m, ["GBP"] = 0.51m, ["NZD"] = 1.08m, ["CAD"] = 0.89m, ["SGD"] = 0.86m })));
            });
        });
    }

    private sealed class FakeAdvice : IAdviceService
    {
        public int CallCount { get; private set; }
        public Task<AdviceResponse> GetAdviceAsync(DashboardResponse dashboard, CancellationToken cancellationToken) { CallCount++; return Task.FromResult(new AdviceResponse("Advice.", [new("food", "Track food.")], "ai")); }
    }

    private sealed record CapabilitiesResponse(bool AiEnabled, bool McpEnabled, bool RagEnabled);

    private sealed class FakeDatabase : IDatabaseApiClient
    {
        public readonly List<BudgetResponse> _budgets = [];
        public readonly List<ExpenseDataResponse> _expenses = [];
        public int CallCount { get; private set; }
        public int WriteCount { get; private set; }
        public ExpenseDataRequest? LastExpenseRequest { get; private set; }
        public static FakeDatabase WithJourney(long actual = 0)
        {
            var value = new FakeDatabase();
            value._budgets.Add(new(1, "Journey", "food", 10000, "AUD", new(2026, 9, 1), new(2026, 9, 7), DateTime.UtcNow, DateTime.UtcNow));
            if (actual > 0) value._expenses.Add(new(1, 1, "Meals", actual, "AUD", actual, 100000000, new(2026, 8, 1), new(2026, 9, 2), null, DateTime.UtcNow, DateTime.UtcNow));
            return value;
        }
        public static FakeDatabase WithInconsistentJourney()
        {
            var value = WithJourney();
            value._budgets.Add(new(2, "Journey", "transport", 10000, "USD", new(2026, 9, 1), new(2026, 9, 7), DateTime.UtcNow, DateTime.UtcNow));
            return value;
        }
        public Task<IReadOnlyList<BudgetResponse>> ListBudgetsAsync(string? journeyLabel, string? category, CancellationToken cancellationToken) { CallCount++; return Task.FromResult<IReadOnlyList<BudgetResponse>>(_budgets.Where(value => journeyLabel is null || value.JourneyLabel == journeyLabel).Where(value => category is null || value.Category == category).ToArray()); }
        public Task<BudgetResponse> GetBudgetAsync(int id, CancellationToken cancellationToken) { CallCount++; return Task.FromResult(_budgets.Single(value => value.Id == id)); }
        public Task<BudgetResponse> CreateBudgetAsync(BudgetWriteRequest request, CancellationToken cancellationToken) { CallCount++; WriteCount++; var value = new BudgetResponse(_budgets.Count + 1, request.JourneyLabel!, request.Category!, request.LimitAmountMinor, request.BaseCurrency!, request.StartDate!.Value, request.EndDate!.Value, DateTime.UtcNow, DateTime.UtcNow); _budgets.Add(value); return Task.FromResult(value); }
        public Task<BudgetResponse> UpdateBudgetAsync(int id, BudgetWriteRequest request, CancellationToken cancellationToken) { CallCount++; WriteCount++; return Task.FromResult(new BudgetResponse(id, request.JourneyLabel!, request.Category!, request.LimitAmountMinor, request.BaseCurrency!, request.StartDate!.Value, request.EndDate!.Value, DateTime.UtcNow, DateTime.UtcNow)); }
        public Task DeleteBudgetAsync(int id, CancellationToken cancellationToken) { CallCount++; WriteCount++; _budgets.RemoveAll(value => value.Id == id); return Task.CompletedTask; }
        public Task<IReadOnlyList<ExpenseDataResponse>> ListExpensesAsync(int? budgetId, string? journeyLabel, string? category, CancellationToken cancellationToken) { CallCount++; return Task.FromResult<IReadOnlyList<ExpenseDataResponse>>(_expenses.Where(value => budgetId is null || value.BudgetId == budgetId).ToArray()); }
        public Task<ExpenseDataResponse> GetExpenseAsync(int id, CancellationToken cancellationToken) { CallCount++; return Task.FromResult(_expenses.Single(value => value.Id == id)); }
        public Task<ExpenseDataResponse> CreateExpenseAsync(ExpenseDataRequest request, CancellationToken cancellationToken) { CallCount++; WriteCount++; LastExpenseRequest = request; var value = Data(_expenses.Count + 1, request); _expenses.Add(value); return Task.FromResult(value); }
        public Task<ExpenseDataResponse> UpdateExpenseAsync(int id, ExpenseDataRequest request, CancellationToken cancellationToken) { CallCount++; WriteCount++; LastExpenseRequest = request; return Task.FromResult(Data(id, request)); }
        public Task DeleteExpenseAsync(int id, CancellationToken cancellationToken) { CallCount++; WriteCount++; _expenses.RemoveAll(value => value.Id == id); return Task.CompletedTask; }
        private static ExpenseDataResponse Data(int id, ExpenseDataRequest request) => new(id, request.BudgetId, request.Description, request.OriginalAmountMinor, request.OriginalCurrency, request.ConvertedAmountMinor, request.ConversionRateScaled, request.RateAsOf, request.SpentOn, request.Notes, DateTime.UtcNow, DateTime.UtcNow);
    }

    private sealed class UnavailableDatabase : IDatabaseApiClient
    {
        private static Task<T> Fail<T>() => Task.FromException<T>(new DatabaseUnavailableException());
        public Task<IReadOnlyList<BudgetResponse>> ListBudgetsAsync(string? journeyLabel, string? category, CancellationToken cancellationToken) => Fail<IReadOnlyList<BudgetResponse>>();
        public Task<BudgetResponse> GetBudgetAsync(int id, CancellationToken cancellationToken) => Fail<BudgetResponse>();
        public Task<BudgetResponse> CreateBudgetAsync(BudgetWriteRequest request, CancellationToken cancellationToken) => Fail<BudgetResponse>();
        public Task<BudgetResponse> UpdateBudgetAsync(int id, BudgetWriteRequest request, CancellationToken cancellationToken) => Fail<BudgetResponse>();
        public Task DeleteBudgetAsync(int id, CancellationToken cancellationToken) => Fail<object>();
        public Task<IReadOnlyList<ExpenseDataResponse>> ListExpensesAsync(int? budgetId, string? journeyLabel, string? category, CancellationToken cancellationToken) => Fail<IReadOnlyList<ExpenseDataResponse>>();
        public Task<ExpenseDataResponse> GetExpenseAsync(int id, CancellationToken cancellationToken) => Fail<ExpenseDataResponse>();
        public Task<ExpenseDataResponse> CreateExpenseAsync(ExpenseDataRequest request, CancellationToken cancellationToken) => Fail<ExpenseDataResponse>();
        public Task<ExpenseDataResponse> UpdateExpenseAsync(int id, ExpenseDataRequest request, CancellationToken cancellationToken) => Fail<ExpenseDataResponse>();
        public Task DeleteExpenseAsync(int id, CancellationToken cancellationToken) => Fail<object>();
    }
}
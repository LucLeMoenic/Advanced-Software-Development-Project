using AgenticLoop;
using System.Text.Json;
using System.Text.Json.Nodes;
using Xunit;

namespace AgenticLoop.Tests;

public sealed class AgenticLoopTests
{
    [Fact]
    public void ValidateRunInput_RejectsEqualModels()
    {
        var exception = Assert.Throws<LoopException>(() =>
            AgenticLoopApplication.ValidateRunInput(
                "Implement one change.",
                ["context.md"],
                "same-model",
                "same-model"));

        Assert.Contains("must be different", exception.Message);
    }

    [Fact]
    public void ValidateRunInput_RejectsAliasesForSameModel()
    {
        var exception = Assert.Throws<LoopException>(() =>
            AgenticLoopApplication.ValidateRunInput(
                "Implement one change.",
                ["context.md"],
                "same-model",
                "same-model:latest"));

        Assert.Contains("must be different", exception.Message);
    }

    [Fact]
    public async Task LoadContextAsync_RejectsPathOutsideWorkspace()
    {
        var workspace = CreateTemporaryDirectory();
        try
        {
            var exception = await Assert.ThrowsAsync<LoopException>(() =>
                AgenticLoopApplication.LoadContextAsync(workspace, ["../outside.txt"]));

            Assert.Contains("escapes the workspace", exception.Message);
        }
        finally
        {
            Directory.Delete(workspace, true);
        }
    }

    [Fact]
    public async Task LoadContextAsync_RejectsSensitiveFile()
    {
        var workspace = CreateTemporaryDirectory();
        try
        {
            await File.WriteAllTextAsync(Path.Combine(workspace, ".env"), "TOKEN=secret");

            var exception = await Assert.ThrowsAsync<LoopException>(() =>
                AgenticLoopApplication.LoadContextAsync(workspace, [".env"]));

            Assert.Contains("Sensitive context path", exception.Message);
        }
        finally
        {
            Directory.Delete(workspace, true);
        }
    }

    [Fact]
    public async Task LoadContextAsync_LoadsAllowListedUtf8File()
    {
        var workspace = CreateTemporaryDirectory();
        try
        {
            await File.WriteAllTextAsync(Path.Combine(workspace, "context.md"), "requirement");

            var context = await AgenticLoopApplication.LoadContextAsync(
                workspace,
                ["context.md"]);

            Assert.Equal(["context.md"], context.Paths);
            Assert.Contains("requirement", context.Content);
        }
        finally
        {
            Directory.Delete(workspace, true);
        }
    }

    [Fact]
    public async Task LoadContextAsync_RejectsInvalidUtf8()
    {
        var workspace = CreateTemporaryDirectory();
        try
        {
            await File.WriteAllBytesAsync(
                Path.Combine(workspace, "context.md"),
                [0xC3, 0x28]);

            var exception = await Assert.ThrowsAsync<LoopException>(() =>
                AgenticLoopApplication.LoadContextAsync(workspace, ["context.md"]));

            Assert.Contains("not valid UTF-8", exception.Message);
        }
        finally
        {
            Directory.Delete(workspace, true);
        }
    }

    [Fact]
    public async Task LoadContextAsync_RejectsSecretLikeContentInAllowedFile()
    {
        var workspace = CreateTemporaryDirectory();
        try
        {
            await File.WriteAllTextAsync(
                Path.Combine(workspace, "context.md"),
                "api_key = \"actual-secret-value\"");

            var exception = await Assert.ThrowsAsync<LoopException>(() =>
                AgenticLoopApplication.LoadContextAsync(workspace, ["context.md"]));

            Assert.Contains("Secret-like context content", exception.Message);
        }
        finally
        {
            Directory.Delete(workspace, true);
        }
    }

    [Theory]
    [InlineData("TOKEN=actualSecretValue123")]
    [InlineData("const apiKey = \"actual-secret-value\";")]
    [InlineData("Authorization: Bearer abcdefghijklmnopqrstuvwxyz")]
    [InlineData("Server=db;Password=actual-secret-value;Database=app")]
    [InlineData("github_pat_abcdefghijklmnopqrstuvwxyz123456")]
    public async Task LoadContextAsync_RejectsCommonCredentialContent(string content)
    {
        var workspace = CreateTemporaryDirectory();
        try
        {
            await File.WriteAllTextAsync(Path.Combine(workspace, "context.md"), content);

            await Assert.ThrowsAsync<LoopException>(() =>
                AgenticLoopApplication.LoadContextAsync(workspace, ["context.md"]));
        }
        finally
        {
            Directory.Delete(workspace, true);
        }
    }

    [Fact]
    public async Task LoadContextAsync_AllowsCredentialPlaceholders()
    {
        var workspace = CreateTemporaryDirectory();
        try
        {
            await File.WriteAllTextAsync(
                Path.Combine(workspace, "context.md"),
                "API_KEY=<redacted>");

            var context = await AgenticLoopApplication.LoadContextAsync(
                workspace,
                ["context.md"]);

            Assert.Contains("API_KEY=<redacted>", context.Content);
        }
        finally
        {
            Directory.Delete(workspace, true);
        }
    }

    [Fact]
    public async Task LoadContextAsync_RejectsSensitiveSymbolicLinkTarget()
    {
        var workspace = CreateTemporaryDirectory();
        try
        {
            var target = Path.Combine(workspace, ".env");
            var link = Path.Combine(workspace, "context.md");
            await File.WriteAllTextAsync(target, "TOKEN=actualSecretValue123");
            File.CreateSymbolicLink(link, target);

            var exception = await Assert.ThrowsAsync<LoopException>(() =>
                AgenticLoopApplication.LoadContextAsync(workspace, ["context.md"]));

            Assert.Contains("Sensitive context path", exception.Message);
        }
        finally
        {
            Directory.Delete(workspace, true);
        }
    }

    [Fact]
    public async Task LoadContextAsync_RejectsBinaryOrDisallowedFile()
    {
        var workspace = CreateTemporaryDirectory();
        try
        {
            await File.WriteAllBytesAsync(
                Path.Combine(workspace, "binary.txt"),
                [65, 0, 66]);
            await File.WriteAllTextAsync(Path.Combine(workspace, "script.exe"), "not executable");

            var binaryException = await Assert.ThrowsAsync<LoopException>(() =>
                AgenticLoopApplication.LoadContextAsync(workspace, ["binary.txt"]));
            var typeException = await Assert.ThrowsAsync<LoopException>(() =>
                AgenticLoopApplication.LoadContextAsync(workspace, ["script.exe"]));

            Assert.Contains("Binary context", binaryException.Message);
            Assert.Contains("file type is not allowed", typeException.Message);
        }
        finally
        {
            Directory.Delete(workspace, true);
        }
    }

    [Theory]
    [InlineData("ACCEPT")]
    [InlineData("revise")]
    [InlineData("REJECT")]
    public void ParseVerdict_ReturnsStructuredVerdict(string verdict)
    {
        Assert.Equal(
            verdict.ToUpperInvariant(),
            AgenticLoopApplication.ParseVerdict(ReviewerResponse(verdict)));
    }

    [Fact]
    public void ParseVerdict_RejectsObserveSectionWithoutVerdict()
    {
        var exception = Assert.Throws<LoopException>(() =>
            AgenticLoopApplication.ParseVerdict("[OBSERVE]\nNo decision"));

        Assert.Contains("exactly one", exception.Message);
    }

    [Fact]
    public void ParseVerdict_RejectsTemplateEchoOrMultipleVerdicts()
    {
        var exception = Assert.Throws<LoopException>(() =>
            AgenticLoopApplication.ParseVerdict(
                "[OBSERVE]\nVerdict: ACCEPT | REVISE | REJECT\nVerdict: ACCEPT\nVerdict: REJECT"));

        Assert.Contains("exactly one", exception.Message);
    }

    [Fact]
    public void ParseVerdict_RejectsMissingReviewSections()
    {
        var exception = Assert.Throws<LoopException>(() =>
            AgenticLoopApplication.ParseVerdict(
                "[OBSERVE]\nVerdict: ACCEPT\nFindings:\n- None"));

        Assert.Contains("Validation gaps:", exception.Message);
    }

    [Fact]
    public void ParseVerdict_RejectsSectionsOutsideObserve()
    {
        var exception = Assert.Throws<LoopException>(() =>
            AgenticLoopApplication.ParseVerdict(
                """
                Findings:
                - None
                Validation gaps:
                - None
                Scope check:
                aligned
                [OBSERVE]
                Verdict: ACCEPT
                """));

        Assert.Contains("Findings:", exception.Message);
    }

    [Theory]
    [InlineData("- Severity: REQUIRED")]
    [InlineData("Severity: REQUIRED")]
    [InlineData("- Severity: REQUIRED because validation is missing")]
    public void ParseVerdict_RejectsAcceptWithRequiredFinding(string severityLine)
    {
        var review = ReviewerResponse("ACCEPT", includeRequiredFinding: true)
            .Replace("- Severity: REQUIRED", severityLine, StringComparison.Ordinal);

        var exception = Assert.Throws<LoopException>(() =>
            AgenticLoopApplication.ParseVerdict(review));

        Assert.Contains("cannot ACCEPT", exception.Message);
    }

    [Fact]
    public void ValidateImplementerOutput_RejectsMissingPlanOrAct()
    {
        var exception = Assert.Throws<LoopException>(() =>
            AgenticLoopApplication.ValidateImplementerOutput("[ACT]\nProposal"));

        Assert.Contains("exactly one [PLAN] and one [ACT]", exception.Message);
    }

    [Fact]
    public async Task ExecuteLoopAsync_UsesReviewerAndProducesOneRevision()
    {
        var client = new FakeModelClient(
            [
                ImplementerResponse("Initial proposal"),
                ReviewerResponse("REVISE"),
                ImplementerResponse("Corrected proposal", "Revision"),
                ReviewerResponse("ACCEPT")
            ]);
        var input = CreateExecutionInput();

        var record = await AgenticLoopApplication.ExecuteLoopAsync(input, client);

        Assert.Equal("REVISE", record.ReviewerVerdict);
        Assert.Equal("Corrected proposal", record.AdaptedProposal?.Split('\n').Last());
        Assert.Equal("ACCEPT", record.FinalReviewerVerdict);
        Assert.Equal("shared-implementer-v1", record.PromptVersions?.Implementer);
        Assert.Equal("shared-reviewer-v1", record.PromptVersions?.Reviewer);
        Assert.Equal("qwen-implementer:latest", record.Models.Implementer);
        Assert.Equal("llama-reviewer:latest", record.Models.Reviewer);
        Assert.Collection(
            client.Calls,
            call => Assert.Equal("qwen-implementer:latest", call.Model),
            call => Assert.Equal("llama-reviewer:latest", call.Model),
            call => Assert.Equal("qwen-implementer:latest", call.Model),
            call => Assert.Equal("llama-reviewer:latest", call.Model));
        Assert.Contains("Initial proposal", client.Calls[1].Prompt);
        Assert.Contains("Address the stated requirement", client.Calls[2].Prompt);
        Assert.Contains("Corrected proposal", client.Calls[3].Prompt);
    }

    [Fact]
    public async Task ExecuteLoopAsync_StopsWhenRequiredModelIsMissing()
    {
        var client = new FakeModelClient([], ["qwen-implementer:latest"]);

        var exception = await Assert.ThrowsAsync<LoopException>(() =>
            AgenticLoopApplication.ExecuteLoopAsync(CreateExecutionInput(), client));

        Assert.Contains("llama-reviewer", exception.Message);
        Assert.Empty(client.Calls);
    }

    [Fact]
    public async Task ExecuteLoopAsync_AcceptVerdictDoesNotGenerateRevision()
    {
        var client = new FakeModelClient(
            [
                ImplementerResponse("Proposal"),
                ReviewerResponse("ACCEPT")
            ]);

        var record = await AgenticLoopApplication.ExecuteLoopAsync(
            CreateExecutionInput(),
            client);

        Assert.Equal("ACCEPT", record.FinalReviewerVerdict);
        Assert.Null(record.AdaptedProposal);
        Assert.Null(record.AdaptedProposalReview);
        Assert.Equal(2, client.Calls.Count);
    }

    [Fact]
    public async Task FinaliseRecordAsync_StoresHumanDecisionAndPostTestOnce()
    {
        var directory = CreateTemporaryDirectory();
        try
        {
            var recordPath = Path.Combine(directory, "record.json");
            var record = await AgenticLoopApplication.ExecuteLoopAsync(
                CreateExecutionInput(),
                new FakeModelClient(
                    [
                        ImplementerResponse("Proposal"),
                        ReviewerResponse("ACCEPT")
                    ]));
            await File.WriteAllTextAsync(
                recordPath,
                System.Text.Json.JsonSerializer.Serialize(
                    record,
                    new System.Text.Json.JsonSerializerOptions(
                        System.Text.Json.JsonSerializerDefaults.Web)
                    {
                        WriteIndented = true
                    }));

            await AgenticLoopApplication.FinaliseRecordAsync(
                recordPath,
                "changed",
                "Applied the reviewed proposal.",
                "dotnet test",
                "All tests passed.");

            var json = await File.ReadAllTextAsync(recordPath);
            Assert.Contains("\"humanDecision\": \"changed\"", json);
            Assert.Contains("\"command\": \"dotnet test\"", json);
            await Assert.ThrowsAsync<LoopException>(() =>
                AgenticLoopApplication.FinaliseRecordAsync(
                    recordPath,
                    "kept",
                    "Duplicate finalisation.",
                    "dotnet test",
                    "Passed."));
        }
        finally
        {
            Directory.Delete(directory, true);
        }
    }

    [Fact]
    public async Task FinaliseRecordAsync_AcceptsSchemaOneRecordWithoutPromptVersions()
    {
        var directory = CreateTemporaryDirectory();
        try
        {
            var recordPath = Path.Combine(directory, "record.json");
            var record = await AgenticLoopApplication.ExecuteLoopAsync(
                CreateExecutionInput(),
                new FakeModelClient(
                    [
                        ImplementerResponse("Proposal"),
                        ReviewerResponse("ACCEPT")
                    ]));
            var json = JsonSerializer.SerializeToNode(
                record,
                new JsonSerializerOptions(JsonSerializerDefaults.Web))!.AsObject();
            json["schemaVersion"] = 1;
            json.Remove("promptVersions");
            await File.WriteAllTextAsync(recordPath, json.ToJsonString());

            await AgenticLoopApplication.FinaliseRecordAsync(
                recordPath,
                "kept",
                "Finalised a legacy pending record.",
                "dotnet test",
                "All tests passed.");

            var finalised = await File.ReadAllTextAsync(recordPath);
            Assert.Contains("\"schemaVersion\": 1", finalised);
            Assert.Contains("\"humanDecision\": \"kept\"", finalised);
        }
        finally
        {
            Directory.Delete(directory, true);
        }
    }

    private static LoopExecutionInput CreateExecutionInput()
    {
        return new LoopExecutionInput(
            "Implement one bounded change.",
            new LoadedContext(
                ["context.md"],
                new Dictionary<string, string> { ["context.md"] = "ABC123" },
                "FILE: context.md\nrequirement\nEND_FILE"),
            "qwen-implementer",
            "llama-reviewer",
            "/app/prompts/implementer.md",
            "/app/prompts/reviewer.md",
            "# Shared Implementer Prompt\n\nVersion: `shared-implementer-v1`",
            "# Shared Reviewer Prompt\n\nVersion: `shared-reviewer-v1`",
            "dotnet test",
            "All baseline tests passed.");
    }

    private static string ImplementerResponse(
        string proposedChange,
        string plan = "Implement the bounded change.")
    {
        return $"[PLAN]\n{plan}\n[ACT]\n{proposedChange}";
    }

    private static string ReviewerResponse(
        string verdict,
        bool includeRequiredFinding = false)
    {
        var findings = verdict.Equals("ACCEPT", StringComparison.OrdinalIgnoreCase)
            && !includeRequiredFinding
            ? "- None"
            : """
              - Severity: REQUIRED
                Evidence: context.md
                Failure mode: The proposal misses a requirement.
                Required correction: Address the stated requirement.
              """;

        return $"""
            [OBSERVE]
            Verdict: {verdict}

            Findings:
            {findings}

            Validation gaps:
            - None

            Scope check:
            aligned
            """;
    }

    private static string CreateTemporaryDirectory()
    {
        var path = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(path);
        return path;
    }

    private sealed class FakeModelClient : IModelClient
    {
        private readonly Queue<string> _responses;
        private readonly HashSet<string> _models;

        public FakeModelClient(
            IEnumerable<string> responses,
            IEnumerable<string>? models = null)
        {
            _responses = new Queue<string>(responses);
            _models = (models ?? ["qwen-implementer:latest", "llama-reviewer:latest"])
                .ToHashSet(StringComparer.Ordinal);
        }

        public List<ModelCall> Calls { get; } = [];

        public Task<HashSet<string>> GetAvailableModelsAsync()
        {
            return Task.FromResult(_models);
        }

        public Task<string> GetRuntimeVersionAsync()
        {
            return Task.FromResult("0.11.0-test");
        }

        public Task<string> GenerateAsync(string model, string prompt)
        {
            Calls.Add(new ModelCall(model, prompt));
            return Task.FromResult(_responses.Dequeue());
        }
    }

    private sealed record ModelCall(string Model, string Prompt);
}

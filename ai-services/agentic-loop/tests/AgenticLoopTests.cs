using AgenticLoop;
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
    [InlineData("[OBSERVE]\nVerdict: ACCEPT", "ACCEPT")]
    [InlineData("[OBSERVE]\nVerdict: revise", "REVISE")]
    [InlineData("[OBSERVE]\nVerdict: REJECT", "REJECT")]
    public void ParseVerdict_ReturnsStructuredVerdict(string review, string expected)
    {
        Assert.Equal(expected, AgenticLoopApplication.ParseVerdict(review));
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
    public async Task ExecuteLoopAsync_UsesReviewerAndProducesOneRevision()
    {
        var client = new FakeModelClient(
            [
                "[PLAN]\nPlan\n[ACT]\nInitial proposal",
                "[OBSERVE]\nVerdict: REVISE\nFindings:\n- Correct validation.",
                "[PLAN]\nRevision\n[ACT]\nCorrected proposal",
                "[OBSERVE]\nVerdict: ACCEPT\nFindings:\n- None"
            ]);
        var input = CreateExecutionInput();

        var record = await AgenticLoopApplication.ExecuteLoopAsync(input, client);

        Assert.Equal("REVISE", record.ReviewerVerdict);
        Assert.Equal("Corrected proposal", record.AdaptedProposal?.Split('\n').Last());
        Assert.Equal("ACCEPT", record.FinalReviewerVerdict);
        Assert.Collection(
            client.Calls,
            call => Assert.Equal("qwen-implementer", call.Model),
            call => Assert.Equal("llama-reviewer", call.Model),
            call => Assert.Equal("qwen-implementer", call.Model),
            call => Assert.Equal("llama-reviewer", call.Model));
        Assert.Contains("Initial proposal", client.Calls[1].Prompt);
        Assert.Contains("Correct validation", client.Calls[2].Prompt);
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
                "[PLAN]\nPlan\n[ACT]\nProposal",
                "[OBSERVE]\nVerdict: ACCEPT\nFindings:\n- None"
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
                        "[PLAN]\nPlan\n[ACT]\nProposal",
                        "[OBSERVE]\nVerdict: ACCEPT\nFindings:\n- None"
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
            "implementer prompt",
            "reviewer prompt",
            "dotnet test",
            "All baseline tests passed.");
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

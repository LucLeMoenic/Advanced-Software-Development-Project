using Xunit;

namespace AgenticLoop.Tests;

public sealed class ReportReviewTests
{
    [Theory]
    [InlineData("multi-agent")]
    [InlineData("testing")]
    [InlineData("cloud")]
    public async Task ReviewsOrdinaryEvidenceWithHashedModeInstructions(string mode)
    {
        var workspace = AgenticLoopApplication.ResolveWorkspace(null, AppContext.BaseDirectory);
        var report = "student-2/docs/release-2-runbook.md";
        var prompt = $"ai-services/agentic-loop/prompts/review-{mode}-v1.txt";
        var context = await AgenticLoopApplication.LoadReviewContextAsync(workspace, [report], mode);
        Assert.Equal(new[] { report, prompt }, context.Paths);
        Assert.Equal(2, context.Sha256ByPath.Count);
        Assert.Contains(await File.ReadAllTextAsync(Path.Combine(workspace, prompt)), context.Content);
        Assert.Contains("Pending", context.Content);
    }

    [Theory]
    [InlineData("missing.txt")]
    [InlineData("../outside.txt")]
    [InlineData(".env")]
    public async Task UsesExistingContextSafetyChecks(string path)
    {
        var workspace = AgenticLoopApplication.ResolveWorkspace(null, AppContext.BaseDirectory);
        await Assert.ThrowsAsync<LoopException>(() =>
            AgenticLoopApplication.LoadReviewContextAsync(workspace, [path], "testing"));
    }

    [Fact]
    public async Task RequiresEvidenceAndKnownMode()
    {
        var workspace = AgenticLoopApplication.ResolveWorkspace(null, AppContext.BaseDirectory);
        await Assert.ThrowsAsync<LoopException>(() =>
            AgenticLoopApplication.LoadReviewContextAsync(workspace, [], "cloud"));
        await Assert.ThrowsAsync<LoopException>(() =>
            AgenticLoopApplication.LoadReviewContextAsync(workspace, ["README.md"], "unknown"));
    }
}

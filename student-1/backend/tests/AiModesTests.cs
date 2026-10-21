using System.Net.Http.Json;
using Accommodation.Backend.Api;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;

namespace Accommodation.Backend.Tests;

public sealed class AiModesTests
{
    [Fact]
    public void ModesDefaultToDisabled()
    {
        using var factory = CreateFactory();

        var modes = factory.Services.GetRequiredService<AiModes>();

        Assert.False(modes.RankingEnabled);
        Assert.False(modes.LookupEnabled);
        Assert.False(modes.GuideEnabled);
        Assert.False(modes.MultiAgentEnabled);
    }

    [Fact]
    public async Task CapabilitiesReportEachConfiguredMode()
    {
        using var factory = CreateFactory(
            ("AI_ENABLED", "true"),
            ("MCP_ENABLED", "false"),
            ("RAG_ENABLED", "true"));
        using var client = factory.CreateClient();

        var body = await client.GetFromJsonAsync<Capabilities>("/api/capabilities");

        Assert.Equal(new Capabilities(AiRanking: true, Lookup: false, Guide: true, MultiAgent: false), body);
    }

    [Fact]
    public async Task ModesAreReadFromConfigurationAndReported()
    {
        using var factory = CreateFactory(
            ("AI_ENABLED", "true"),
            ("MCP_ENABLED", "true"),
            ("RAG_ENABLED", "false"));
        using var client = factory.CreateClient();

        var body = await client.GetFromJsonAsync<ServiceInformation>("/");

        Assert.NotNull(body);
        Assert.True(body.Modes.Ranking);
        Assert.True(body.Modes.Lookup);
        Assert.False(body.Modes.Guide);
    }

    [Theory]
    [InlineData("AI_ENABLED", "TRUE")]
    [InlineData("MCP_ENABLED", "True")]
    [InlineData("MCP_ENABLED", "yes")]
    [InlineData("RAG_ENABLED", "1")]
    [InlineData("MULTI_AGENT_ENABLED", "on")]
    [InlineData("RAG_ENABLED", "")]
    public void InvalidFlagStopsStartup(string name, string value)
    {
        using var factory = CreateFactory((name, value));

        var exception = Assert.ThrowsAny<Exception>(() => factory.CreateClient());

        Assert.Contains($"{name} must be true or false.", exception.ToString());
    }

    private static WebApplicationFactory<Program> CreateFactory(
        params (string Name, string Value)[] settings)
    {
        return new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            foreach (var (name, value) in settings)
            {
                builder.UseSetting(name, value);
            }
        });
    }

    private sealed record ServiceInformation(ModeInformation Modes);

    private sealed record ModeInformation(bool Ranking, bool Lookup, bool Guide, bool MultiAgent);

    private sealed record Capabilities(bool AiRanking, bool Lookup, bool Guide, bool MultiAgent);
}

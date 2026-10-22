using Accommodation.Backend.Clients;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace Accommodation.Backend.Tests;

public sealed class CloudDeadlineTests
{
    [Theory]
    [InlineData(false, 12, 60, 30)]
    [InlineData(true, 180, 180, 200)]
    public void CloudProfileExtendsOnlyModelAndRagDeadlines(bool slow, int ranking, int lookup, int rag)
    {
        using var factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
            builder.ConfigureAppConfiguration((_, config) => config.AddInMemoryCollection(
                new Dictionary<string, string?> { ["CLOUD_AI_SLOW_MODE"] = slow.ToString() })));
        var clients = factory.Services.GetRequiredService<IHttpClientFactory>();
        Assert.Equal(TimeSpan.FromSeconds(ranking), clients.CreateClient(nameof(IOllamaRankingClient)).Timeout);
        Assert.Equal(TimeSpan.FromSeconds(lookup), clients.CreateClient(nameof(ILookupArgumentExtractor)).Timeout);
        Assert.Equal(TimeSpan.FromSeconds(rag), factory.Services.GetRequiredService<RagSettings>().Deadline);
        Assert.Equal(TimeSpan.FromSeconds(3), clients.CreateClient(nameof(IDatabaseApiClient)).Timeout);
        Assert.Equal(TimeSpan.FromSeconds(10), clients.CreateClient(nameof(IMultiAgentClient)).Timeout);
    }
}

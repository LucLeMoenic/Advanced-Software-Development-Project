using BudgetTracker.Backend.Clients;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace BudgetTracker.Backend.Tests;

public sealed class CloudDeadlineTests
{
    [Theory]
    [InlineData(false, 15, 30)]
    [InlineData(true, 180, 200)]
    public void CloudProfileExtendsOnlyModelAndRagDeadlines(bool slow, int model, int rag)
    {
        using var factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
            builder.ConfigureAppConfiguration((_, config) => config.AddInMemoryCollection(
                new Dictionary<string, string?> { ["CLOUD_AI_SLOW_MODE"] = slow.ToString() })));
        var clients = factory.Services.GetRequiredService<IHttpClientFactory>();
        Assert.Equal(TimeSpan.FromSeconds(model), clients.CreateClient(nameof(IOllamaInsightsClient)).Timeout);
        Assert.Equal(TimeSpan.FromSeconds(rag), factory.Services.GetRequiredService<RagSettings>().Deadline);
        Assert.Equal(TimeSpan.FromSeconds(4), clients.CreateClient(nameof(IDatabaseApiClient)).Timeout);
    }
}

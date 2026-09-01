using System.Net;
using System.Net.Http.Json;

namespace Accommodation.Database.Tests;

public sealed class ServiceEndpointsTests : DatabaseApiTestBase
{
    [Fact]
    public async Task RootReturnsServiceInformation()
    {
        var response = await Client.GetAsync("/");
        var body = await response.Content.ReadFromJsonAsync<ServiceInformation>();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.NotNull(body);
        Assert.Equal("accommodation-database", body.Service);
        Assert.Equal("ready", body.Status);
        Assert.Equal("sqlite", body.Provider);
    }

    [Fact]
    public async Task HealthConfirmsSqliteConnectivity()
    {
        var response = await Client.GetAsync("/health");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("Healthy", await response.Content.ReadAsStringAsync());
    }

    private sealed record ServiceInformation(string Service, string Status, string Provider);
}

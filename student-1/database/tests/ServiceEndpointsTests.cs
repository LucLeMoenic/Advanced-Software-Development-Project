using System.Net;
using System.Net.Http.Json;
using Microsoft.Data.Sqlite;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;

namespace Student1.Database.Tests;

public sealed class ServiceEndpointsTests : IAsyncLifetime
{
    private readonly string _databasePath =
        Path.Combine(Path.GetTempPath(), $"student1-{Guid.NewGuid():N}.db");
    private WebApplicationFactory<Program>? _factory;
    private HttpClient? _client;

    public Task InitializeAsync()
    {
        _factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
            builder.UseSetting(
                "ConnectionStrings:AccommodationDatabase",
                $"Data Source={_databasePath}"));
        _client = _factory.CreateClient();
        return Task.CompletedTask;
    }

    [Fact]
    public async Task RootReturnsServiceInformation()
    {
        var response = await Client.GetAsync("/");
        var body = await response.Content.ReadFromJsonAsync<ServiceInformation>();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.NotNull(body);
        Assert.Equal("student1-database", body.Service);
        Assert.Equal("ready", body.Status);
        Assert.Equal("sqlite", body.Provider);
    }

    [Fact]
    public async Task HealthConfirmsSqliteConnectivity()
    {
        var response = await Client.GetAsync("/health");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("Healthy", await response.Content.ReadAsStringAsync());
        Assert.True(File.Exists(_databasePath));
    }

    public async Task DisposeAsync()
    {
        _client?.Dispose();
        if (_factory is not null)
        {
            await _factory.DisposeAsync();
        }

        SqliteConnection.ClearAllPools();
        File.Delete(_databasePath);
    }

    private HttpClient Client =>
        _client ?? throw new InvalidOperationException("The test client is not initialized.");

    private sealed record ServiceInformation(string Service, string Status, string Provider);
}

using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Data.Sqlite;

namespace Accommodation.Database.Tests;

public abstract class DatabaseApiTestBase : IAsyncLifetime
{
    private readonly string _databasePath =
        Path.Combine(Path.GetTempPath(), $"student1-{Guid.NewGuid():N}.db");
    private WebApplicationFactory<Program>? _factory;
    private HttpClient? _client;

    protected HttpClient Client =>
        _client ?? throw new InvalidOperationException("The test client is not initialized.");

    protected WebApplicationFactory<Program> Factory =>
        _factory ?? throw new InvalidOperationException("The test host is not initialized.");

    public Task InitializeAsync()
    {
        _factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
            builder.UseSetting(
                "ConnectionStrings:AccommodationDatabase",
                $"Data Source={_databasePath}"));
        _client = _factory.CreateClient();
        return Task.CompletedTask;
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
}

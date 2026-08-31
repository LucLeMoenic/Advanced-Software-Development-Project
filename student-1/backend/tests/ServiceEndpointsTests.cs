using System.Net;
using System.Net.Http.Json;
using Microsoft.AspNetCore.Mvc.Testing;

namespace Accommodation.Backend.Tests;

public sealed class ServiceEndpointsTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly HttpClient _client;

    public ServiceEndpointsTests(WebApplicationFactory<Program> factory)
    {
        _client = factory.CreateClient();
    }

    [Fact]
    public async Task RootReturnsServiceInformation()
    {
        var response = await _client.GetAsync("/");
        var body = await response.Content.ReadFromJsonAsync<ServiceInformation>();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.NotNull(body);
        Assert.Equal("accommodation-backend", body.Service);
        Assert.Equal("ready", body.Status);
        Assert.Equal("http://localhost:5301", body.Dependencies.Database);
        Assert.Equal("http://localhost:11434", body.Dependencies.Ollama);
    }

    [Fact]
    public async Task HealthReturnsHealthy()
    {
        var response = await _client.GetAsync("/health");
        var body = await response.Content.ReadFromJsonAsync<HealthResponse>();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.NotNull(body);
        Assert.Equal("healthy", body.Status);
        Assert.Equal("accommodation-backend", body.Service);
    }

    private sealed record ServiceInformation(
        string Service,
        string Status,
        DependencyInformation Dependencies);

    private sealed record DependencyInformation(string Database, string Ollama);

    private sealed record HealthResponse(string Status, string Service);
}

using Accommodation.Backend.Api;
using Accommodation.Backend.Clients;

var builder = WebApplication.CreateBuilder(args);
var databaseUrl = builder.Configuration["Services:DatabaseUrl"]
    ?? "http://localhost:5301";
var ollamaUrl = builder.Configuration["Services:OllamaUrl"]
    ?? "http://localhost:11434";
var applicationModel = builder.Configuration["APPLICATION_MODEL"]
    ?? "llama3.2:3b";
var rankingPrompt = File.ReadAllText(Path.Combine(
    builder.Environment.ContentRootPath,
    "Prompts",
    "accommodation-ranking-v1.txt"));

builder.Services.AddSingleton(TimeProvider.System);
builder.Services.AddSingleton(new OllamaRankingSettings(applicationModel, rankingPrompt));
builder.Services
    .AddHttpClient<IDatabaseApiClient, DatabaseApiClient>(client =>
    {
        client.BaseAddress = new Uri(databaseUrl);
        client.Timeout = TimeSpan.FromSeconds(3);
    });
builder.Services
    .AddHttpClient<IOllamaRankingClient, OllamaRankingClient>(client =>
    {
        client.BaseAddress = new Uri(ollamaUrl);
        client.Timeout = TimeSpan.FromSeconds(12);
    });

var app = builder.Build();

app.MapGet("/", () => Results.Ok(new
{
    service = "accommodation-backend",
    status = "ready",
    dependencies = new
    {
        database = databaseUrl,
        ollama = ollamaUrl
    }
}));

app.MapGet("/health", () => Results.Ok(new
{
    status = "healthy",
    service = "accommodation-backend"
}));

app.MapSearchEndpoints();

app.Run();

public partial class Program;

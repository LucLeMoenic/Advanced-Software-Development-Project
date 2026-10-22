using Accommodation.Backend.Api;
using Accommodation.Backend.Clients;

var builder = WebApplication.CreateBuilder(args);
var databaseUrl = builder.Configuration["Services:DatabaseUrl"]
    ?? "http://localhost:5301";
var ollamaUrl = builder.Configuration["Services:OllamaUrl"]
    ?? "http://localhost:11434";
var liteApiUrl = builder.Configuration["Services:LiteApiUrl"]
    ?? "https://api.liteapi.travel";
var liteApiKey = builder.Configuration["LITEAPI_KEY"] ?? string.Empty;
var applicationModel = builder.Configuration["APPLICATION_MODEL"]
    ?? "llama3.2:3b";
var aiModes = AiModes.FromConfiguration(builder.Configuration);
var mcpServerUrl = builder.Configuration["MCP_SERVER_URL"]
    ?? "http://localhost:5400/mcp";
var ragServerUrl = builder.Configuration["RAG_SERVER_URL"]
    ?? "http://localhost:5500";
var multiAgentServerUrl = builder.Configuration["MULTI_AGENT_SERVER_URL"]
    ?? "http://localhost:5600";
var lookupPrompt = File.ReadAllText(Path.Combine(
    builder.Environment.ContentRootPath,
    "Prompts",
    "assistant-lookup-v1.txt"));
var rankingPrompt = File.ReadAllText(Path.Combine(
    builder.Environment.ContentRootPath,
    "Prompts",
    "accommodation-ranking-v1.txt"));

builder.Services.AddSingleton(TimeProvider.System);
builder.Services.AddSingleton(aiModes);
builder.Services.AddSingleton(new OllamaRankingSettings(applicationModel, rankingPrompt));
builder.Services.AddSingleton(new LiteApiSettings(liteApiKey));
builder.Services.AddSingleton(new LookupExtractorSettings(applicationModel, lookupPrompt));
builder.Services.AddSingleton(new McpSettings(new Uri(mcpServerUrl)));
builder.Services.AddSingleton(services => new RagSettings(new Uri(ragServerUrl),
    TimeSpan.FromSeconds(services.GetRequiredService<IConfiguration>().GetValue("CLOUD_AI_SLOW_MODE", false) ? 200 : 30)));
builder.Services
    .AddHttpClient<IDatabaseApiClient, DatabaseApiClient>(client =>
    {
        client.BaseAddress = new Uri(databaseUrl);
        client.Timeout = TimeSpan.FromSeconds(3);
    });
builder.Services
    .AddHttpClient<IOllamaRankingClient, OllamaRankingClient>((services, client) =>
    {
        client.BaseAddress = new Uri(ollamaUrl);
        client.Timeout = TimeSpan.FromSeconds(services.GetRequiredService<IConfiguration>().GetValue("CLOUD_AI_SLOW_MODE", false) ? 180 : 12);
    });
builder.Services
    .AddHttpClient<ILookupArgumentExtractor, OllamaLookupExtractor>((services, client) =>
    {
        client.BaseAddress = new Uri(ollamaUrl);
        client.Timeout = TimeSpan.FromSeconds(services.GetRequiredService<IConfiguration>().GetValue("CLOUD_AI_SLOW_MODE", false) ? 180 : 60);
    });
// The MCP client enforces its own 5-second deadline for the whole session.
builder.Services.AddHttpClient<IMcpToolClient, McpToolClient>();
// The RAG client enforces its own deadline and 16000-byte response limit.
builder.Services.AddHttpClient<IRagClient, RagClient>(client => client.Timeout = Timeout.InfiniteTimeSpan);
builder.Services
    .AddHttpClient<ILiteApiClient, LiteApiClient>(client =>
    {
        client.BaseAddress = new Uri(liteApiUrl);
        client.Timeout = TimeSpan.FromSeconds(10);
    });
// Workflows run asynchronously on the server, so every call returns quickly (202 on start).
builder.Services
    .AddHttpClient<IMultiAgentClient, MultiAgentClient>(client =>
    {
        client.BaseAddress = new Uri(multiAgentServerUrl);
        client.Timeout = TimeSpan.FromSeconds(10);
    });

var app = builder.Build();

app.MapGet("/", () => Results.Ok(new
{
    service = "accommodation-backend",
    status = "ready",
    dependencies = new
    {
        database = databaseUrl,
        ollama = ollamaUrl,
        accommodationProvider = liteApiUrl
    },
    modes = new
    {
        ranking = aiModes.RankingEnabled,
        lookup = aiModes.LookupEnabled,
        guide = aiModes.GuideEnabled,
        multiAgent = aiModes.MultiAgentEnabled
    }
}));

// The frontend reads this through its /api/ proxy to show only the enabled AI options.
app.MapGet("/api/capabilities", () => Results.Ok(new
{
    aiRanking = aiModes.RankingEnabled,
    lookup = aiModes.LookupEnabled,
    guide = aiModes.GuideEnabled,
    multiAgent = aiModes.MultiAgentEnabled
}));

app.MapGet("/health", () => Results.Ok(new
{
    status = "healthy",
    service = "accommodation-backend"
}));

app.MapSearchEndpoints();
app.MapAssistantEndpoints();
app.MapAgentReviewEndpoints();

app.Run();

public partial class Program;

using System.Text.Json.Serialization;
using BudgetTracker.Backend.Api;
using BudgetTracker.Backend.Clients;
using BudgetTracker.Backend.Services;

var builder = WebApplication.CreateBuilder(args);
var databaseUrl = builder.Configuration["Services:DatabaseUrl"] ?? "http://localhost:5304";
var ollamaUrl = builder.Configuration["Services:OllamaUrl"] ?? "http://localhost:11434";
var ragUrl = builder.Configuration["RAG_SERVER_URL"] ?? "http://localhost:5500";
var databaseTimeout = builder.Configuration.GetValue("Services:DatabaseTimeoutSeconds", 4);
var ollamaTimeout = builder.Configuration.GetValue("Services:OllamaTimeoutSeconds", 15);
var model = builder.Configuration["STUDENT4_MODEL"] ?? "llama3.2:3b";
var prompt = File.ReadAllText(Path.Combine(builder.Environment.ContentRootPath, "Prompts", "budget-insights-v1.txt"));

builder.Services.ConfigureHttpJsonOptions(options => options.SerializerOptions.UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow);
builder.Services.AddSingleton(serviceProvider => FeatureModeSettings.FromConfiguration(serviceProvider.GetRequiredService<IConfiguration>()));
builder.Services.AddSingleton(TimeProvider.System);
builder.Services.AddSingleton<IExchangeRateProvider, FrankfurterExchangeRateProvider>();
builder.Services.AddHttpClient(FrankfurterExchangeRateProvider.ClientName, client => client.Timeout = Timeout.InfiniteTimeSpan)
    .ConfigurePrimaryHttpMessageHandler(() => new HttpClientHandler { AllowAutoRedirect = false });
builder.Services.AddSingleton(new OllamaInsightsSettings(model, prompt));
builder.Services.AddSingleton(serviceProvider => McpBudgetCheckSettings.FromUrl(
    serviceProvider.GetRequiredService<IConfiguration>()["MCP_SERVER_URL"] ?? "http://localhost:5400/mcp"));
builder.Services.AddSingleton(RagSettings.FromUrl(ragUrl));
builder.Services.AddScoped<IAdviceService, AdviceService>();
builder.Services.AddHttpClient<IDatabaseApiClient, DatabaseApiClient>(client => { client.BaseAddress = new Uri(databaseUrl); client.Timeout = TimeSpan.FromSeconds(databaseTimeout); });
builder.Services.AddHttpClient<IOllamaInsightsClient, OllamaInsightsClient>(client => { client.BaseAddress = new Uri(ollamaUrl); client.Timeout = TimeSpan.FromSeconds(ollamaTimeout); });
builder.Services.AddHttpClient<IMcpBudgetCheckClient, McpBudgetCheckClient>(client => client.Timeout = Timeout.InfiniteTimeSpan)
    .ConfigurePrimaryHttpMessageHandler(() => new BoundedMcpResponseHandler());
builder.Services.AddHttpClient<IRagClient, RagClient>(client => client.Timeout = Timeout.InfiniteTimeSpan);

var app = builder.Build();
_ = app.Services.GetRequiredService<FeatureModeSettings>();

app.Use(async (context, next) =>
{
    try { await next(); }
    catch (BadHttpRequestException) when (!context.Response.HasStarted) { await BudgetEndpoints.Error(context, 400, "invalid_request", "The request body is invalid.").ExecuteAsync(context); }
    catch (DatabaseRejectedException exception) when (!context.Response.HasStarted) { await BudgetEndpoints.Error(context, exception.StatusCode, exception.Code, exception.Message, exception.Fields).ExecuteAsync(context); }
    catch (DatabaseUnavailableException) when (!context.Response.HasStarted) { await BudgetEndpoints.Error(context, 503, "database_unavailable", "The database service is unavailable.").ExecuteAsync(context); }
    catch (DatabaseResponseException) when (!context.Response.HasStarted) { await BudgetEndpoints.Error(context, 502, "database_response_invalid", "The database service returned an unusable response.").ExecuteAsync(context); }
    catch (ExchangeRateUnavailableException) when (!context.Response.HasStarted) { await BudgetEndpoints.Error(context, 503, "exchange_rates_unavailable", "Reference exchange rates are currently unavailable.").ExecuteAsync(context); }
    catch (ExchangeRateResponseException) when (!context.Response.HasStarted) { await BudgetEndpoints.Error(context, 502, "exchange_rates_response_invalid", "The exchange rate service returned an unusable response.").ExecuteAsync(context); }
    catch (DashboardDataException) when (!context.Response.HasStarted) { await BudgetEndpoints.Error(context, 502, "database_response_invalid", "The database service returned unusable dashboard data.").ExecuteAsync(context); }
});

app.MapGet("/", () => Results.Ok(new { service = "budget-backend", status = "ready" }));
app.MapGet("/health", () => Results.Ok(new { status = "healthy", service = "budget-backend" }));
app.MapGet("/api/capabilities", (FeatureModeSettings modes) => Results.Ok(new { aiEnabled = modes.AiEnabled, mcpEnabled = modes.McpEnabled, ragEnabled = modes.RagEnabled }));
app.MapBudgetEndpoints();
app.MapBudgetCheckEndpoints();
app.MapBudgetGuidanceEndpoints();
app.Run();

public partial class Program;
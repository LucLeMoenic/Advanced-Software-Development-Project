using System.Globalization;
using System.Text.Json.Serialization;
using BudgetTracker.Backend.Api;
using BudgetTracker.Backend.Clients;
using BudgetTracker.Backend.Services;

var builder = WebApplication.CreateBuilder(args);
var databaseUrl = builder.Configuration["Services:DatabaseUrl"] ?? "http://localhost:5304";
var ollamaUrl = builder.Configuration["Services:OllamaUrl"] ?? "http://localhost:11434";
var databaseTimeout = builder.Configuration.GetValue("Services:DatabaseTimeoutSeconds", 4);
var ollamaTimeout = builder.Configuration.GetValue("Services:OllamaTimeoutSeconds", 15);
var model = builder.Configuration["STUDENT4_MODEL"] ?? "llama3.2:3b";
var rateSection = builder.Configuration.GetSection("ExchangeRates");
var rateDate = DateOnly.ParseExact(rateSection["RateAsOf"] ?? "2026-08-01", "yyyy-MM-dd", CultureInfo.InvariantCulture);
var rateValues = rateSection.GetSection("AudUnits").GetChildren().ToDictionary(value => value.Key, value => decimal.Parse(value.Value!, CultureInfo.InvariantCulture), StringComparer.OrdinalIgnoreCase);
var prompt = File.ReadAllText(Path.Combine(builder.Environment.ContentRootPath, "Prompts", "budget-insights-v1.txt"));

builder.Services.ConfigureHttpJsonOptions(options => options.SerializerOptions.UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow);
builder.Services.AddSingleton<IExchangeRateProvider>(new FixedExchangeRateProvider(new ExchangeRateSettings(rateSection["Version"] ?? "demo-v1", rateDate, rateSection["Disclaimer"] ?? "Demonstration rates only.", rateValues)));
builder.Services.AddSingleton(new OllamaInsightsSettings(model, prompt));
builder.Services.AddScoped<IAdviceService, AdviceService>();
builder.Services.AddHttpClient<IDatabaseApiClient, DatabaseApiClient>(client => { client.BaseAddress = new Uri(databaseUrl); client.Timeout = TimeSpan.FromSeconds(databaseTimeout); });
builder.Services.AddHttpClient<IOllamaInsightsClient, OllamaInsightsClient>(client => { client.BaseAddress = new Uri(ollamaUrl); client.Timeout = TimeSpan.FromSeconds(ollamaTimeout); });

var app = builder.Build();

app.Use(async (context, next) =>
{
    try { await next(); }
    catch (BadHttpRequestException) when (!context.Response.HasStarted) { await BudgetEndpoints.Error(context, 400, "invalid_request", "The request body is invalid.").ExecuteAsync(context); }
    catch (DatabaseRejectedException exception) when (!context.Response.HasStarted) { await BudgetEndpoints.Error(context, exception.StatusCode, exception.Code, exception.Message, exception.Fields).ExecuteAsync(context); }
    catch (DatabaseUnavailableException) when (!context.Response.HasStarted) { await BudgetEndpoints.Error(context, 503, "database_unavailable", "The database service is unavailable.").ExecuteAsync(context); }
    catch (DatabaseResponseException) when (!context.Response.HasStarted) { await BudgetEndpoints.Error(context, 502, "database_response_invalid", "The database service returned an unusable response.").ExecuteAsync(context); }
    catch (DashboardDataException) when (!context.Response.HasStarted) { await BudgetEndpoints.Error(context, 502, "database_response_invalid", "The database service returned unusable dashboard data.").ExecuteAsync(context); }
});

app.MapGet("/", () => Results.Ok(new { service = "budget-backend", status = "ready" }));
app.MapGet("/health", () => Results.Ok(new { status = "healthy", service = "budget-backend" }));
app.MapBudgetEndpoints();
app.Run();

public partial class Program;
using BudgetTracker.Database.Api;
using BudgetTracker.Database.Data;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);
var connectionString = builder.Configuration.GetConnectionString("BudgetDatabase") ?? "Data Source=budget.db";
var seedDemoData = builder.Configuration.GetValue("DemoData:Seed", true);

builder.Services.AddDbContext<BudgetDbContext>(options => options.UseSqlite(connectionString));
builder.Services.AddHealthChecks().AddDbContextCheck<BudgetDbContext>("sqlite");

var app = builder.Build();

app.Use(async (context, next) =>
{
    try
    {
        await next();
    }
    catch (BadHttpRequestException)
    {
        if (!context.Response.HasStarted)
        {
            await DataEndpoints.Error(context, 400, "invalid_request", "The request body is invalid.").ExecuteAsync(context);
        }
    }
    catch (DbUpdateException) when (!context.Response.HasStarted)
    {
        await DataEndpoints.Error(context, 409, "data_conflict", "The requested change conflicts with existing data.").ExecuteAsync(context);
    }
});

await using (var scope = app.Services.CreateAsyncScope())
{
    var database = scope.ServiceProvider.GetRequiredService<BudgetDbContext>();
    await database.Database.MigrateAsync();
    if (seedDemoData)
    {
        await DemoDataSeeder.SeedAsync(database);
    }
}

app.MapGet("/", () => Results.Ok(new { service = "budget-database", status = "ready", provider = "sqlite" }));
app.MapHealthChecks("/health");
app.MapDataEndpoints();

app.Run();

public partial class Program;
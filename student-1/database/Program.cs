using Microsoft.EntityFrameworkCore;
using Accommodation.Database.Api;
using Accommodation.Database.Data;

var builder = WebApplication.CreateBuilder(args);
var connectionString = builder.Configuration.GetConnectionString("AccommodationDatabase")
    ?? "Data Source=accommodation.db";

builder.Services.AddDbContext<AccommodationDbContext>(options =>
    options.UseSqlite(connectionString));
builder.Services
    .AddHealthChecks()
    .AddDbContextCheck<AccommodationDbContext>("sqlite");

var app = builder.Build();

await using (var scope = app.Services.CreateAsyncScope())
{
    var database = scope.ServiceProvider.GetRequiredService<AccommodationDbContext>();
    await database.Database.MigrateAsync();
}

app.MapGet("/", () => Results.Ok(new
{
    service = "accommodation-database",
    status = "ready",
    provider = "sqlite"
}));

app.MapHealthChecks("/health");
app.MapAccommodationEndpoints();

app.Run();

public partial class Program;

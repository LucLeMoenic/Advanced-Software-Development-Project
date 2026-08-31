using Microsoft.EntityFrameworkCore;
using Accommodation.Database.Api;
using Accommodation.Database.Data;
using Accommodation.Database.Repositories;

var builder = WebApplication.CreateBuilder(args);
var connectionString = builder.Configuration.GetConnectionString("AccommodationDatabase")
    ?? "Data Source=accommodation.db";

builder.Services.AddDbContext<DatabaseContext>(options =>
    options.UseSqlite(connectionString));
builder.Services.AddScoped<IAccommodationRepository, AccommodationRepository>();
builder.Services.AddScoped<ISearchRepository, SearchRepository>();
builder.Services
    .AddHealthChecks()
    .AddDbContextCheck<DatabaseContext>("sqlite");

var app = builder.Build();

await using (var scope = app.Services.CreateAsyncScope())
{
    var database = scope.ServiceProvider.GetRequiredService<DatabaseContext>();
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
app.MapSearchEndpoints();

app.Run();

public partial class Program;

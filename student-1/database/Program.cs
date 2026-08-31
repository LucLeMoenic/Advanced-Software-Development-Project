using Microsoft.EntityFrameworkCore;

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
    await database.Database.EnsureCreatedAsync();
}

app.MapGet("/", () => Results.Ok(new
{
    service = "student1-database",
    status = "ready",
    provider = "sqlite"
}));

app.MapHealthChecks("/health");

app.Run();

public sealed class AccommodationDbContext(DbContextOptions<AccommodationDbContext> options)
    : DbContext(options);

public partial class Program;

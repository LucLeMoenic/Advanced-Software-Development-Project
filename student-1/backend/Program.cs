var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

var databaseUrl = builder.Configuration["Services:DatabaseUrl"]
    ?? "http://localhost:5301";
var ollamaUrl = builder.Configuration["Services:OllamaUrl"]
    ?? "http://localhost:11434";

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

app.Run();

public partial class Program;

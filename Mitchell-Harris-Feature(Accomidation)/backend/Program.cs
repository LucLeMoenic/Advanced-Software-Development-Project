var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/", () => Results.Ok(new { service = "backend", status = "ok" }));
app.MapGet("/health", () => Results.Ok(new { status = "healthy" }));

app.Run();
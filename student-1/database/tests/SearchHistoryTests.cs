using System.Net;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Accommodation.Database.Api;
using Accommodation.Database.Data;
using SearchEntity = Accommodation.Database.Data.Search;

namespace Accommodation.Database.Tests;

public sealed class SearchHistoryTests : DatabaseApiTestBase
{
    private const string Route = "/api/data/searches";

    [Fact]
    public async Task SearchHistoryStartsEmpty()
    {
        var searches = await Client.GetFromJsonAsync<SearchSummaryResponse[]>(Route);

        Assert.NotNull(searches);
        Assert.Empty(searches);
    }

    [Fact]
    public async Task CreateListGetRenameAndDeleteSearch()
    {
        var firstResponse = await Client.PostAsJsonAsync(Route, ValidRequest("First Search"));
        var first = await firstResponse.Content.ReadFromJsonAsync<SearchResponse>();
        var secondResponse = await Client.PostAsJsonAsync(Route, ValidRequest("Second Search"));
        var second = await secondResponse.Content.ReadFromJsonAsync<SearchResponse>();

        Assert.Equal(HttpStatusCode.Created, firstResponse.StatusCode);
        Assert.Equal(HttpStatusCode.Created, secondResponse.StatusCode);
        Assert.NotNull(first);
        Assert.NotNull(second);
        Assert.Equal($"{Route}/{first.Id}", firstResponse.Headers.Location?.OriginalString);

        var summaries = await Client.GetFromJsonAsync<SearchSummaryResponse[]>(Route);

        Assert.NotNull(summaries);
        Assert.Equal(2, summaries.Length);
        Assert.Equal(second.Id, summaries[0].Id);
        Assert.Equal(first.Id, summaries[1].Id);

        var stored = await Client.GetFromJsonAsync<SearchResponse>($"{Route}/{first.Id}");

        Assert.NotNull(stored);
        Assert.Equal("First Search", stored.Title);
        Assert.Equal("Sydney", stored.Destination);
        Assert.Equal("ai", stored.RankingMode);
        Assert.Equal(JsonValueKind.Array, stored.Results.ValueKind);
        Assert.Single(stored.Results.EnumerateArray());

        var renameResponse = await Client.PatchAsJsonAsync(
            $"{Route}/{first.Id}",
            new SearchRenameRequest("  Renamed Search  "));
        var renamed = await renameResponse.Content.ReadFromJsonAsync<SearchResponse>();

        Assert.Equal(HttpStatusCode.OK, renameResponse.StatusCode);
        Assert.NotNull(renamed);
        Assert.Equal("Renamed Search", renamed.Title);
        Assert.Equal(stored.Results.GetRawText(), renamed.Results.GetRawText());
        Assert.True(renamed.UpdatedAt >= stored.UpdatedAt);

        var deleteResponse = await Client.DeleteAsync($"{Route}/{first.Id}");
        var repeatedDelete = await Client.DeleteAsync($"{Route}/{first.Id}");

        Assert.Equal(HttpStatusCode.NoContent, deleteResponse.StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, repeatedDelete.StatusCode);
    }

    [Fact]
    public async Task InvalidSearchReturnsFieldErrorsWithoutPersisting()
    {
        var today = DateOnly.FromDateTime(DateTime.Today);
        var response = await Client.PostAsJsonAsync(
            Route,
            new SearchCreateRequest(
                " ",
                "A",
                today.AddDays(-1),
                today.AddDays(-2),
                0,
                200m,
                100m,
                new string('x', 501),
                "model",
                Json("""{"rank":1}""")));
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();
        var searches = await Client.GetFromJsonAsync<SearchSummaryResponse[]>(Route);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.NotNull(error);
        Assert.Equal("validation_error", error.Error.Code);
        Assert.Contains("title", error.Error.Fields.Keys);
        Assert.Contains("destination", error.Error.Fields.Keys);
        Assert.Contains("checkIn", error.Error.Fields.Keys);
        Assert.Contains("checkOut", error.Error.Fields.Keys);
        Assert.Contains("guests", error.Error.Fields.Keys);
        Assert.Contains("maximumPrice", error.Error.Fields.Keys);
        Assert.Contains("preferences", error.Error.Fields.Keys);
        Assert.Contains("rankingMode", error.Error.Fields.Keys);
        Assert.Contains("results", error.Error.Fields.Keys);
        Assert.Empty(searches!);
    }

    [Fact]
    public async Task MalformedJsonAndInvalidRenameReturnValidationErrors()
    {
        using var malformedContent = new StringContent(
            """{"title":""",
            Encoding.UTF8,
            "application/json");
        var malformedResponse = await Client.PostAsync(Route, malformedContent);
        var createdResponse = await Client.PostAsJsonAsync(Route, ValidRequest("Valid Search"));
        var created = await createdResponse.Content.ReadFromJsonAsync<SearchResponse>();
        var renameResponse = await Client.PatchAsJsonAsync(
            $"{Route}/{created!.Id}",
            new SearchRenameRequest(" "));

        Assert.Equal(HttpStatusCode.BadRequest, malformedResponse.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, renameResponse.StatusCode);
    }

    [Fact]
    public async Task MissingSearchOperationsReturnNotFound()
    {
        var getResponse = await Client.GetAsync($"{Route}/999");
        var renameResponse = await Client.PatchAsJsonAsync(
            $"{Route}/999",
            new SearchRenameRequest("Missing"));
        var deleteResponse = await Client.DeleteAsync($"{Route}/999");

        Assert.Equal(HttpStatusCode.NotFound, getResponse.StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, renameResponse.StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, deleteResponse.StatusCode);
    }

    [Fact]
    public async Task StoredSnapshotSurvivesAccommodationDeletion()
    {
        var accommodationResponse = await Client.PostAsJsonAsync(
            "/api/data/accommodations",
            new AccommodationRequest(
                "Snapshot Hotel",
                "Sydney",
                "Stored independently from history.",
                180m,
                2,
                ["Wi-Fi"],
                null,
                null,
                true));
        var accommodation =
            await accommodationResponse.Content.ReadFromJsonAsync<AccommodationResponse>();
        var results = Json(
            $$"""
            [{
              "accommodationId": {{accommodation!.Id}},
              "name": "{{accommodation.Name}}",
              "rank": 1,
              "reason": "Within budget"
            }]
            """);
        var searchResponse = await Client.PostAsJsonAsync(
            Route,
            ValidRequest("Snapshot Search") with { Results = results });
        var search = await searchResponse.Content.ReadFromJsonAsync<SearchResponse>();

        var deleteAccommodation =
            await Client.DeleteAsync($"/api/data/accommodations/{accommodation.Id}");
        var stored =
            await Client.GetFromJsonAsync<SearchResponse>($"{Route}/{search!.Id}");

        Assert.Equal(HttpStatusCode.NoContent, deleteAccommodation.StatusCode);
        Assert.NotNull(stored);
        var storedResult = stored.Results.EnumerateArray().Single();
        Assert.Equal(accommodation.Id, storedResult.GetProperty("accommodationId").GetInt32());
        Assert.Equal(accommodation.Name, storedResult.GetProperty("name").GetString());
        Assert.Equal(1, storedResult.GetProperty("rank").GetInt32());
        Assert.Equal("Within budget", storedResult.GetProperty("reason").GetString());
    }

    [Fact]
    public async Task ProgrammaticRankingModeIsPersisted()
    {
        var response = await Client.PostAsJsonAsync(
            Route,
            ValidRequest("Programmatic Search") with { RankingMode = "programmatic" });
        var stored = await response.Content.ReadFromJsonAsync<SearchResponse>();

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        Assert.NotNull(stored);
        Assert.Equal("programmatic", stored.RankingMode);
    }

    [Fact]
    public async Task DatabaseRejectsMalformedSearchSnapshot()
    {
        await using var scope = Factory.Services.CreateAsyncScope();
        var database = scope.ServiceProvider.GetRequiredService<DatabaseContext>();
        var today = DateOnly.FromDateTime(DateTime.Today);
        database.Searches.Add(new SearchEntity
        {
            Title = "Invalid Snapshot",
            Destination = "Sydney",
            CheckIn = today.AddDays(1),
            CheckOut = today.AddDays(2),
            Guests = 2,
            MinimumPrice = 100m,
            MaximumPrice = 200m,
            Preferences = "",
            RankingMode = "ai",
            ResultsJson = "{}",
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        });

        await Assert.ThrowsAsync<DbUpdateException>(() => database.SaveChangesAsync());
    }

    private static SearchCreateRequest ValidRequest(string title)
    {
        var checkIn = DateOnly.FromDateTime(DateTime.Today).AddDays(14);
        return new(
            title,
            "Sydney",
            checkIn,
            checkIn.AddDays(3),
            2,
            100m,
            300m,
            "Near public transport",
            "AI",
            Json(
                """
                [{
                  "accommodationId": 7,
                  "rank": 1,
                  "reason": "Within budget"
                }]
                """));
    }

    private static JsonElement Json(string value)
    {
        return JsonSerializer.Deserialize<JsonElement>(value);
    }
}

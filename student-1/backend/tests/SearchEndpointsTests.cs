using System.Net;
using System.Net.Http.Json;
using Accommodation.Backend.Api;
using Accommodation.Backend.Clients;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace Accommodation.Backend.Tests;

public sealed class SearchEndpointsTests
{
    [Theory]
    [MemberData(nameof(InvalidSearches))]
    public async Task InvalidSearchDoesNotCallDatabase(SearchRequest request, string field)
    {
        var database = new FakeDatabaseApiClient();
        var ollama = new FakeOllamaRankingClient();
        using var factory = CreateFactory(database, ollama);
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync("/api/searches", request);
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.NotNull(error);
        Assert.Contains(field, error.Error.Fields.Keys);
        Assert.Equal(0, database.CallCount);
        Assert.Equal(0, ollama.CallCount);
    }

    [Fact]
    public async Task InvalidJsonDoesNotCallDatabase()
    {
        var database = new FakeDatabaseApiClient();
        var ollama = new FakeOllamaRankingClient();
        using var factory = CreateFactory(database, ollama);
        using var client = factory.CreateClient();
        using var content = new StringContent(
            """{"destination":""",
            System.Text.Encoding.UTF8,
            "application/json");

        var response = await client.PostAsync("/api/searches", content);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, database.CallCount);
        Assert.Equal(0, ollama.CallCount);
    }

    [Fact]
    public async Task NonJsonContentDoesNotCallDatabase()
    {
        var database = new FakeDatabaseApiClient();
        var ollama = new FakeOllamaRankingClient();
        using var factory = CreateFactory(database, ollama);
        using var client = factory.CreateClient();
        using var content = new StringContent("""{"destination":"Gold Coast"}""");

        var response = await client.PostAsync("/api/searches", content);
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.NotNull(error);
        Assert.Contains("body", error.Error.Fields.Keys);
        Assert.Equal(0, database.CallCount);
        Assert.Equal(0, ollama.CallCount);
    }

    [Fact]
    public async Task ValidSearchUsesAiRankingAndPersists()
    {
        var database = new FakeDatabaseApiClient
        {
            Candidates =
            [
                Candidate(2, 110m),
                Candidate(3, 90m),
                Candidate(4, 100m),
                Candidate(1, 100m)
            ]
        };
        var ollama = new FakeOllamaRankingClient();
        using var factory = CreateFactory(database, ollama);
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync(
            "/api/searches",
            ValidSearch() with
            {
                Destination = "  Gold Coast  ",
                Preferences = "  quiet room  "
            });
        var saved = await response.Content.ReadFromJsonAsync<SearchResponse>();

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        Assert.NotNull(saved);
        Assert.Equal(
            new CandidateQuery("Gold Coast", 2, 50m, 150m),
            database.LastCandidateQuery);
        Assert.NotNull(database.LastPersistRequest);
        Assert.Equal("Gold Coast", database.LastPersistRequest.Title);
        Assert.Equal("quiet room", database.LastPersistRequest.Preferences);
        Assert.Equal("ai", database.LastPersistRequest.RankingMode);
        Assert.Equal([2, 3, 4, 1], saved.Results.Select(result => result.AccommodationId));
        Assert.Equal([1, 2, 3, 4], saved.Results.Select(result => result.Rank));
        Assert.Null(saved.Notice);
        Assert.Equal(1, ollama.CallCount);
    }

    [Theory]
    [InlineData(RankingFailure.InvalidResponse)]
    [InlineData(RankingFailure.Unavailable)]
    public async Task AiFailureUsesDeterministicFallbackAndPersistsNotice(
        RankingFailure failure)
    {
        var database = new FakeDatabaseApiClient
        {
            Candidates =
            [
                Candidate(2, 110m),
                Candidate(3, 90m),
                Candidate(4, 100m),
                Candidate(1, 100m)
            ]
        };
        var ollama = new FakeOllamaRankingClient
        {
            Failure = failure
        };
        using var factory = CreateFactory(database, ollama);
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync("/api/searches", ValidSearch());
        var saved = await response.Content.ReadFromJsonAsync<SearchResponse>();

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        Assert.NotNull(saved);
        Assert.Equal("fallback", database.LastPersistRequest!.RankingMode);
        Assert.Equal([1, 4, 3, 2], saved.Results.Select(result => result.AccommodationId));
        Assert.Equal(
            "AI ranking was unavailable, so deterministic fallback ranking was used.",
            saved.Notice);
    }

    [Fact]
    public async Task EmptyCandidateSearchIsPersistedAndReturnsOk()
    {
        var database = new FakeDatabaseApiClient();
        var ollama = new FakeOllamaRankingClient();
        using var factory = CreateFactory(database, ollama);
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync("/api/searches", ValidSearch());
        var saved = await response.Content.ReadFromJsonAsync<SearchResponse>();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.NotNull(saved);
        Assert.Empty(saved.Results);
        Assert.NotNull(database.LastPersistRequest);
        Assert.Equal(0, ollama.CallCount);
    }

    [Theory]
    [InlineData(Failure.Unavailable, HttpStatusCode.ServiceUnavailable, "dependency_unavailable")]
    [InlineData(Failure.MalformedResponse, HttpStatusCode.BadGateway, "dependency_response_error")]
    public async Task SearchMapsDatabaseFailures(
        Failure failure,
        HttpStatusCode expectedStatus,
        string expectedCode)
    {
        var database = new FakeDatabaseApiClient { Failure = failure };
        using var factory = CreateFactory(database, new FakeOllamaRankingClient());
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync("/api/searches", ValidSearch());
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(expectedStatus, response.StatusCode);
        Assert.NotNull(error);
        Assert.Equal(expectedCode, error.Error.Code);
        Assert.Empty(error.Error.Fields);
        Assert.False(string.IsNullOrWhiteSpace(error.Error.CorrelationId));
    }

    [Fact]
    public async Task HistoryCrudUsesDatabaseApi()
    {
        var database = new FakeDatabaseApiClient();
        database.Searches.Add(database.CreateStoredSearch(
            new PersistSearchRequest(
                "Original",
                "Gold Coast",
                DateOnly.FromDateTime(DateTime.Today.AddDays(1)),
                DateOnly.FromDateTime(DateTime.Today.AddDays(2)),
                2,
                50m,
                150m,
                string.Empty,
                "fallback",
                [Result(1, 1)])));
        using var factory = CreateFactory(database, new FakeOllamaRankingClient());
        using var client = factory.CreateClient();

        var listResponse = await client.GetAsync("/api/searches");
        var list = await listResponse.Content.ReadFromJsonAsync<SearchSummaryResponse[]>();
        var getResponse = await client.GetAsync("/api/searches/1");
        var renameResponse = await client.PatchAsJsonAsync(
            "/api/searches/1",
            new SearchRenameRequest("  Renamed  "));
        var renamed = await renameResponse.Content.ReadFromJsonAsync<SearchResponse>();
        var deleteResponse = await client.DeleteAsync("/api/searches/1");
        var missingResponse = await client.GetAsync("/api/searches/1");
        var repeatedDeleteResponse = await client.DeleteAsync("/api/searches/1");

        Assert.Equal(HttpStatusCode.OK, listResponse.StatusCode);
        Assert.Single(list!);
        Assert.Equal(HttpStatusCode.OK, getResponse.StatusCode);
        Assert.Equal(HttpStatusCode.OK, renameResponse.StatusCode);
        Assert.Equal("Renamed", renamed!.Title);
        Assert.Equal(HttpStatusCode.NoContent, deleteResponse.StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, missingResponse.StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, repeatedDeleteResponse.StatusCode);
    }

    [Fact]
    public async Task InvalidRenameDoesNotCallDatabase()
    {
        var database = new FakeDatabaseApiClient();
        using var factory = CreateFactory(database, new FakeOllamaRankingClient());
        using var client = factory.CreateClient();

        var response = await client.PatchAsJsonAsync(
            "/api/searches/1",
            new SearchRenameRequest(" "));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, database.CallCount);
    }

    public static TheoryData<SearchRequest, string> InvalidSearches()
    {
        var valid = ValidSearch();
        return new TheoryData<SearchRequest, string>
        {
            { valid with { Destination = "x" }, "destination" },
            { valid with { Destination = new string('x', 101) }, "destination" },
            { valid with { CheckIn = DateOnly.FromDateTime(DateTime.Today.AddDays(-1)) }, "checkIn" },
            { valid with { CheckOut = valid.CheckIn }, "checkOut" },
            { valid with { Guests = 0 }, "guests" },
            { valid with { Guests = 21 }, "guests" },
            { valid with { MinimumPrice = -1m }, "minimumPrice" },
            { valid with { MaximumPrice = 100001m }, "maximumPrice" },
            { valid with { MinimumPrice = 151m, MaximumPrice = 150m }, "minimumPrice" },
            { valid with { Preferences = new string('x', 501) }, "preferences" }
        };
    }

    private static SearchRequest ValidSearch()
    {
        return new(
            "Gold Coast",
            DateOnly.FromDateTime(DateTime.Today.AddDays(1)),
            DateOnly.FromDateTime(DateTime.Today.AddDays(2)),
            2,
            50m,
            150m,
            string.Empty);
    }

    private static AccommodationCandidate Candidate(int id, decimal price)
    {
        return new(
            id,
            $"Stay {id}",
            "Gold Coast",
            "Description",
            price,
            4,
            ["WiFi"],
            null,
            null);
    }

    private static SearchResult Result(int accommodationId, int rank)
    {
        return new(
            accommodationId,
            $"Stay {accommodationId}",
            "Gold Coast",
            100m,
            4,
            rank,
            "Within budget.");
    }

    private static WebApplicationFactory<Program> CreateFactory(
        FakeDatabaseApiClient database,
        FakeOllamaRankingClient ollama)
    {
        return new WebApplicationFactory<Program>()
            .WithWebHostBuilder(builder =>
            {
                builder.ConfigureTestServices(services =>
                {
                    services.RemoveAll<IDatabaseApiClient>();
                    services.RemoveAll<IOllamaRankingClient>();
                    services.AddSingleton<IDatabaseApiClient>(database);
                    services.AddSingleton<IOllamaRankingClient>(ollama);
                });
            });
    }

    public enum Failure
    {
        None,
        Unavailable,
        MalformedResponse
    }

    public enum RankingFailure
    {
        None,
        InvalidResponse,
        Unavailable
    }

    private sealed class FakeOllamaRankingClient : IOllamaRankingClient
    {
        public RankingFailure Failure { get; init; }
        public int CallCount { get; private set; }

        public Task<IReadOnlyList<SearchResult>> RankAsync(
            ValidatedSearch search,
            IReadOnlyList<AccommodationCandidate> candidates,
            CancellationToken cancellationToken)
        {
            CallCount++;
            if (Failure == RankingFailure.InvalidResponse)
            {
                throw new OllamaResponseException();
            }

            if (Failure == RankingFailure.Unavailable)
            {
                throw new OllamaUnavailableException("connection");
            }

            IReadOnlyList<SearchResult> results = candidates
                .Select((candidate, index) => new SearchResult(
                    candidate.Id,
                    candidate.Name,
                    candidate.Destination,
                    candidate.NightlyPrice,
                    candidate.MaxGuests,
                    index + 1,
                    "AI-ranked from the supplied criteria."))
                .ToArray();
            return Task.FromResult(results);
        }
    }

    private sealed class FakeDatabaseApiClient : IDatabaseApiClient
    {
        public IReadOnlyList<AccommodationCandidate> Candidates { get; init; } = [];
        public List<SearchResponse> Searches { get; } = [];
        public CandidateQuery? LastCandidateQuery { get; private set; }
        public PersistSearchRequest? LastPersistRequest { get; private set; }
        public Failure Failure { get; init; }
        public int CallCount { get; private set; }

        public Task<IReadOnlyList<AccommodationCandidate>> ListCandidatesAsync(
            CandidateQuery query,
            CancellationToken cancellationToken)
        {
            Called();
            LastCandidateQuery = query;
            return Task.FromResult(Candidates);
        }

        public Task<SearchResponse> CreateSearchAsync(
            PersistSearchRequest request,
            CancellationToken cancellationToken)
        {
            Called();
            LastPersistRequest = request;
            var search = CreateStoredSearch(request);
            Searches.Add(search);
            return Task.FromResult(search);
        }

        public Task<IReadOnlyList<SearchSummaryResponse>> ListSearchesAsync(
            CancellationToken cancellationToken)
        {
            Called();
            IReadOnlyList<SearchSummaryResponse> summaries = Searches
                .OrderByDescending(search => search.CreatedAt)
                .Select(search => new SearchSummaryResponse(
                    search.Id,
                    search.Title,
                    search.Destination,
                    search.CheckIn,
                    search.CheckOut,
                    search.Guests,
                    search.RankingMode,
                    search.CreatedAt,
                    search.UpdatedAt))
                .ToArray();
            return Task.FromResult(summaries);
        }

        public Task<SearchResponse> GetSearchAsync(
            int id,
            CancellationToken cancellationToken)
        {
            Called();
            return Task.FromResult(
                Searches.SingleOrDefault(search => search.Id == id)
                ?? throw new DatabaseRecordNotFoundException());
        }

        public Task<SearchResponse> RenameSearchAsync(
            int id,
            SearchRenameRequest request,
            CancellationToken cancellationToken)
        {
            Called();
            var index = Searches.FindIndex(search => search.Id == id);
            if (index < 0)
            {
                throw new DatabaseRecordNotFoundException();
            }

            Searches[index] = Searches[index] with
            {
                Title = request.Title!,
                UpdatedAt = DateTime.UtcNow
            };
            return Task.FromResult(Searches[index]);
        }

        public Task DeleteSearchAsync(int id, CancellationToken cancellationToken)
        {
            Called();
            var removed = Searches.RemoveAll(search => search.Id == id);
            if (removed == 0)
            {
                throw new DatabaseRecordNotFoundException();
            }

            return Task.CompletedTask;
        }

        public SearchResponse CreateStoredSearch(PersistSearchRequest request)
        {
            var now = DateTime.UtcNow;
            return new(
                Searches.Count + 1,
                request.Title,
                request.Destination,
                request.CheckIn,
                request.CheckOut,
                request.Guests,
                request.MinimumPrice,
                request.MaximumPrice,
                request.Preferences,
                request.RankingMode,
                request.Results,
                now,
                now);
        }

        private void Called()
        {
            CallCount++;
            switch (Failure)
            {
                case Failure.Unavailable:
                    throw new DatabaseUnavailableException();
                case Failure.MalformedResponse:
                    throw new DatabaseResponseException();
            }
        }
    }
}

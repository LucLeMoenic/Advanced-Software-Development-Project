using System.Net;
using System.Text;
using Accommodation.Backend.Api;
using Accommodation.Backend.Clients;

namespace Accommodation.Backend.Tests;

public sealed class DatabaseApiClientTests
{
    [Fact]
    public async Task CandidateRequestContainsAllEligibilityFilters()
    {
        var handler = new StubHandler(request =>
        {
            Assert.Equal(HttpMethod.Get, request.Method);
            Assert.Equal(
                "/api/data/accommodations?destination=Gold%20Coast&minPrice=50&maxPrice=150&guests=2&active=true",
                request.RequestUri!.PathAndQuery);
            return JsonResponse("[]");
        });
        var client = new DatabaseApiClient(new HttpClient(handler)
        {
            BaseAddress = new Uri("http://database")
        });

        var candidates = await client.ListCandidatesAsync(
            new CandidateQuery("Gold Coast", 2, 50m, 150m),
            CancellationToken.None);

        Assert.Empty(candidates);
    }

    [Fact]
    public async Task CandidateResponseMapsDatabaseContract()
    {
        var handler = new StubHandler(_ => JsonResponse(
            """
            [{
              "id": 7,
              "name": "Harbour Stay",
              "destination": "Gold Coast",
              "description": "Near the water",
              "nightlyPrice": 120.50,
              "maxGuests": 4,
              "amenities": ["WiFi"],
              "imageUrl": null,
              "bookingUrl": "https://example.com/stay",
              "isActive": true,
              "createdAt": "2026-08-31T00:00:00Z",
              "updatedAt": "2026-08-31T00:00:00Z"
            }]
            """));
        var client = new DatabaseApiClient(new HttpClient(handler)
        {
            BaseAddress = new Uri("http://database")
        });

        var candidates = await client.ListCandidatesAsync(
            new CandidateQuery("Gold Coast", 2, 100m, 150m),
            CancellationToken.None);

        var candidate = Assert.Single(candidates);
        Assert.Equal(7, candidate.Id);
        Assert.Equal(120.50m, candidate.NightlyPrice);
    }

    [Theory]
    [InlineData(HttpStatusCode.Created)]
    [InlineData(HttpStatusCode.Conflict)]
    public async Task AccommodationImportAcceptsCreatedOrExistingRecord(
        HttpStatusCode statusCode)
    {
        var handler = new StubHandler(request =>
        {
            Assert.Equal(HttpMethod.Post, request.Method);
            Assert.Equal("/api/data/accommodations", request.RequestUri!.AbsolutePath);
            return new HttpResponseMessage(statusCode);
        });
        var client = new DatabaseApiClient(new HttpClient(handler)
        {
            BaseAddress = new Uri("http://database")
        });

        await client.ImportAccommodationAsync(
            new AccommodationImportRequest(
                "Stay",
                "Gold Coast",
                "Imported",
                100m,
                2,
                [],
                null,
                null,
                true),
            CancellationToken.None);
    }

    [Theory]
    [InlineData("[null]")]
    [InlineData("[{}]")]
    [InlineData("""
        [{
          "id": 1,
          "name": "Stay",
          "destination": "Wrong Place",
          "description": "Description",
          "nightlyPrice": 100,
          "maxGuests": 2,
          "amenities": [],
          "isActive": true
        }]
        """)]
    public async Task SemanticallyInvalidCandidateResponseIsRejected(string json)
    {
        var handler = new StubHandler(_ => JsonResponse(json));
        var client = new DatabaseApiClient(new HttpClient(handler)
        {
            BaseAddress = new Uri("http://database")
        });

        await Assert.ThrowsAsync<DatabaseResponseException>(() =>
            client.ListCandidatesAsync(
                new CandidateQuery("Gold Coast", 2, 50m, 150m),
                CancellationToken.None));
    }

    [Fact]
    public async Task MalformedJsonIsAnUnusableDependencyResponse()
    {
        var handler = new StubHandler(_ => JsonResponse("""{"not":"an array"}"""));
        var client = new DatabaseApiClient(new HttpClient(handler)
        {
            BaseAddress = new Uri("http://database")
        });

        await Assert.ThrowsAsync<DatabaseResponseException>(() =>
            client.ListSearchesAsync(CancellationToken.None));
    }

    [Fact]
    public async Task ProgrammaticSearchResponseIsAccepted()
    {
        var handler = new StubHandler(_ => JsonResponse(
            """
            [{
              "id": 1,
              "title": "Sydney",
              "destination": "Sydney",
              "checkIn": "2026-09-10",
              "checkOut": "2026-09-12",
              "guests": 2,
              "rankingMode": "programmatic",
              "createdAt": "2026-09-01T00:00:00Z",
              "updatedAt": "2026-09-01T00:00:00Z"
            }]
            """));
        var client = new DatabaseApiClient(new HttpClient(handler)
        {
            BaseAddress = new Uri("http://database")
        });

        var searches = await client.ListSearchesAsync(CancellationToken.None);

        Assert.Equal("programmatic", Assert.Single(searches).RankingMode);
    }

    [Fact]
    public async Task TimeoutIsAnUnavailableDependency()
    {
        var client = new DatabaseApiClient(new HttpClient(new TimeoutHandler())
        {
            BaseAddress = new Uri("http://database")
        });

        await Assert.ThrowsAsync<DatabaseUnavailableException>(() =>
            client.ListSearchesAsync(CancellationToken.None));
    }

    [Fact]
    public async Task CollectionNotFoundIsAnUnusableDependencyResponse()
    {
        var handler = new StubHandler(_ =>
            new HttpResponseMessage(HttpStatusCode.NotFound));
        var client = new DatabaseApiClient(new HttpClient(handler)
        {
            BaseAddress = new Uri("http://database")
        });

        await Assert.ThrowsAsync<DatabaseResponseException>(() =>
            client.ListSearchesAsync(CancellationToken.None));
    }

    [Fact]
    public async Task ItemNotFoundIsARecordNotFoundResponse()
    {
        var handler = new StubHandler(_ =>
            new HttpResponseMessage(HttpStatusCode.NotFound));
        var client = new DatabaseApiClient(new HttpClient(handler)
        {
            BaseAddress = new Uri("http://database")
        });

        await Assert.ThrowsAsync<DatabaseRecordNotFoundException>(() =>
            client.GetSearchAsync(42, CancellationToken.None));
    }

    private static HttpResponseMessage JsonResponse(string json)
    {
        return new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json")
        };
    }

    private sealed class StubHandler(
        Func<HttpRequestMessage, HttpResponseMessage> responseFactory)
        : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            return Task.FromResult(responseFactory(request));
        }
    }

    private sealed class TimeoutHandler : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            throw new TaskCanceledException();
        }
    }
}

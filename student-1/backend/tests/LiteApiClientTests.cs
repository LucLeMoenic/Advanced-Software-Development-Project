using System.Net;
using System.Text;
using System.Text.Json;
using Accommodation.Backend.Api;
using Accommodation.Backend.Clients;

namespace Accommodation.Backend.Tests;

public sealed class LiteApiClientTests
{
    [Fact]
    public async Task ValidRatesAreMappedToNightlyAccommodationImports()
    {
        var handler = new StubHandler(async request =>
        {
            Assert.Equal(HttpMethod.Post, request.Method);
            Assert.Equal("/v3.0/hotels/rates", request.RequestUri!.AbsolutePath);
            Assert.Equal("sandbox-key", request.Headers.GetValues("X-API-Key").Single());

            var body = JsonDocument.Parse(await request.Content!.ReadAsStringAsync());
            Assert.Equal("Gold Coast", body.RootElement.GetProperty("aiSearch").GetString());
            Assert.Equal("AUD", body.RootElement.GetProperty("currency").GetString());
            Assert.True(body.RootElement.GetProperty("includeHotelData").GetBoolean());
            Assert.Equal(2, body.RootElement
                .GetProperty("occupancies")[0]
                .GetProperty("adults")
                .GetInt32());

            return JsonResponse(
                """
                {
                  "data": [{
                    "hotelId": "lp1",
                    "roomTypes": [{
                      "rates": [{ "maxOccupancy": 4 }],
                      "offerRetailRate": { "amount": 300, "currency": "AUD" }
                    }]
                  }],
                  "hotels": [{
                    "id": "lp1",
                    "name": "Harbour Stay",
                    "main_photo": "https://example.com/hotel.jpg",
                    "address": "1 Beach Road"
                  }]
                }
                """);
        });
        var client = CreateClient(handler, "sandbox-key");

        var imports = await client.SearchAsync(
            Search(checkOutDays: 2),
            CancellationToken.None);

        var import = Assert.Single(imports);
        Assert.Equal("Harbour Stay", import.Name);
        Assert.Equal(150m, import.NightlyPrice);
        Assert.Equal(4, import.MaxGuests);
        Assert.Equal("Gold Coast", import.Destination);
    }

    [Fact]
    public async Task MissingKeyDoesNotSendARequest()
    {
        var handler = new StubHandler(_ =>
            throw new InvalidOperationException("HTTP should not be called."));
        var client = CreateClient(handler, string.Empty);

        var exception = await Assert.ThrowsAsync<LiteApiUnavailableException>(() =>
            client.SearchAsync(Search(), CancellationToken.None));

        Assert.Equal("liteapi_configuration", exception.FailureCategory);
    }

    [Theory]
    [InlineData("""{"data":[{"hotelId":"lp1","roomTypes":[]}],"hotels":[]}""")]
    [InlineData("""{"data":[{"hotelId":"lp1","roomTypes":[{"rates":[{"maxOccupancy":1}],"offerRetailRate":{"amount":100,"currency":"USD"}}]}],"hotels":[{"id":"lp1","name":"Stay"}]}""")]
    [InlineData("""{"data":[{"hotelId":"lp1","roomTypes":[{"rates":[{"maxOccupancy":2}],"offerRetailRate":null}]}],"hotels":[{"id":"lp1","name":"Stay"}]}""")]
    [InlineData("""{"data":[{"hotelId":"lp1","roomTypes":[{"rates":[{"maxOccupancy":2}],"offerRetailRate":{"amount":null,"currency":"AUD"}}]}],"hotels":[{"id":"lp1","name":"Stay"}]}""")]
    [InlineData("""{"data":null,"hotels":[]}""")]
    public async Task UnusableProviderResponsesAreRejected(string json)
    {
        var client = CreateClient(
            new StubHandler(_ => Task.FromResult(JsonResponse(json))),
            "sandbox-key");

        await Assert.ThrowsAsync<LiteApiResponseException>(() =>
            client.SearchAsync(Search(), CancellationToken.None));
    }

    [Fact]
    public async Task EmptyProviderResultReturnsNoImports()
    {
        var client = CreateClient(
            new StubHandler(_ => Task.FromResult(
                JsonResponse("""{"data":[],"hotels":[]}"""))),
            "sandbox-key");

        var imports = await client.SearchAsync(Search(), CancellationToken.None);

        Assert.Empty(imports);
    }

    [Fact]
    public async Task MissingHotelMetadataIsSkippedWhenOtherResultsAreUsable()
    {
        const string json =
            """
            {
              "data": [
                {
                  "hotelId": "missing",
                  "roomTypes": [{
                    "rates": [{ "maxOccupancy": 2 }],
                    "offerRetailRate": { "amount": 100, "currency": "AUD" }
                  }]
                },
                {
                  "hotelId": "lp1",
                  "roomTypes": [{
                    "rates": [{ "maxOccupancy": 2 }],
                    "offerRetailRate": { "amount": 120, "currency": "AUD" }
                  }]
                }
              ],
              "hotels": [{ "id": "lp1", "name": "Usable Stay" }]
            }
            """;
        var client = CreateClient(
            new StubHandler(_ => Task.FromResult(JsonResponse(json))),
            "sandbox-key");

        var imports = await client.SearchAsync(Search(), CancellationToken.None);

        var import = Assert.Single(imports);
        Assert.Equal("Usable Stay", import.Name);
    }

    [Fact]
    public async Task DuplicateHotelMetadataIsRejected()
    {
        const string json =
            """
            {
              "data": [],
              "hotels": [
                { "id": "lp1", "name": "Stay One" },
                { "id": "lp1", "name": "Stay Two" }
              ]
            }
            """;
        var client = CreateClient(
            new StubHandler(_ => Task.FromResult(JsonResponse(json))),
            "sandbox-key");

        await Assert.ThrowsAsync<LiteApiResponseException>(() =>
            client.SearchAsync(Search(), CancellationToken.None));
    }

    [Fact]
    public async Task RateLimitIsAnUnavailableProvider()
    {
        var client = CreateClient(
            new StubHandler(_ => Task.FromResult(
                new HttpResponseMessage(HttpStatusCode.TooManyRequests))),
            "sandbox-key");

        var exception = await Assert.ThrowsAsync<LiteApiUnavailableException>(() =>
            client.SearchAsync(Search(), CancellationToken.None));

        Assert.Equal("liteapi_http_429", exception.FailureCategory);
    }

    private static LiteApiClient CreateClient(
        HttpMessageHandler handler,
        string apiKey)
    {
        return new(
            new HttpClient(handler)
            {
                BaseAddress = new Uri("https://api.liteapi.travel")
            },
            new LiteApiSettings(apiKey));
    }

    private static ValidatedSearch Search(int checkOutDays = 1)
    {
        var checkIn = DateOnly.FromDateTime(DateTime.Today.AddDays(1));
        return new(
            "Gold Coast",
            checkIn,
            checkIn.AddDays(checkOutDays),
            2,
            50m,
            200m,
            string.Empty);
    }

    private static HttpResponseMessage JsonResponse(string json)
    {
        return new(HttpStatusCode.OK)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json")
        };
    }

    private sealed class StubHandler(
        Func<HttpRequestMessage, Task<HttpResponseMessage>> responseFactory)
        : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            return responseFactory(request);
        }
    }
}

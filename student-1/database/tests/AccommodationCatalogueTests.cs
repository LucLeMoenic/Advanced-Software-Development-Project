using System.Net;
using System.Net.Http.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Accommodation.Database.Api;
using Accommodation.Database.Data;
using Accommodation.Database.Repositories;
using AccommodationEntity = Accommodation.Database.Data.Accommodation;

namespace Accommodation.Database.Tests;

public sealed class AccommodationCatalogueTests : DatabaseApiTestBase
{
    private const string Route = "/api/data/accommodations";

    [Fact]
    public async Task CatalogueStartsEmpty()
    {
        var accommodations =
            await Client.GetFromJsonAsync<AccommodationResponse[]>(Route);

        Assert.NotNull(accommodations);
        Assert.Empty(accommodations);
    }

    [Fact]
    public async Task CreateReadReplaceAndDeleteAccommodation()
    {
        var createResponse = await Client.PostAsJsonAsync(Route, ValidRequest());
        var created =
            await createResponse.Content.ReadFromJsonAsync<AccommodationResponse>();

        Assert.Equal(HttpStatusCode.Created, createResponse.StatusCode);
        Assert.NotNull(created);
        Assert.True(created.Id > 0);
        Assert.Equal("Harbour View Hotel", created.Name);
        Assert.Equal($"{Route}/{created.Id}", createResponse.Headers.Location?.OriginalString);

        var read =
            await Client.GetFromJsonAsync<AccommodationResponse>($"{Route}/{created.Id}");
        Assert.NotNull(read);
        Assert.Equal(created.Id, read.Id);
        Assert.Equal(created.Name, read.Name);
        Assert.Equal(created.Destination, read.Destination);
        Assert.Equal(created.NightlyPrice, read.NightlyPrice);
        Assert.Equal(created.Amenities, read.Amenities);

        var replacement = ValidRequest() with
        {
            Name = "Harbour View Suites",
            NightlyPrice = 245.50m,
            MaxGuests = 4,
            Amenities = ["Wi-Fi", "Kitchen"]
        };
        var replaceResponse =
            await Client.PutAsJsonAsync($"{Route}/{created.Id}", replacement);
        var replaced =
            await replaceResponse.Content.ReadFromJsonAsync<AccommodationResponse>();

        Assert.Equal(HttpStatusCode.OK, replaceResponse.StatusCode);
        Assert.NotNull(replaced);
        Assert.Equal(created.Id, replaced.Id);
        Assert.Equal("Harbour View Suites", replaced.Name);
        Assert.Equal(245.50m, replaced.NightlyPrice);
        Assert.Equal(created.CreatedAt, replaced.CreatedAt);
        Assert.True(replaced.UpdatedAt >= created.UpdatedAt);

        var deleteResponse = await Client.DeleteAsync($"{Route}/{created.Id}");
        var missingResponse = await Client.GetAsync($"{Route}/{created.Id}");

        Assert.Equal(HttpStatusCode.NoContent, deleteResponse.StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, missingResponse.StatusCode);
    }

    [Fact]
    public async Task InvalidAccommodationReturnsFieldErrorsWithoutPersisting()
    {
        var response = await Client.PostAsJsonAsync(
            Route,
            new AccommodationRequest(
                " ",
                "A",
                "",
                -1m,
                21,
                ["Wi-Fi", "wi-fi", ""],
                "ftp://invalid.example",
                new string('x', 2049),
                true));
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();
        var accommodations =
            await Client.GetFromJsonAsync<AccommodationResponse[]>(Route);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.NotNull(error);
        Assert.Equal("validation_error", error.Error.Code);
        Assert.Contains("name", error.Error.Fields.Keys);
        Assert.Contains("destination", error.Error.Fields.Keys);
        Assert.Contains("description", error.Error.Fields.Keys);
        Assert.Contains("nightlyPrice", error.Error.Fields.Keys);
        Assert.Contains("maxGuests", error.Error.Fields.Keys);
        Assert.Contains("amenities", error.Error.Fields.Keys);
        Assert.Contains("imageUrl", error.Error.Fields.Keys);
        Assert.Contains("bookingUrl", error.Error.Fields.Keys);
        Assert.Empty(accommodations!);
    }

    [Fact]
    public async Task DuplicateNameAndDestinationReturnsConflictCaseInsensitively()
    {
        var first = await Client.PostAsJsonAsync(Route, ValidRequest());
        var duplicate = await Client.PostAsJsonAsync(
            Route,
            ValidRequest() with
            {
                Name = "harbour view hotel",
                Destination = "SYDNEY"
            });
        var error = await duplicate.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(HttpStatusCode.Created, first.StatusCode);
        Assert.Equal(HttpStatusCode.Conflict, duplicate.StatusCode);
        Assert.NotNull(error);
        Assert.Equal("accommodation_conflict", error.Error.Code);
    }

    [Fact]
    public async Task FiltersUseInclusivePriceCapacityAndActiveBoundaries()
    {
        await Client.PostAsJsonAsync(
            Route,
            ValidRequest() with { Name = "Exact Match", NightlyPrice = 200m, MaxGuests = 4 });
        await Client.PostAsJsonAsync(
            Route,
            ValidRequest() with { Name = "Too Expensive", NightlyPrice = 201m, MaxGuests = 4 });
        await Client.PostAsJsonAsync(
            Route,
            ValidRequest() with { Name = "Too Small", NightlyPrice = 180m, MaxGuests = 3 });
        await Client.PostAsJsonAsync(
            Route,
            ValidRequest() with { Name = "Inactive", NightlyPrice = 190m, MaxGuests = 5, IsActive = false });
        await Client.PostAsJsonAsync(
            Route,
            ValidRequest() with { Name = "Other City", Destination = "Melbourne", NightlyPrice = 190m, MaxGuests = 5 });

        var matches = await Client.GetFromJsonAsync<AccommodationResponse[]>(
            $"{Route}?destination=sydney&minPrice=200&maxPrice=200&guests=4&active=true");
        var inactive = await Client.GetFromJsonAsync<AccommodationResponse[]>(
            $"{Route}?destination=Sydney&active=false");

        Assert.NotNull(matches);
        Assert.Single(matches);
        Assert.Equal("Exact Match", matches[0].Name);
        Assert.NotNull(inactive);
        Assert.Single(inactive);
        Assert.Equal("Inactive", inactive[0].Name);
    }

    [Fact]
    public async Task InvalidFiltersReturnStableValidationError()
    {
        var response = await Client.GetAsync(
            $"{Route}?destination=A&minPrice=20&maxPrice=10&guests=0&active=sometimes");
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.NotNull(error);
        Assert.Equal("validation_error", error.Error.Code);
        Assert.Contains("destination", error.Error.Fields.Keys);
        Assert.Contains("minPrice", error.Error.Fields.Keys);
        Assert.Contains("guests", error.Error.Fields.Keys);
        Assert.Contains("active", error.Error.Fields.Keys);
    }

    [Fact]
    public async Task MissingAccommodationOperationsReturnNotFound()
    {
        var getResponse = await Client.GetAsync($"{Route}/999");
        var putResponse = await Client.PutAsJsonAsync($"{Route}/999", ValidRequest());
        var deleteResponse = await Client.DeleteAsync($"{Route}/999");

        Assert.Equal(HttpStatusCode.NotFound, getResponse.StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, putResponse.StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, deleteResponse.StatusCode);
    }

    [Fact]
    public async Task SqlInjectionShapedDestinationRemainsData()
    {
        const string destination = "Sydney'; DROP TABLE accommodations;--";
        var createResponse = await Client.PostAsJsonAsync(
            Route,
            ValidRequest() with { Destination = destination });
        var encodedDestination = Uri.EscapeDataString(destination);
        var matches = await Client.GetFromJsonAsync<AccommodationResponse[]>(
            $"{Route}?destination={encodedDestination}");
        var secondCreate = await Client.PostAsJsonAsync(
            Route,
            ValidRequest() with { Name = "Schema Still Available" });

        Assert.Equal(HttpStatusCode.Created, createResponse.StatusCode);
        Assert.NotNull(matches);
        Assert.Single(matches);
        Assert.Equal(destination, matches[0].Destination);
        Assert.Equal(HttpStatusCode.Created, secondCreate.StatusCode);
    }

    [Fact]
    public async Task DatabaseConstraintsRejectInvalidRows()
    {
        await using var scope = Factory.Services.CreateAsyncScope();
        var repository =
            scope.ServiceProvider.GetRequiredService<IAccommodationRepository>();
        repository.Add(new AccommodationEntity
        {
            Name = "Invalid Price",
            Destination = "Sydney",
            Description = "Inserted directly to prove the database constraint.",
            NightlyPrice = -1m,
            MaxGuests = 2,
            AmenitiesJson = "[]",
            IsActive = true,
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        });

        await Assert.ThrowsAsync<DbUpdateException>(
            () => repository.SaveChangesAsync(CancellationToken.None));
    }

    [Fact]
    public async Task DatabaseConstraintRejectsMalformedAmenitiesJson()
    {
        await using var scope = Factory.Services.CreateAsyncScope();
        var database = scope.ServiceProvider.GetRequiredService<DatabaseContext>();
        database.Accommodations.Add(new AccommodationEntity
        {
            Name = "Invalid Amenities",
            Destination = "Sydney",
            Description = "Inserted directly to prove the JSON database constraint.",
            NightlyPrice = 100m,
            MaxGuests = 2,
            AmenitiesJson = "Wi-Fi, Breakfast",
            IsActive = true,
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        });

        await Assert.ThrowsAsync<DbUpdateException>(() => database.SaveChangesAsync());
    }

    private static AccommodationRequest ValidRequest()
    {
        return new(
            "Harbour View Hotel",
            "Sydney",
            "Central accommodation with harbour access.",
            220m,
            2,
            ["Wi-Fi", "Breakfast"],
            "https://example.com/image.jpg",
            "https://example.com/book",
            true);
    }
}

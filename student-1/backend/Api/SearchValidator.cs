namespace Accommodation.Backend.Api;

internal static class SearchValidator
{
    public static SearchValidationResult Validate(SearchRequest request, DateOnly today)
    {
        var fields = new Dictionary<string, string>();
        var destination = request.Destination?.Trim();
        if (destination is null || destination.Length is < 2 or > 100)
        {
            fields["destination"] = "Must be between 2 and 100 characters.";
        }

        if (request.CheckIn is null)
        {
            fields["checkIn"] = "A valid ISO date is required.";
        }
        else if (request.CheckIn < today)
        {
            fields["checkIn"] = "Must not be before the current local date.";
        }

        if (request.CheckOut is null)
        {
            fields["checkOut"] = "A valid ISO date is required.";
        }
        else if (request.CheckIn is not null && request.CheckOut <= request.CheckIn)
        {
            fields["checkOut"] = "Must be after check-in.";
        }

        if (request.Guests is null or < 1 or > 20)
        {
            fields["guests"] = "Must be an integer between 1 and 20.";
        }

        if (request.MinimumPrice is null or < 0 or > 100000)
        {
            fields["minimumPrice"] = "Must be a number between 0 and 100000.";
        }

        if (request.MaximumPrice is null or < 0 or > 100000)
        {
            fields["maximumPrice"] = "Must be a number between 0 and 100000.";
        }
        else if (request.MinimumPrice is not null
            && request.MinimumPrice > request.MaximumPrice)
        {
            fields["minimumPrice"] = "Must not be greater than maximumPrice.";
        }

        var preferences = request.Preferences?.Trim() ?? string.Empty;
        if (preferences.Length > 500)
        {
            fields["preferences"] = "Must contain at most 500 characters.";
        }

        if (fields.Count > 0)
        {
            return new(null, fields);
        }

        return new(
            new ValidatedSearch(
                destination!,
                request.CheckIn!.Value,
                request.CheckOut!.Value,
                request.Guests!.Value,
                decimal.Round(request.MinimumPrice!.Value, 2),
                decimal.Round(request.MaximumPrice!.Value, 2),
                preferences),
            null);
    }
}

internal sealed record SearchValidationResult(
    ValidatedSearch? Value,
    IReadOnlyDictionary<string, string>? Errors);

internal sealed record ValidatedSearch(
    string Destination,
    DateOnly CheckIn,
    DateOnly CheckOut,
    int Guests,
    decimal MinimumPrice,
    decimal MaximumPrice,
    string Preferences);

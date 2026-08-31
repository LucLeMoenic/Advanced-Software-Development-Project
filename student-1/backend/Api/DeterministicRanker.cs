using System.Globalization;

namespace Accommodation.Backend.Api;

internal static class DeterministicRanker
{
    public static IReadOnlyList<SearchResult> Rank(
        IReadOnlyList<AccommodationCandidate> candidates,
        decimal minimumPrice,
        decimal maximumPrice)
    {
        var budgetMidpoint = (minimumPrice + maximumPrice) / 2m;

        return candidates
            .OrderBy(candidate => Math.Abs(candidate.NightlyPrice - budgetMidpoint))
            .ThenBy(candidate => candidate.NightlyPrice)
            .ThenBy(candidate => candidate.Id)
            .Select((candidate, index) => ToResult(candidate, index + 1, budgetMidpoint))
            .ToArray();
    }

    private static SearchResult ToResult(
        AccommodationCandidate candidate,
        int rank,
        decimal budgetMidpoint)
    {
        var distance = Math.Abs(candidate.NightlyPrice - budgetMidpoint);
        var reason = string.Create(
            CultureInfo.InvariantCulture,
            $"Nightly price is {distance:0.00} from the budget midpoint.");

        return new(
            candidate.Id,
            candidate.Name,
            candidate.Destination,
            candidate.NightlyPrice,
            candidate.MaxGuests,
            rank,
            reason);
    }
}

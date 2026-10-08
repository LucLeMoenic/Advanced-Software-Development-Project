using BudgetTracker.Backend.Api;

namespace BudgetTracker.Backend.Services;

public interface IExchangeRateProvider
{
    IReadOnlyList<string> Currencies { get; }
    ExchangeRateMetadata Metadata { get; }
    bool Supports(string? currency);
    Task<ConversionResponse> ConvertAsync(long amountMinor, string fromCurrency, string toCurrency, CancellationToken cancellationToken);
}

public sealed record ExchangeRateMetadata(DateOnly? RateAsOf, string RateVersion, string Disclaimer, string Status, DateTimeOffset? FetchedAt = null);
public sealed record ExchangeRateSettings(string Version, DateOnly RateAsOf, string Disclaimer, IReadOnlyDictionary<string, decimal> AudUnits);

public sealed class FixedExchangeRateProvider(ExchangeRateSettings settings) : IExchangeRateProvider
{
    private const decimal RateScale = 100_000_000m;
    public IReadOnlyList<string> Currencies { get; } = settings.AudUnits.Keys.Order(StringComparer.Ordinal).ToArray();
    public ExchangeRateMetadata Metadata => new(settings.RateAsOf, settings.Version, settings.Disclaimer, "fixed");

    public bool Supports(string? currency) => currency is not null && settings.AudUnits.ContainsKey(currency.Trim().ToUpperInvariant());

    public Task<ConversionResponse> ConvertAsync(long amountMinor, string fromCurrency, string toCurrency, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return Task.FromResult(Convert(amountMinor, fromCurrency, toCurrency));
    }

    public ConversionResponse Convert(long amountMinor, string fromCurrency, string toCurrency)
    {
        var from = fromCurrency.Trim().ToUpperInvariant();
        var to = toCurrency.Trim().ToUpperInvariant();
        if (amountMinor <= 0 || !settings.AudUnits.TryGetValue(from, out var fromUnits) || !settings.AudUnits.TryGetValue(to, out var toUnits) || fromUnits <= 0 || toUnits <= 0)
        {
            throw new ArgumentException("The amount and currencies must be supported.");
        }

        var rate = toUnits / fromUnits;
        var converted = checked((long)Math.Round(amountMinor * rate, 0, MidpointRounding.AwayFromZero));
        var scaled = checked((long)Math.Round(rate * RateScale, 0, MidpointRounding.AwayFromZero));
        return new(amountMinor, from, converted, to, rate, scaled, settings.RateAsOf, settings.Version, settings.Disclaimer);
    }
}
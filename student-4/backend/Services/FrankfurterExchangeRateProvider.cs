using System.Globalization;
using System.Text.Json;
using BudgetTracker.Backend.Api;

namespace BudgetTracker.Backend.Services;

public sealed class ExchangeRateUnavailableException(Exception? innerException = null)
    : Exception("Reference exchange rates are currently unavailable.", innerException);

public sealed class ExchangeRateResponseException(Exception? innerException = null)
    : Exception("The exchange rate service returned an unusable response.", innerException);

public sealed class FrankfurterExchangeRateProvider(IHttpClientFactory clients, TimeProvider clock) : IExchangeRateProvider
{
    public const string ClientName = "Frankfurter";
    private const string Version = "Frankfurter / ECB";
    private const string Disclaimer = "Daily reference rates; card fees may differ.";
    private const int MaximumResponseBytes = 32 * 1024;
    private static readonly Uri Endpoint = new("https://api.frankfurter.dev/v2/providers/ecb/rates?base=AUD&quotes=USD,EUR,GBP,NZD,CAD,SGD");
    private static readonly TimeSpan RefreshInterval = TimeSpan.FromHours(1);
    private static readonly TimeSpan MaximumCacheAge = TimeSpan.FromHours(24);
    private readonly object _sync = new();
    private RateSnapshot? _snapshot;
    private Task<RateSnapshot>? _refresh;
    private bool _refreshFailed;

    public IReadOnlyList<string> Currencies { get; } = Array.AsReadOnly(new[] { "AUD", "CAD", "EUR", "GBP", "NZD", "SGD", "USD" });

    public ExchangeRateMetadata Metadata
    {
        get
        {
            lock (_sync)
            {
                return new(_snapshot?.RateAsOf, Version, Disclaimer, Status(_snapshot, clock.GetUtcNow()), _snapshot?.FetchedAt);
            }
        }
    }

    public bool Supports(string? currency) => currency is not null && Currencies.Contains(currency.Trim().ToUpperInvariant(), StringComparer.Ordinal);

    public async Task<ConversionResponse> ConvertAsync(long amountMinor, string fromCurrency, string toCurrency, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var from = fromCurrency.Trim().ToUpperInvariant();
        var to = toCurrency.Trim().ToUpperInvariant();
        if (amountMinor <= 0 || !Supports(from) || !Supports(to)) throw new ArgumentException("The amount and currencies must be supported.");
        if (from == to)
        {
            return new(amountMinor, from, amountMinor, to, 1m, 100_000_000, Today(clock.GetUtcNow()), "identity", "No currency conversion required.", "identity");
        }

        var snapshot = await GetSnapshotAsync(cancellationToken);
        try
        {
            var rate = snapshot.AudUnits[to] / snapshot.AudUnits[from];
            var converted = checked((long)Math.Round(amountMinor * rate, 0, MidpointRounding.AwayFromZero));
            var scaled = checked((long)Math.Round(rate * 100_000_000m, 0, MidpointRounding.AwayFromZero));
            if (scaled <= 0) throw new ExchangeRateResponseException();
            lock (_sync)
            {
                return new(amountMinor, from, converted, to, rate, scaled, snapshot.RateAsOf, Version, Disclaimer, Status(snapshot, clock.GetUtcNow()), snapshot.FetchedAt);
            }
        }
        catch (ArithmeticException exception)
        {
            throw new ExchangeRateResponseException(exception);
        }
    }

    private async Task<RateSnapshot> GetSnapshotAsync(CancellationToken cancellationToken)
    {
        Task<RateSnapshot> refresh;
        lock (_sync)
        {
            var now = clock.GetUtcNow();
            if (_snapshot is not null && IsUsable(_snapshot, now) && now - _snapshot.FetchedAt < RefreshInterval) return _snapshot;
            if (_refresh is null || _refresh.IsCompleted) _refresh = RefreshAsync();
            refresh = _refresh;
        }

        try
        {
            return await refresh.WaitAsync(cancellationToken);
        }
        catch (Exception exception) when (exception is ExchangeRateUnavailableException or ExchangeRateResponseException)
        {
            cancellationToken.ThrowIfCancellationRequested();
            lock (_sync)
            {
                if (_snapshot is not null && IsUsable(_snapshot, clock.GetUtcNow())) return _snapshot;
            }
            throw;
        }
    }

    private async Task<RateSnapshot> RefreshAsync()
    {
        try
        {
            var snapshot = await FetchAsync();
            lock (_sync)
            {
                _snapshot = snapshot;
                _refreshFailed = false;
            }
            return snapshot;
        }
        catch
        {
            lock (_sync) _refreshFailed = true;
            throw;
        }
    }

    private async Task<RateSnapshot> FetchAsync()
    {
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(3), clock);
        using var client = clients.CreateClient(ClientName);
        try
        {
            using var response = await client.GetAsync(Endpoint, HttpCompletionOption.ResponseHeadersRead, deadline.Token);
            if (!response.IsSuccessStatusCode) throw new ExchangeRateUnavailableException();
            if (response.Content.Headers.ContentLength > MaximumResponseBytes) throw new ExchangeRateResponseException();
            await using var stream = await response.Content.ReadAsStreamAsync(deadline.Token);
            using var buffer = new MemoryStream();
            var chunk = new byte[4096];
            int read;
            while ((read = await stream.ReadAsync(chunk, deadline.Token)) > 0)
            {
                if (buffer.Length + read > MaximumResponseBytes) throw new ExchangeRateResponseException();
                buffer.Write(chunk, 0, read);
            }

            using var document = JsonDocument.Parse(buffer.ToArray());
            var now = clock.GetUtcNow();
            var units = new Dictionary<string, decimal>(StringComparer.Ordinal) { ["AUD"] = 1m };
            DateOnly? rateDate = null;
            if (document.RootElement.ValueKind != JsonValueKind.Array || document.RootElement.GetArrayLength() != Currencies.Count - 1) throw new ExchangeRateResponseException();
            foreach (var row in document.RootElement.EnumerateArray())
            {
                if (row.ValueKind != JsonValueKind.Object) throw new ExchangeRateResponseException();
                var properties = row.EnumerateObject().Select(value => value.Name).ToArray();
                if (properties.Length != 4 || properties.Distinct(StringComparer.Ordinal).Count() != 4
                    || !row.TryGetProperty("base", out var baseValue) || baseValue.ValueKind != JsonValueKind.String || baseValue.GetString() != "AUD"
                    || !row.TryGetProperty("quote", out var quoteValue) || quoteValue.ValueKind != JsonValueKind.String
                    || !row.TryGetProperty("date", out var dateValue) || dateValue.ValueKind != JsonValueKind.String
                    || !DateOnly.TryParseExact(dateValue.GetString(), "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var date)
                    || !DateIsUsable(date, now) || (rateDate is not null && rateDate != date)
                    || !row.TryGetProperty("rate", out var rateValue) || rateValue.ValueKind != JsonValueKind.Number
                    || !rateValue.TryGetDecimal(out var rate) || rate <= 0) throw new ExchangeRateResponseException();
                var quote = quoteValue.GetString()!;
                if (!Currencies.Contains(quote, StringComparer.Ordinal) || !units.TryAdd(quote, rate)) throw new ExchangeRateResponseException();
                rateDate = date;
            }
            return new(rateDate!.Value, now, units);
        }
        catch (OperationCanceledException exception)
        {
            throw new ExchangeRateUnavailableException(exception);
        }
        catch (HttpRequestException exception)
        {
            throw new ExchangeRateUnavailableException(exception);
        }
        catch (IOException exception)
        {
            throw new ExchangeRateUnavailableException(exception);
        }
        catch (JsonException exception)
        {
            throw new ExchangeRateResponseException(exception);
        }
    }

    private string Status(RateSnapshot? snapshot, DateTimeOffset now) => snapshot is null ? "not_fetched"
        : !IsUsable(snapshot, now) ? "expired"
        : _refreshFailed ? "cached_after_failure"
        : now - snapshot.FetchedAt < RefreshInterval ? "current" : "refresh_due";
    private static bool IsUsable(RateSnapshot snapshot, DateTimeOffset now) => now >= snapshot.FetchedAt && now - snapshot.FetchedAt < MaximumCacheAge && DateIsUsable(snapshot.RateAsOf, now);
    private static bool DateIsUsable(DateOnly date, DateTimeOffset now) => date <= Today(now) && Today(now).DayNumber - date.DayNumber <= 7;
    private static DateOnly Today(DateTimeOffset now) => DateOnly.FromDateTime(now.UtcDateTime);
    private sealed record RateSnapshot(DateOnly RateAsOf, DateTimeOffset FetchedAt, IReadOnlyDictionary<string, decimal> AudUnits);
}
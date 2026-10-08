using System.Net;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using BudgetTracker.Backend.Services;

namespace BudgetTracker.Backend.Tests;

public sealed class FrankfurterExchangeRateProviderTests
{
    [Fact]
    public async Task IdentityAndMetadataNeverFetchAndUseUtcToday()
    {
        var clock = new TestClock();
        var transport = new Transport((_, _) => throw new InvalidOperationException("Unexpected HTTP request."));
        var provider = new FrankfurterExchangeRateProvider(transport, clock);

        Assert.Null(provider.Metadata.RateAsOf);
        Assert.Null(provider.Metadata.FetchedAt);
        Assert.Equal("not_fetched", provider.Metadata.Status);
        Assert.Equal("Frankfurter / ECB", provider.Metadata.RateVersion);
        Assert.Equal("Daily reference rates; card fees may differ.", provider.Metadata.Disclaimer);
        Assert.Equal(new[] { "AUD", "CAD", "EUR", "GBP", "NZD", "SGD", "USD" }, provider.Currencies);
        Assert.False(provider.Supports("JPY"));
        var result = await provider.ConvertAsync(101, "aud", "AUD", CancellationToken.None);

        Assert.Equal(101, result.ConvertedAmountMinor);
        Assert.Equal(1m, result.Rate);
        Assert.Equal(100_000_000, result.RateScaled);
        Assert.Equal(new DateOnly(2026, 10, 8), result.RateAsOf);
        Assert.Equal("identity", result.RateVersion);
        Assert.Null(result.RateFetchedAt);
        Assert.Equal(0, transport.CallCount);
    }

    [Fact]
    public async Task V2EcbSnapshotUsesFixedEndpointDecimalRoundingAndCache()
    {
        var clock = new TestClock();
        var transport = new Transport((request, _) =>
        {
            Assert.Equal("https://api.frankfurter.dev/v2/providers/ecb/rates?base=AUD&quotes=USD,EUR,GBP,NZD,CAD,SGD", request.RequestUri!.AbsoluteUri);
            Assert.Equal(HttpMethod.Get, request.Method);
            return Task.FromResult(Response(Payload()));
        });
        var provider = new FrankfurterExchangeRateProvider(transport, clock);

        var result = await provider.ConvertAsync(101, "USD", "AUD", CancellationToken.None);
        var cross = await provider.ConvertAsync(10000, "USD", "EUR", CancellationToken.None);

        Assert.Equal(145, result.ConvertedAmountMinor);
        Assert.Equal(143857983, result.RateScaled);
        Assert.Equal(0.62193m / 0.69513m, cross.Rate);
        Assert.Equal(8947, cross.ConvertedAmountMinor);
        Assert.Equal(new DateOnly(2026, 10, 7), result.RateAsOf);
        Assert.Equal("Frankfurter / ECB", result.RateVersion);
        Assert.Equal("current", result.RateStatus);
        Assert.Equal(clock.Now, result.RateFetchedAt);
        Assert.Equal(result.RateFetchedAt, provider.Metadata.FetchedAt);
        Assert.Equal(1, transport.CallCount);
    }

    [Fact]
    public async Task ConcurrentRefreshIsCoalescedAndCallerCancellationDoesNotCancelOtherWaiters()
    {
        var release = new TaskCompletionSource<HttpResponseMessage>(TaskCreationOptions.RunContinuationsAsynchronously);
        var transport = new Transport((_, _) => release.Task);
        var provider = new FrankfurterExchangeRateProvider(transport, new TestClock());
        using var cancelled = new CancellationTokenSource();

        var abandoned = provider.ConvertAsync(100, "USD", "AUD", cancelled.Token);
        var waiting = Enumerable.Range(0, 20).Select(_ => provider.ConvertAsync(100, "EUR", "AUD", CancellationToken.None)).ToArray();
        Assert.Equal(1, transport.CallCount);
        cancelled.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => abandoned);
        Assert.False(transport.LastToken.IsCancellationRequested);
        release.SetResult(Response(Payload()));
        var results = await Task.WhenAll(waiting);

        Assert.All(results, value => Assert.Equal("Frankfurter / ECB", value.RateVersion));
        Assert.Equal(1, transport.CallCount);
    }

    [Fact]
    public async Task PreCancelledCallDoesNotFetch()
    {
        var transport = new Transport((_, _) => Task.FromResult(Response(Payload())));
        var provider = new FrankfurterExchangeRateProvider(transport, new TestClock());
        using var cancelled = new CancellationTokenSource();
        cancelled.Cancel();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => provider.ConvertAsync(100, "USD", "AUD", cancelled.Token));

        Assert.Equal(0, transport.CallCount);
    }

    [Fact]
    public async Task DeadlineCancelsFetchAfterThreeSecondsWithoutRealWaiting()
    {
        var clock = new TestClock();
        var transport = new Transport(async (_, token) =>
        {
            await Task.Delay(Timeout.InfiniteTimeSpan, token);
            return Response(Payload());
        });
        var provider = new FrankfurterExchangeRateProvider(transport, clock);

        var conversion = provider.ConvertAsync(100, "USD", "AUD", CancellationToken.None);
        clock.Advance(TimeSpan.FromSeconds(3));

        await Assert.ThrowsAsync<ExchangeRateUnavailableException>(() => conversion);
        Assert.True(transport.LastToken.IsCancellationRequested);
        Assert.Null(provider.Metadata.RateAsOf);
    }

    [Fact]
    public async Task RefreshAfterOneHourReplacesSnapshot()
    {
        var clock = new TestClock();
        var payload = Payload();
        var transport = new Transport((_, _) => Task.FromResult(Response(payload)));
        var provider = new FrankfurterExchangeRateProvider(transport, clock);
        var first = await provider.ConvertAsync(10000, "AUD", "USD", CancellationToken.None);
        clock.Advance(TimeSpan.FromMinutes(59));
        Assert.Equal(first, await provider.ConvertAsync(10000, "AUD", "USD", CancellationToken.None));
        clock.Advance(TimeSpan.FromMinutes(1));
        payload = Payload(usd: 0.7m);

        var refreshed = await provider.ConvertAsync(10000, "AUD", "USD", CancellationToken.None);

        Assert.Equal(7000, refreshed.ConvertedAmountMinor);
        Assert.Equal(clock.Now, refreshed.RateFetchedAt);
        Assert.Equal(2, transport.CallCount);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task FailedRefreshUsesOnlyFreshCacheAndPreservesProvenance(bool invalidResponse)
    {
        var clock = new TestClock();
        var fail = false;
        var transport = new Transport((_, _) => !fail ? Task.FromResult(Response(Payload()))
            : invalidResponse ? Task.FromResult(Response("[]")) : Task.FromException<HttpResponseMessage>(new HttpRequestException()));
        var provider = new FrankfurterExchangeRateProvider(transport, clock);
        var first = await provider.ConvertAsync(100, "USD", "AUD", CancellationToken.None);
        fail = true;
        clock.Advance(TimeSpan.FromHours(1));

        var cached = await provider.ConvertAsync(100, "USD", "AUD", CancellationToken.None);

        Assert.Equal(first.Rate, cached.Rate);
        Assert.Equal(first.RateAsOf, cached.RateAsOf);
        Assert.Equal(first.RateFetchedAt, cached.RateFetchedAt);
        Assert.Equal("Frankfurter / ECB", cached.RateVersion);
        Assert.Equal("cached_after_failure", cached.RateStatus);
        Assert.Equal("cached_after_failure", provider.Metadata.Status);
        clock.Advance(TimeSpan.FromHours(23));
        if (invalidResponse) await Assert.ThrowsAsync<ExchangeRateResponseException>(() => provider.ConvertAsync(100, "USD", "AUD", CancellationToken.None));
        else await Assert.ThrowsAsync<ExchangeRateUnavailableException>(() => provider.ConvertAsync(100, "USD", "AUD", CancellationToken.None));
        Assert.Equal("expired", provider.Metadata.Status);
    }

    [Theory]
    [InlineData("2026-10-05")]
    [InlineData("2026-10-01")]
    public async Task WeekendAndSevenDayOldReferenceDatesAreAccepted(string date)
    {
        var transport = new Transport((_, _) => Task.FromResult(Response(Payload(date))));
        var provider = new FrankfurterExchangeRateProvider(transport, new TestClock());

        var result = await provider.ConvertAsync(100, "USD", "AUD", CancellationToken.None);

        Assert.Equal(DateOnly.Parse(date), result.RateAsOf);
    }

    [Fact]
    public async Task ReferenceDateExpiryPreventsCacheReuseEvenWithinTwentyFourHours()
    {
        var clock = new TestClock();
        clock.Now = new DateTimeOffset(2026, 10, 8, 23, 30, 0, TimeSpan.Zero);
        var transport = new Transport((_, _) => Task.FromResult(Response(Payload("2026-10-01"))));
        var provider = new FrankfurterExchangeRateProvider(transport, clock);
        await provider.ConvertAsync(100, "USD", "AUD", CancellationToken.None);
        clock.Advance(TimeSpan.FromHours(1));

        await Assert.ThrowsAsync<ExchangeRateResponseException>(() => provider.ConvertAsync(100, "USD", "AUD", CancellationToken.None));

        Assert.Equal("expired", provider.Metadata.Status);
    }

    [Theory]
    [MemberData(nameof(InvalidPayloads))]
    public async Task MalformedIncompleteAndInvalidSnapshotsAreRejected(string payload)
    {
        var transport = new Transport((_, _) => Task.FromResult(Response(payload)));
        var provider = new FrankfurterExchangeRateProvider(transport, new TestClock());

        await Assert.ThrowsAsync<ExchangeRateResponseException>(() => provider.ConvertAsync(100, "USD", "AUD", CancellationToken.None));

        Assert.Null(provider.Metadata.RateAsOf);
        Assert.Equal("not_fetched", provider.Metadata.Status);
    }

    [Theory]
    [InlineData(302)]
    [InlineData(429)]
    [InlineData(500)]
    public async Task HttpFailuresDoNotProduceDemoRates(int status)
    {
        var transport = new Transport((_, _) => Task.FromResult(new HttpResponseMessage((HttpStatusCode)status)));
        var provider = new FrankfurterExchangeRateProvider(transport, new TestClock());

        await Assert.ThrowsAsync<ExchangeRateUnavailableException>(() => provider.ConvertAsync(100, "USD", "AUD", CancellationToken.None));

        Assert.Null(provider.Metadata.RateAsOf);
    }

    [Fact]
    public async Task OversizedChunkedResponseIsRejected()
    {
        var transport = new Transport((_, _) => Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StreamContent(new ResponseStream(Encoding.UTF8.GetBytes(new string(' ', 32769))))
        }));
        var provider = new FrankfurterExchangeRateProvider(transport, new TestClock());

        await Assert.ThrowsAsync<ExchangeRateResponseException>(() => provider.ConvertAsync(100, "USD", "AUD", CancellationToken.None));
    }

    [Fact]
    public async Task DeadlineAlsoBoundsStreamedBodyAndNextCallCanRecover()
    {
        var clock = new TestClock();
        var stall = true;
        var transport = new Transport((_, _) => Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StreamContent(new ResponseStream(Encoding.UTF8.GetBytes(Payload()), stall))
        }));
        var provider = new FrankfurterExchangeRateProvider(transport, clock);
        var conversion = provider.ConvertAsync(100, "USD", "AUD", CancellationToken.None);
        clock.Advance(TimeSpan.FromSeconds(3));
        await Assert.ThrowsAsync<ExchangeRateUnavailableException>(() => conversion);
        stall = false;

        var recovered = await provider.ConvertAsync(100, "USD", "AUD", CancellationToken.None);

        Assert.Equal("current", recovered.RateStatus);
        Assert.Equal(2, transport.CallCount);
    }

    [Fact]
    public async Task DeclaredOversizedResponseIsRejected()
    {
        var transport = new Transport((_, _) => Task.FromResult(Response(new string(' ', 32769))));
        var provider = new FrankfurterExchangeRateProvider(transport, new TestClock());

        await Assert.ThrowsAsync<ExchangeRateResponseException>(() => provider.ConvertAsync(100, "USD", "AUD", CancellationToken.None));
    }

    public static IEnumerable<object[]> InvalidPayloads()
    {
        yield return new object[] { "not json" };
        yield return new object[] { "{}" };
        yield return new object[] { "[]" };
        yield return new object[] { Payload("2026-09-30") };
        yield return new object[] { Payload("2026-10-09") };
        yield return new object[] { Payload("not-a-date") };
        yield return new object[] { Payload(usd: 0m) };
        yield return new object[] { Payload(usd: -1m) };
        foreach (var (field, value) in new (string, JsonNode?)[]
        {
            ("base", JsonValue.Create("USD")), ("base", JsonValue.Create(42)),
            ("quote", JsonValue.Create("JPY")), ("quote", JsonValue.Create("AUD")),
            ("quote", JsonValue.Create("EUR")), ("quote", JsonValue.Create("usd")),
            ("date", JsonValue.Create("2026-10-06")), ("rate", JsonValue.Create("0.7")), ("rate", null)
        })
        {
            var rows = JsonNode.Parse(Payload())!;
            rows[0]![field] = value;
            yield return new object[] { rows.ToJsonString() };
        }
        yield return new object[] { Payload().Replace("\"rate\":0.69513", "\"rate\":1e100", StringComparison.Ordinal) };
        yield return new object[] { Payload().Replace("\"rate\":0.69513", "\"rate\":0.69513,\"rate\":0.7", StringComparison.Ordinal) };
        var missing = JsonNode.Parse(Payload())!.AsArray();
        missing.RemoveAt(0);
        yield return new object[] { missing.ToJsonString() };
        var missingField = JsonNode.Parse(Payload())!;
        missingField[0]!.AsObject().Remove("rate");
        yield return new object[] { missingField.ToJsonString() };
    }

    private static string Payload(string date = "2026-10-07", decimal usd = 0.69513m) => JsonSerializer.Serialize(new[]
    {
        new { date, @base = "AUD", quote = "USD", rate = usd },
        new { date, @base = "AUD", quote = "EUR", rate = 0.62193m },
        new { date, @base = "AUD", quote = "GBP", rate = 0.52643m },
        new { date, @base = "AUD", quote = "NZD", rate = 1.2424m },
        new { date, @base = "AUD", quote = "CAD", rate = 0.94m },
        new { date, @base = "AUD", quote = "SGD", rate = 0.90m }
    });

    private static HttpResponseMessage Response(string payload) => new(HttpStatusCode.OK) { Content = new StringContent(payload, Encoding.UTF8, "application/json") };

    private sealed class ResponseStream(byte[] payload, bool stall = false) : Stream
    {
        private readonly MemoryStream _source = new(payload);
        public override bool CanRead => true;
        public override bool CanSeek => false;
        public override bool CanWrite => false;
        public override long Length => throw new NotSupportedException();
        public override long Position { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }
        public override int Read(byte[] buffer, int offset, int count) => _source.Read(buffer, offset, count);
        public override async ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default)
        {
            if (stall) await Task.Delay(Timeout.InfiniteTimeSpan, cancellationToken);
            return await _source.ReadAsync(buffer, cancellationToken);
        }
        public override void Flush() => throw new NotSupportedException();
        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();
        public override void SetLength(long value) => throw new NotSupportedException();
        public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();
        protected override void Dispose(bool disposing) { if (disposing) _source.Dispose(); base.Dispose(disposing); }
    }

    private sealed class Transport(Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> send) : HttpMessageHandler, IHttpClientFactory
    {
        public int CallCount { get; private set; }
        public CancellationToken LastToken { get; private set; }
        public HttpClient CreateClient(string name)
        {
            Assert.Equal(FrankfurterExchangeRateProvider.ClientName, name);
            return new(this, disposeHandler: false) { Timeout = Timeout.InfiniteTimeSpan };
        }
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            CallCount++;
            LastToken = cancellationToken;
            return send(request, cancellationToken);
        }
    }

    private sealed class TestClock : TimeProvider
    {
        private readonly List<TestTimer> _timers = [];
        public DateTimeOffset Now { get; set; } = new(2026, 10, 8, 12, 0, 0, TimeSpan.Zero);
        public override DateTimeOffset GetUtcNow() => Now;
        public override ITimer CreateTimer(TimerCallback callback, object? state, TimeSpan dueTime, TimeSpan period)
        {
            var timer = new TestTimer(this, callback, state, dueTime);
            _timers.Add(timer);
            return timer;
        }
        public void Advance(TimeSpan duration)
        {
            Now += duration;
            foreach (var timer in _timers.ToArray()) timer.FireIfDue();
        }
        private sealed class TestTimer(TestClock clock, TimerCallback callback, object? state, TimeSpan dueTime) : ITimer
        {
            private DateTimeOffset _due = clock.Now + dueTime;
            private bool _disposed;
            public void FireIfDue()
            {
                if (!_disposed && clock.Now >= _due)
                {
                    _disposed = true;
                    callback(state);
                }
            }
            public bool Change(TimeSpan dueTime, TimeSpan period) { _due = clock.Now + dueTime; return !_disposed; }
            public void Dispose() => _disposed = true;
            public ValueTask DisposeAsync() { Dispose(); return ValueTask.CompletedTask; }
        }
    }
}
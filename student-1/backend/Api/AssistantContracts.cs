namespace Accommodation.Backend.Api;

public static class AssistantTools
{
    public const string Find = "accommodation.find";
    public const string GetSearch = "accommodation.get_search";

    public static readonly IReadOnlySet<string> Allowed = new HashSet<string>(StringComparer.Ordinal)
    {
        Find,
        GetSearch
    };
}

public enum AssistantFailure
{
    NotUnderstood,
    SearchNotFound,
    Unavailable,
    Timeout,
    InvalidResponse
}

public sealed class AssistantException(AssistantFailure failure, string dependency, Exception? inner = null)
    : Exception($"{dependency} failed: {failure}", inner)
{
    public AssistantFailure Failure { get; } = failure;

    public string Dependency { get; } = dependency;
}

public sealed record LookupCall(string Tool, IReadOnlyDictionary<string, object> Arguments);

public sealed record LookupResponse(
    string Mode,
    string Tool,
    IReadOnlyDictionary<string, object> Arguments,
    object Result);

namespace Accommodation.Backend.Api;

public sealed record AiModes(
    bool RankingEnabled,
    bool LookupEnabled,
    bool GuideEnabled,
    bool MultiAgentEnabled)
{
    public static AiModes FromConfiguration(IConfiguration configuration)
    {
        return new AiModes(
            ReadFlag(configuration, "AI_ENABLED"),
            ReadFlag(configuration, "MCP_ENABLED"),
            ReadFlag(configuration, "RAG_ENABLED"),
            ReadFlag(configuration, "MULTI_AGENT_ENABLED"));
    }

    private static bool ReadFlag(IConfiguration configuration, string name)
    {
        return configuration[name] switch
        {
            null or "false" => false,
            "true" => true,
            _ => throw new InvalidOperationException($"{name} must be true or false.")
        };
    }
}

using Microsoft.Extensions.Configuration;

namespace BudgetTracker.Backend.Services;

public sealed record FeatureModeSettings(bool AiEnabled, bool McpEnabled, bool RagEnabled)
{
    public static FeatureModeSettings FromConfiguration(IConfiguration configuration) => new(
        ReadFlag(configuration, "AI_ENABLED", true),
        ReadFlag(configuration, "MCP_ENABLED", false),
        ReadFlag(configuration, "RAG_ENABLED", false));

    private static bool ReadFlag(IConfiguration configuration, string name, bool defaultValue)
    {
        var value = configuration[name];
        if (value is null) return defaultValue;

        return value switch
        {
            "true" => true,
            "false" => false,
            _ => throw new InvalidOperationException($"Configuration value '{name}' must be exactly 'true' or 'false'.")
        };
    }
}
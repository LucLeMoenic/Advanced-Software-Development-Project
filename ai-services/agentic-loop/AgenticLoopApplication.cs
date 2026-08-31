using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace AgenticLoop;

public static partial class AgenticLoopApplication
{
    private const int MaxTaskCharacters = 4_000;
    private const int MaxContextBytes = 16_000;
    private const int MaxContextFileBytes = 8_000;
    internal const int OllamaContextTokens = 8_192;
    internal const int OllamaMaxOutputTokens = 2_048;
    internal const double OllamaTemperature = 0;
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        WriteIndented = true
    };

    public static async Task<int> RunAsync(string[] args)
    {
        if (args.Length == 0)
        {
            WriteUsage();
            return 1;
        }

        try
        {
            return args[0] switch
            {
                "serve" => await ServeAsync(),
                "healthcheck" => await CheckHealthAsync(),
                "run" => await RunLoopAsync(ParsedArguments.Parse(args[1..])),
                "finalise" => await FinaliseAsync(ParsedArguments.Parse(args[1..])),
                _ => throw new LoopException($"Unknown command: {args[0]}")
            };
        }
        catch (LoopException exception)
        {
            Console.Error.WriteLine($"error: {exception.Message}");
            return 1;
        }
        catch (OperationCanceledException)
        {
            Console.Error.WriteLine("error: operation timed out or was cancelled");
            return 1;
        }
        catch (HttpRequestException exception)
        {
            Console.Error.WriteLine($"error: Ollama request failed: {exception.Message}");
            return 1;
        }
        catch (IOException exception)
        {
            Console.Error.WriteLine($"error: file operation failed: {exception.Message}");
            return 1;
        }
        catch (UnauthorizedAccessException exception)
        {
            Console.Error.WriteLine($"error: file access denied: {exception.Message}");
            return 1;
        }
        catch (JsonException exception)
        {
            Console.Error.WriteLine($"error: invalid JSON response: {exception.Message}");
            return 1;
        }
        catch (NotSupportedException exception)
        {
            Console.Error.WriteLine($"error: unsupported response content: {exception.Message}");
            return 1;
        }
    }

    private static async Task<int> ServeAsync()
    {
        var builder = WebApplication.CreateSlimBuilder();
        var app = builder.Build();

        app.MapGet("/health", async () =>
        {
            var implementerModel = Environment.GetEnvironmentVariable("IMPLEMENTER_MODEL");
            var reviewerModel = Environment.GetEnvironmentVariable("REVIEWER_MODEL");
            if (string.IsNullOrWhiteSpace(implementerModel)
                || string.IsNullOrWhiteSpace(reviewerModel)
                || string.Equals(implementerModel, reviewerModel, StringComparison.Ordinal))
            {
                return Results.Json(
                    new { status = "unhealthy", reason = "Model roles are missing or equal." },
                    statusCode: StatusCodes.Status503ServiceUnavailable);
            }

            try
            {
                using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(5) };
                IModelClient ollama = new OllamaClient(
                    client,
                    Environment.GetEnvironmentVariable("OLLAMA_URL")
                        ?? "http://ollama:11434");
                var models = await ollama.GetAvailableModelsAsync();
                var missing = new[] { implementerModel, reviewerModel }
                    .Where(model => !models.Contains(NormaliseModelName(model)))
                    .ToArray();
                return missing.Length == 0
                    ? Results.Ok(new
                    {
                        status = "healthy",
                        implementerModel,
                        reviewerModel
                    })
                    : Results.Json(
                        new
                        {
                            status = "unhealthy",
                            reason = $"Missing models: {string.Join(", ", missing)}"
                        },
                        statusCode: StatusCodes.Status503ServiceUnavailable);
            }
            catch (Exception exception) when (
                exception is HttpRequestException
                or OperationCanceledException
                or JsonException
                or LoopException)
            {
                return Results.Json(
                    new { status = "unhealthy", reason = exception.Message },
                    statusCode: StatusCodes.Status503ServiceUnavailable);
            }
        });

        await app.RunAsync();
        return 0;
    }

    private static async Task<int> CheckHealthAsync()
    {
        var healthUrl = Environment.GetEnvironmentVariable("AGENTIC_LOOP_HEALTH_URL")
            ?? "http://localhost:8080/health";
        using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(2) };
        using var response = await client.GetAsync(healthUrl);
        return response.IsSuccessStatusCode ? 0 : 1;
    }

    private static async Task<int> RunLoopAsync(ParsedArguments arguments)
    {
        var task = arguments.RequiredSingle("task");
        var contextPaths = arguments.RequiredMany("context");
        var workspace = Path.GetFullPath(arguments.SingleOrDefault("workspace") ?? "/workspace");
        var recordDirectory = Path.GetFullPath(
            arguments.SingleOrDefault("record-directory")
            ?? Path.Combine(workspace, "docs", "agentic-loop-records"));
        var implementerModel = arguments.SingleOrDefault("implementer-model")
            ?? Environment.GetEnvironmentVariable("IMPLEMENTER_MODEL");
        var reviewerModel = arguments.SingleOrDefault("reviewer-model")
            ?? Environment.GetEnvironmentVariable("REVIEWER_MODEL");
        var implementerPromptPath = arguments.SingleOrDefault("implementer-prompt")
            ?? "/app/prompts/implementer.md";
        var reviewerPromptPath = arguments.SingleOrDefault("reviewer-prompt")
            ?? "/app/prompts/reviewer.md";
        var preTestCommand = arguments.RequiredSingle("pre-test-command");
        var preTestResult = arguments.RequiredSingle("pre-test-result");
        var ollamaUrl = arguments.SingleOrDefault("ollama-url")
            ?? Environment.GetEnvironmentVariable("OLLAMA_URL")
            ?? "http://ollama:11434";
        var timeoutSeconds = arguments.OptionalPositiveInt("timeout-seconds", 600);

        ValidateRunInput(task, contextPaths, implementerModel, reviewerModel);
        var context = await LoadContextAsync(workspace, contextPaths);
        var implementerPrompt = await ReadRequiredTextAsync(implementerPromptPath, "Implementer prompt");
        var reviewerPrompt = await ReadRequiredTextAsync(reviewerPromptPath, "Reviewer prompt");

        using var httpClient = new HttpClient { Timeout = TimeSpan.FromSeconds(timeoutSeconds) };
        IModelClient ollama = new OllamaClient(httpClient, ollamaUrl);
        var record = await ExecuteLoopAsync(
            new LoopExecutionInput(
                task,
                context,
                implementerModel!,
                reviewerModel!,
                implementerPromptPath,
                reviewerPromptPath,
                implementerPrompt,
                reviewerPrompt,
                preTestCommand,
                preTestResult),
            ollama);

        var recordPath = await WriteRecordAsync(recordDirectory, record);
        Console.WriteLine($"Agentic-loop record awaiting human finalisation: {recordPath}");
        return 0;
    }

    private static async Task<int> FinaliseAsync(ParsedArguments arguments)
    {
        var recordPath = Path.GetFullPath(arguments.RequiredSingle("record"));
        var decision = arguments.RequiredSingle("decision");
        var notes = arguments.RequiredSingle("notes");
        var postTestCommand = arguments.RequiredSingle("post-test-command");
        var postTestResult = arguments.RequiredSingle("post-test-result");

        await FinaliseRecordAsync(
            recordPath,
            decision,
            notes,
            postTestCommand,
            postTestResult);
        Console.WriteLine($"Finalised agentic-loop record: {recordPath}");
        return 0;
    }

    internal static async Task FinaliseRecordAsync(
        string recordPath,
        string decision,
        string notes,
        string postTestCommand,
        string postTestResult)
    {
        if (decision is not ("kept" or "changed" or "rejected"))
        {
            throw new LoopException("Decision must be kept, changed, or rejected.");
        }
        if (string.IsNullOrWhiteSpace(notes))
        {
            throw new LoopException("Human notes are required.");
        }
        if (string.IsNullOrWhiteSpace(postTestCommand)
            || string.IsNullOrWhiteSpace(postTestResult))
        {
            throw new LoopException("A post-test command and result are required.");
        }

        AgenticLoopRecord record;
        try
        {
            await using var stream = File.OpenRead(recordPath);
            record = await JsonSerializer.DeserializeAsync<AgenticLoopRecord>(stream, JsonOptions)
                ?? throw new LoopException("Record is empty.");
        }
        catch (FileNotFoundException exception)
        {
            throw new LoopException($"Record does not exist: {recordPath}", exception);
        }
        catch (JsonException exception)
        {
            throw new LoopException($"Record contains invalid JSON: {recordPath}", exception);
        }

        if (record.SchemaVersion != 1)
        {
            throw new LoopException("Record has an unsupported schema.");
        }
        if (record.HumanDecision is not null)
        {
            throw new LoopException("Record has already been finalised.");
        }

        var finalised = record with
        {
            HumanDecision = decision,
            HumanNotes = notes,
            PostTest = new TestEvidence(postTestCommand, postTestResult),
            FinalisedAt = DateTimeOffset.UtcNow
        };

        await WriteTextAtomicallyAsync(
            recordPath,
            JsonSerializer.Serialize(finalised, JsonOptions) + Environment.NewLine);
    }

    internal static void ValidateRunInput(
        string task,
        IReadOnlyCollection<string> contextPaths,
        string? implementerModel,
        string? reviewerModel)
    {
        if (string.IsNullOrWhiteSpace(task))
        {
            throw new LoopException("Task must not be empty.");
        }
        if (task.Length > MaxTaskCharacters)
        {
            throw new LoopException($"Task exceeds {MaxTaskCharacters} characters.");
        }
        if (contextPaths.Count == 0)
        {
            throw new LoopException("At least one context file is required.");
        }
        if (string.IsNullOrWhiteSpace(implementerModel) || string.IsNullOrWhiteSpace(reviewerModel))
        {
            throw new LoopException("IMPLEMENTER_MODEL and REVIEWER_MODEL are required.");
        }
        if (string.Equals(implementerModel, reviewerModel, StringComparison.Ordinal))
        {
            throw new LoopException("Implementer and reviewer models must be different.");
        }
    }

    internal static async Task<LoadedContext> LoadContextAsync(
        string workspace,
        IReadOnlyCollection<string> requestedPaths)
    {
        var workspacePath = Path.GetFullPath(workspace)
            .TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        var selectedPaths = new List<string>();
        var hashes = new Dictionary<string, string>(StringComparer.Ordinal);
        var content = new StringBuilder();
        var totalBytes = 0;

        foreach (var requestedPath in requestedPaths)
        {
            var candidate = Path.GetFullPath(Path.Combine(workspacePath, requestedPath));
            if (!IsInsideWorkspace(workspacePath, candidate))
            {
                throw new LoopException($"Context path escapes the workspace: {requestedPath}");
            }

            var relativePath = Path.GetRelativePath(workspacePath, candidate);
            if (IsSensitivePath(relativePath))
            {
                throw new LoopException($"Sensitive context path is not allowed: {requestedPath}");
            }
            if (!IsAllowedContextPath(relativePath))
            {
                throw new LoopException($"Context file type is not allowed: {requestedPath}");
            }
            if (!File.Exists(candidate))
            {
                throw new LoopException($"Context file does not exist: {requestedPath}");
            }

            var linkTarget = new FileInfo(candidate).ResolveLinkTarget(returnFinalTarget: true);
            if (linkTarget is not null)
            {
                candidate = Path.GetFullPath(linkTarget.FullName);
                if (!IsInsideWorkspace(workspacePath, candidate))
                {
                    throw new LoopException(
                        $"Context symbolic link escapes the workspace: {requestedPath}");
                }
            }

            var bytes = await File.ReadAllBytesAsync(candidate);
            if (bytes.Length > MaxContextFileBytes)
            {
                throw new LoopException(
                    $"Context file exceeds {MaxContextFileBytes} bytes: {requestedPath}");
            }
            if (bytes.Contains((byte)0))
            {
                throw new LoopException($"Binary context file is not allowed: {requestedPath}");
            }

            totalBytes += bytes.Length;
            if (totalBytes > MaxContextBytes)
            {
                throw new LoopException($"Combined context exceeds {MaxContextBytes} bytes.");
            }

            string text;
            try
            {
                text = new UTF8Encoding(false, true).GetString(bytes);
            }
            catch (DecoderFallbackException exception)
            {
                throw new LoopException(
                    $"Context file is not valid UTF-8: {requestedPath}", exception);
            }

            var normalisedPath = relativePath.Replace(Path.DirectorySeparatorChar, '/');
            selectedPaths.Add(normalisedPath);
            hashes[normalisedPath] = Convert.ToHexString(SHA256.HashData(bytes));
            content.AppendLine($"FILE: {normalisedPath}");
            content.AppendLine(text);
            content.AppendLine("END_FILE");
            content.AppendLine();
        }

        return new LoadedContext(selectedPaths, hashes, content.ToString());
    }

    internal static string ParseVerdict(string review)
    {
        var observeIndex = review.IndexOf("[OBSERVE]", StringComparison.Ordinal);
        if (observeIndex < 0)
        {
            throw new LoopException("Reviewer output does not contain an [OBSERVE] section.");
        }

        var matches = VerdictRegex().Matches(review[observeIndex..]);
        if (matches.Count != 1)
        {
            throw new LoopException("Reviewer output must contain exactly one valid Verdict line.");
        }

        return matches[0].Groups[1].Value.ToUpperInvariant();
    }

    internal static async Task<AgenticLoopRecord> ExecuteLoopAsync(
        LoopExecutionInput input,
        IModelClient modelClient)
    {
        var availableModels = await modelClient.GetAvailableModelsAsync();
        var runtimeVersion = await modelClient.GetRuntimeVersionAsync();
        var missingModels = new[] { input.ImplementerModel, input.ReviewerModel }
            .Where(model => !availableModels.Contains(NormaliseModelName(model)))
            .ToArray();
        if (missingModels.Length > 0)
        {
            throw new LoopException(
                $"Required Ollama models are unavailable: {string.Join(", ", missingModels)}");
        }

        var planMarker = $"CONTEXT_{Guid.NewGuid():N}";
        var planActPrompt = $"""
            {input.ImplementerPrompt}

            TASK
            {input.Task}
            END_TASK

            {planMarker}
            {input.Context.Content}
            END_{planMarker}

            PRE_TEST_COMMAND
            {input.PreTestCommand}
            END_PRE_TEST_COMMAND

            PRE_TEST_RESULT
            {input.PreTestResult}
            END_PRE_TEST_RESULT
            """;

        Console.WriteLine("[PLAN] Implementer model analysing task.");
        Console.WriteLine("[ACT] Implementer model producing proposal.");
        var implementation = await modelClient.GenerateAsync(
            input.ImplementerModel,
            planActPrompt);
        Console.WriteLine(implementation);

        var reviewMarker = $"REVIEW_DATA_{Guid.NewGuid():N}";
        var reviewPrompt = $"""
            {input.ReviewerPrompt}

            GOAL
            {input.Task}
            END_GOAL

            {reviewMarker}_CONTEXT
            {input.Context.Content}
            END_{reviewMarker}_CONTEXT

            {reviewMarker}_IMPLEMENTER_PROPOSAL
            {implementation}
            END_{reviewMarker}_IMPLEMENTER_PROPOSAL

            PRE_TEST_RESULT
            {input.PreTestResult}
            END_PRE_TEST_RESULT
            """;

        Console.WriteLine("[OBSERVE] Reviewer model assessing proposal.");
        var review = await modelClient.GenerateAsync(input.ReviewerModel, reviewPrompt);
        Console.WriteLine(review);
        var verdict = ParseVerdict(review);

        string? adaptedProposal = null;
        string? adaptedProposalReview = null;
        string finalReviewerVerdict = verdict;
        if (verdict == "REVISE")
        {
            var adaptMarker = $"ADAPT_DATA_{Guid.NewGuid():N}";
            var adaptPrompt = $"""
                {input.ImplementerPrompt}

                ORIGINAL_TASK
                {input.Task}
                END_ORIGINAL_TASK

                {adaptMarker}_ORIGINAL_PROPOSAL
                {implementation}
                END_{adaptMarker}_ORIGINAL_PROPOSAL

                {adaptMarker}_REVIEW_FINDINGS
                {review}
                END_{adaptMarker}_REVIEW_FINDINGS

                Produce one bounded revision that addresses every blocking and required finding.
                Do not expand the original scope.
                """;

            Console.WriteLine("[ADAPT] Implementer model producing one bounded revision.");
            adaptedProposal = await modelClient.GenerateAsync(
                input.ImplementerModel,
                adaptPrompt);
            Console.WriteLine(adaptedProposal);

            var finalReviewMarker = $"FINAL_REVIEW_DATA_{Guid.NewGuid():N}";
            var finalReviewPrompt = $"""
                {input.ReviewerPrompt}

                GOAL
                {input.Task}
                END_GOAL

                {finalReviewMarker}_ORIGINAL_FINDINGS
                {review}
                END_{finalReviewMarker}_ORIGINAL_FINDINGS

                {finalReviewMarker}_ADAPTED_PROPOSAL
                {adaptedProposal}
                END_{finalReviewMarker}_ADAPTED_PROPOSAL

                Review whether the adapted proposal resolved every blocking and required finding.
                """;

            Console.WriteLine("[OBSERVE] Reviewer model assessing the adapted proposal.");
            adaptedProposalReview = await modelClient.GenerateAsync(
                input.ReviewerModel,
                finalReviewPrompt);
            Console.WriteLine(adaptedProposalReview);
            finalReviewerVerdict = ParseVerdict(adaptedProposalReview);
        }
        else
        {
            Console.WriteLine(
                $"[ADAPT] No model revision generated because reviewer verdict is {verdict}.");
        }

        return new AgenticLoopRecord(
            SchemaVersion: 1,
            CreatedAt: DateTimeOffset.UtcNow,
            Task: input.Task,
            ContextFiles: input.Context.Paths,
            Models: new ModelRoles(input.ImplementerModel, input.ReviewerModel),
            PromptFiles: new PromptFiles(
                input.ImplementerPromptPath,
                input.ReviewerPromptPath),
            EvidenceHashes: new EvidenceHashes(
                input.Context.Sha256ByPath,
                HashText(input.ImplementerPrompt),
                HashText(input.ReviewerPrompt)),
            GenerationOptions: new GenerationOptions(
                OllamaContextTokens,
                OllamaMaxOutputTokens,
                OllamaTemperature),
            OllamaVersion: runtimeVersion,
            PreTest: new TestEvidence(input.PreTestCommand, input.PreTestResult),
            PlanAct: implementation,
            Observe: review,
            ReviewerVerdict: verdict,
            AdaptedProposal: adaptedProposal,
            AdaptedProposalReview: adaptedProposalReview,
            FinalReviewerVerdict: finalReviewerVerdict,
            HumanDecision: null,
            HumanNotes: null,
            PostTest: null,
            FinalisedAt: null);
    }

    private static bool IsInsideWorkspace(string workspace, string candidate)
    {
        var comparison = OperatingSystem.IsWindows()
            ? StringComparison.OrdinalIgnoreCase
            : StringComparison.Ordinal;
        return candidate.Equals(workspace, comparison)
            || candidate.StartsWith(workspace + Path.DirectorySeparatorChar, comparison)
            || candidate.StartsWith(workspace + Path.AltDirectorySeparatorChar, comparison);
    }

    private static bool IsSensitivePath(string relativePath)
    {
        var parts = relativePath
            .Split([Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar])
            .Select(part => part.ToLowerInvariant())
            .ToArray();
        var fileName = parts[^1];
        var extension = Path.GetExtension(fileName);

        return parts.Contains(".git")
            || fileName == ".env"
            || fileName.StartsWith(".env.", StringComparison.Ordinal)
            || fileName is "credentials.json" or "secrets.json" or "id_rsa" or "id_ed25519"
            || extension is ".key" or ".pem" or ".pfx" or ".p12";
    }

    private static bool IsAllowedContextPath(string relativePath)
    {
        var fileName = Path.GetFileName(relativePath);
        var extension = Path.GetExtension(fileName).ToLowerInvariant();
        return fileName is "Dockerfile" or ".gitignore"
            || extension is ".md"
                or ".cs"
                or ".csproj"
                or ".ts"
                or ".tsx"
                or ".vue"
                or ".json"
                or ".yml"
                or ".yaml"
                or ".ps1"
                or ".html"
                or ".css"
                or ".txt"
                or ".xml"
                or ".props"
                or ".targets";
    }

    internal static string NormaliseModelName(string model)
    {
        return model.Contains(':', StringComparison.Ordinal) ? model : $"{model}:latest";
    }

    private static string HashText(string value)
    {
        return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
    }

    private static async Task<string> ReadRequiredTextAsync(string path, string description)
    {
        if (!File.Exists(path))
        {
            throw new LoopException($"{description} does not exist: {path}");
        }

        return await File.ReadAllTextAsync(path);
    }

    private static async Task<string> WriteRecordAsync(
        string recordDirectory,
        AgenticLoopRecord record)
    {
        Directory.CreateDirectory(recordDirectory);
        var fileName = $"{DateTimeOffset.UtcNow:yyyyMMddTHHmmssZ}-{Guid.NewGuid():N}.json";
        var path = Path.Combine(recordDirectory, fileName);
        await WriteTextAtomicallyAsync(
            path,
            JsonSerializer.Serialize(record, JsonOptions) + Environment.NewLine);
        return path;
    }

    private static async Task WriteTextAtomicallyAsync(string path, string content)
    {
        var temporaryPath = $"{path}.{Guid.NewGuid():N}.tmp";
        try
        {
            await File.WriteAllTextAsync(temporaryPath, content);
            File.Move(temporaryPath, path, overwrite: true);
        }
        finally
        {
            if (File.Exists(temporaryPath))
            {
                File.Delete(temporaryPath);
            }
        }
    }

    private static void WriteUsage()
    {
        Console.Error.WriteLine("Usage: AgenticLoop <serve|healthcheck|run|finalise> [options]");
    }

    [GeneratedRegex(
        @"^\s*Verdict:\s*(ACCEPT|REVISE|REJECT)\s*$",
        RegexOptions.IgnoreCase | RegexOptions.Multiline)]
    private static partial Regex VerdictRegex();
}

internal interface IModelClient
{
    Task<HashSet<string>> GetAvailableModelsAsync();

    Task<string> GetRuntimeVersionAsync();

    Task<string> GenerateAsync(string model, string prompt);
}

internal sealed class OllamaClient(HttpClient httpClient, string baseUrl) : IModelClient
{
    private readonly string _baseUrl = baseUrl.TrimEnd('/');

    public async Task<HashSet<string>> GetAvailableModelsAsync()
    {
        using var response = await httpClient.GetAsync($"{_baseUrl}/api/tags");
        await EnsureSuccessAsync(response);
        var payload = await response.Content.ReadFromJsonAsync<OllamaTagsResponse>()
            ?? throw new LoopException("Ollama returned an empty model list.");
        if (payload.Models is null)
        {
            throw new LoopException("Ollama returned an invalid model list.");
        }

        return payload.Models
            .Where(model => !string.IsNullOrWhiteSpace(model.Name))
            .Select(model => model.Name)
            .ToHashSet(StringComparer.Ordinal);
    }

    public async Task<string> GetRuntimeVersionAsync()
    {
        using var response = await httpClient.GetAsync($"{_baseUrl}/api/version");
        await EnsureSuccessAsync(response);
        var payload = await response.Content.ReadFromJsonAsync<OllamaVersionResponse>()
            ?? throw new LoopException("Ollama returned an empty version response.");
        return !string.IsNullOrWhiteSpace(payload.Version)
            ? payload.Version
            : throw new LoopException("Ollama returned an invalid version response.");
    }

    public async Task<string> GenerateAsync(string model, string prompt)
    {
        using var response = await httpClient.PostAsJsonAsync(
            $"{_baseUrl}/api/generate",
            new
            {
                model = AgenticLoopApplication.NormaliseModelName(model),
                prompt,
                stream = false,
                options = new
                {
                    num_ctx = AgenticLoopApplication.OllamaContextTokens,
                    num_predict = AgenticLoopApplication.OllamaMaxOutputTokens,
                    temperature = AgenticLoopApplication.OllamaTemperature
                }
            });
        await EnsureSuccessAsync(response);
        var payload = await response.Content.ReadFromJsonAsync<OllamaGenerateResponse>()
            ?? throw new LoopException($"Model {model} returned an empty response.");
        if (string.IsNullOrWhiteSpace(payload.Response))
        {
            throw new LoopException($"Model {model} returned an empty response.");
        }

        return payload.Response.Trim();
    }

    private static async Task EnsureSuccessAsync(HttpResponseMessage response)
    {
        if (response.IsSuccessStatusCode)
        {
            return;
        }

        var body = await response.Content.ReadAsStringAsync();
        throw new LoopException($"Ollama returned HTTP {(int)response.StatusCode}: {body}");
    }
}

internal sealed class ParsedArguments
{
    private readonly Dictionary<string, List<string>> _values;

    private ParsedArguments(Dictionary<string, List<string>> values)
    {
        _values = values;
    }

    public static ParsedArguments Parse(string[] args)
    {
        var values = new Dictionary<string, List<string>>(StringComparer.Ordinal);
        for (var index = 0; index < args.Length; index += 2)
        {
            if (!args[index].StartsWith("--", StringComparison.Ordinal) || index + 1 >= args.Length)
            {
                throw new LoopException($"Invalid argument near: {args[index]}");
            }

            var name = args[index][2..];
            if (!values.TryGetValue(name, out var entries))
            {
                entries = [];
                values[name] = entries;
            }
            entries.Add(args[index + 1]);
        }

        return new ParsedArguments(values);
    }

    public string RequiredSingle(string name)
    {
        var value = SingleOrDefault(name);
        return !string.IsNullOrWhiteSpace(value)
            ? value
            : throw new LoopException($"--{name} is required.");
    }

    public IReadOnlyList<string> RequiredMany(string name)
    {
        return _values.TryGetValue(name, out var values) && values.Count > 0
            ? values
            : throw new LoopException($"At least one --{name} value is required.");
    }

    public string? SingleOrDefault(string name)
    {
        if (!_values.TryGetValue(name, out var values))
        {
            return null;
        }
        if (values.Count != 1)
        {
            throw new LoopException($"--{name} may be specified only once.");
        }

        return values[0];
    }

    public int OptionalPositiveInt(string name, int defaultValue)
    {
        var value = SingleOrDefault(name);
        if (value is null)
        {
            return defaultValue;
        }
        if (!int.TryParse(value, out var parsed) || parsed <= 0)
        {
            throw new LoopException($"--{name} must be a positive integer.");
        }

        return parsed;
    }
}

public sealed class LoopException : Exception
{
    public LoopException(string message)
        : base(message)
    {
    }

    public LoopException(string message, Exception innerException)
        : base(message, innerException)
    {
    }
}

internal sealed record LoadedContext(
    IReadOnlyList<string> Paths,
    IReadOnlyDictionary<string, string> Sha256ByPath,
    string Content);
internal sealed record LoopExecutionInput(
    string Task,
    LoadedContext Context,
    string ImplementerModel,
    string ReviewerModel,
    string ImplementerPromptPath,
    string ReviewerPromptPath,
    string ImplementerPrompt,
    string ReviewerPrompt,
    string PreTestCommand,
    string PreTestResult);
internal sealed record ModelRoles(string Implementer, string Reviewer);
internal sealed record PromptFiles(string Implementer, string Reviewer);
internal sealed record TestEvidence(string Command, string Result);
internal sealed record EvidenceHashes(
    IReadOnlyDictionary<string, string> ContextSha256,
    string ImplementerPromptSha256,
    string ReviewerPromptSha256);
internal sealed record GenerationOptions(
    int ContextTokens,
    int MaxOutputTokens,
    double Temperature);

internal sealed record AgenticLoopRecord(
    int SchemaVersion,
    DateTimeOffset CreatedAt,
    string Task,
    IReadOnlyList<string> ContextFiles,
    ModelRoles Models,
    PromptFiles PromptFiles,
    EvidenceHashes EvidenceHashes,
    GenerationOptions GenerationOptions,
    string OllamaVersion,
    TestEvidence PreTest,
    string PlanAct,
    string Observe,
    string ReviewerVerdict,
    string? AdaptedProposal,
    string? AdaptedProposalReview,
    string FinalReviewerVerdict,
    string? HumanDecision,
    string? HumanNotes,
    TestEvidence? PostTest,
    DateTimeOffset? FinalisedAt);

internal sealed record OllamaTagsResponse(IReadOnlyList<OllamaModel>? Models);
internal sealed record OllamaModel(string Name);
internal sealed record OllamaGenerateResponse(string? Response);
internal sealed record OllamaVersionResponse(string? Version);

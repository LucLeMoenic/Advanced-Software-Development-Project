namespace BudgetTracker.Database.Data;

public sealed class Budget
{
    public int Id { get; set; }
    public string JourneyLabel { get; set; } = string.Empty;
    public string Category { get; set; } = string.Empty;
    public long LimitAmountMinor { get; set; }
    public string BaseCurrency { get; set; } = string.Empty;
    public DateOnly StartDate { get; set; }
    public DateOnly EndDate { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
    public ICollection<Expense> Expenses { get; set; } = new List<Expense>();
}

public sealed class Expense
{
    public int Id { get; set; }
    public int BudgetId { get; set; }
    public string Description { get; set; } = string.Empty;
    public long OriginalAmountMinor { get; set; }
    public string OriginalCurrency { get; set; } = string.Empty;
    public long ConvertedAmountMinor { get; set; }
    public long ConversionRateScaled { get; set; }
    public DateOnly RateAsOf { get; set; }
    public DateOnly SpentOn { get; set; }
    public string? Notes { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
    public Budget Budget { get; set; } = null!;
}
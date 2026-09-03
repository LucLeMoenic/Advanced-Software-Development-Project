using Microsoft.EntityFrameworkCore;

namespace BudgetTracker.Database.Data;

public sealed class BudgetDbContext(DbContextOptions<BudgetDbContext> options)
    : DbContext(options)
{
    public DbSet<Budget> Budgets { get; set; } = null!;
    public DbSet<Expense> Expenses { get; set; } = null!;

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Budget>(configuration =>
        {
            configuration.ToTable("budgets", table =>
            {
                table.HasCheckConstraint("CK_budgets_journey_label", "length(trim(journey_label)) BETWEEN 1 AND 80");
                table.HasCheckConstraint("CK_budgets_category", "category IN ('accommodation','food','transport','activities','shopping','other')");
                table.HasCheckConstraint("CK_budgets_limit", "limit_amount_minor > 0");
                table.HasCheckConstraint("CK_budgets_currency", "length(base_currency) = 3 AND base_currency = upper(base_currency)");
                table.HasCheckConstraint("CK_budgets_period", "end_date >= start_date");
            });
            configuration.HasKey(value => value.Id);
            configuration.Property(value => value.Id).HasColumnName("id");
            configuration.Property(value => value.JourneyLabel).HasColumnName("journey_label").HasMaxLength(80).UseCollation("NOCASE").IsRequired();
            configuration.Property(value => value.Category).HasColumnName("category").HasMaxLength(20).UseCollation("NOCASE").IsRequired();
            configuration.Property(value => value.LimitAmountMinor).HasColumnName("limit_amount_minor").HasColumnType("INTEGER");
            configuration.Property(value => value.BaseCurrency).HasColumnName("base_currency").HasMaxLength(3).IsRequired();
            configuration.Property(value => value.StartDate).HasColumnName("start_date").HasColumnType("TEXT");
            configuration.Property(value => value.EndDate).HasColumnName("end_date").HasColumnType("TEXT");
            configuration.Property(value => value.CreatedAt).HasColumnName("created_at");
            configuration.Property(value => value.UpdatedAt).HasColumnName("updated_at");
            configuration.HasIndex(value => new { value.JourneyLabel, value.Category, value.StartDate, value.EndDate }).IsUnique();
            configuration.HasIndex(value => value.JourneyLabel);
        });

        modelBuilder.Entity<Expense>(configuration =>
        {
            configuration.ToTable("expenses", table =>
            {
                table.HasCheckConstraint("CK_expenses_description", "length(trim(description)) BETWEEN 1 AND 120");
                table.HasCheckConstraint("CK_expenses_original_amount", "original_amount_minor > 0");
                table.HasCheckConstraint("CK_expenses_converted_amount", "converted_amount_minor > 0");
                table.HasCheckConstraint("CK_expenses_original_currency", "length(original_currency) = 3 AND original_currency = upper(original_currency)");
                table.HasCheckConstraint("CK_expenses_rate", "conversion_rate_scaled > 0");
                table.HasCheckConstraint("CK_expenses_notes", "notes IS NULL OR length(notes) <= 500");
            });
            configuration.HasKey(value => value.Id);
            configuration.Property(value => value.Id).HasColumnName("id");
            configuration.Property(value => value.BudgetId).HasColumnName("budget_id");
            configuration.Property(value => value.Description).HasColumnName("description").HasMaxLength(120).IsRequired();
            configuration.Property(value => value.OriginalAmountMinor).HasColumnName("original_amount_minor").HasColumnType("INTEGER");
            configuration.Property(value => value.OriginalCurrency).HasColumnName("original_currency").HasMaxLength(3).IsRequired();
            configuration.Property(value => value.ConvertedAmountMinor).HasColumnName("converted_amount_minor").HasColumnType("INTEGER");
            configuration.Property(value => value.ConversionRateScaled).HasColumnName("conversion_rate_scaled").HasColumnType("INTEGER");
            configuration.Property(value => value.RateAsOf).HasColumnName("rate_as_of").HasColumnType("TEXT");
            configuration.Property(value => value.SpentOn).HasColumnName("spent_on").HasColumnType("TEXT");
            configuration.Property(value => value.Notes).HasColumnName("notes").HasMaxLength(500);
            configuration.Property(value => value.CreatedAt).HasColumnName("created_at");
            configuration.Property(value => value.UpdatedAt).HasColumnName("updated_at");
            configuration.HasOne(value => value.Budget).WithMany(value => value.Expenses).HasForeignKey(value => value.BudgetId).OnDelete(DeleteBehavior.Cascade);
            configuration.HasIndex(value => new { value.BudgetId, value.SpentOn });
        });
    }
}
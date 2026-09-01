using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace Accommodation.Database.Data.Configurations;

public sealed class SearchConfiguration : BaseEntityTypeConfiguration<Search>
{
    public static class Schema
    {
        public const string TableName = "searches";
    }

    protected override string TableName => Schema.TableName;

    protected override void ConfigureTable(TableBuilder<Search> table)
    {
        table.HasCheckConstraint(
            "CK_searches_dates",
            "check_out > check_in");
        table.HasCheckConstraint(
            "CK_searches_text_lengths",
            "length(trim(title)) BETWEEN 1 AND 80"
            + " AND length(trim(destination)) BETWEEN 2 AND 100"
            + " AND length(preferences) <= 500");
        table.HasCheckConstraint(
            "CK_searches_guests",
            "guests >= 1 AND guests <= 20");
        table.HasCheckConstraint(
            "CK_searches_prices",
            "min_price >= 0 AND max_price <= 10000000 AND min_price <= max_price");
        table.HasCheckConstraint(
            "CK_searches_ranking_mode",
            "ranking_mode IN ('ai', 'fallback', 'programmatic')");
        table.HasCheckConstraint(
            "CK_searches_results_json",
            "json_valid(results_json) AND json_type(results_json) = 'array'");
    }

    protected override void ConfigurePrimaryKey(EntityTypeBuilder<Search> configuration)
    {
        configuration.HasKey(search => search.Id);
    }

    protected override void ConfigureProperties(EntityTypeBuilder<Search> configuration)
    {
        configuration.Property(search => search.Id).HasColumnName("id");
        configuration.Property(search => search.Title)
            .HasColumnName("title")
            .HasMaxLength(80)
            .IsRequired();
        configuration.Property(search => search.Destination)
            .HasColumnName("destination")
            .HasMaxLength(100)
            .UseCollation("NOCASE")
            .IsRequired();
        configuration.Property(search => search.CheckIn).HasColumnName("check_in");
        configuration.Property(search => search.CheckOut).HasColumnName("check_out");
        configuration.Property(search => search.Guests).HasColumnName("guests");
        configuration.Property(search => search.MinimumPrice)
            .HasColumnName("min_price")
            .HasConversion(
                value => decimal.ToInt64(value * 100m),
                value => value / 100m)
            .HasColumnType("INTEGER");
        configuration.Property(search => search.MaximumPrice)
            .HasColumnName("max_price")
            .HasConversion(
                value => decimal.ToInt64(value * 100m),
                value => value / 100m)
            .HasColumnType("INTEGER");
        configuration.Property(search => search.Preferences)
            .HasColumnName("preferences")
            .HasMaxLength(500)
            .IsRequired();
        configuration.Property(search => search.RankingMode)
            .HasColumnName("ranking_mode")
            .HasMaxLength(12)
            .IsRequired();
        configuration.Property(search => search.ResultsJson)
            .HasColumnName("results_json")
            .HasColumnType("TEXT")
            .IsRequired();
        configuration.Property(search => search.CreatedAt).HasColumnName("created_at");
        configuration.Property(search => search.UpdatedAt).HasColumnName("updated_at");
    }

    protected override void ConfigureIndexes(EntityTypeBuilder<Search> configuration)
    {
        configuration.HasIndex(search => search.CreatedAt);
    }
}

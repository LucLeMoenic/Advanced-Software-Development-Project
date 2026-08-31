using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace Accommodation.Database.Data.Configurations;

public sealed class SearchConfiguration : IEntityTypeConfiguration<Search>
{
    public void Configure(EntityTypeBuilder<Search> builder)
    {
        builder.ToTable(
            "searches",
            table =>
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
                    "ranking_mode IN ('ai', 'fallback')");
                table.HasCheckConstraint(
                    "CK_searches_results_json",
                    "json_valid(results_json) AND json_type(results_json) = 'array'");
            });

        builder.HasKey(search => search.Id);
        builder.Property(search => search.Id).HasColumnName("id");
        builder.Property(search => search.Title)
            .HasColumnName("title")
            .HasMaxLength(80)
            .IsRequired();
        builder.Property(search => search.Destination)
            .HasColumnName("destination")
            .HasMaxLength(100)
            .UseCollation("NOCASE")
            .IsRequired();
        builder.Property(search => search.CheckIn).HasColumnName("check_in");
        builder.Property(search => search.CheckOut).HasColumnName("check_out");
        builder.Property(search => search.Guests).HasColumnName("guests");
        builder.Property(search => search.MinimumPrice)
            .HasColumnName("min_price")
            .HasConversion(
                value => decimal.ToInt64(value * 100m),
                value => value / 100m)
            .HasColumnType("INTEGER");
        builder.Property(search => search.MaximumPrice)
            .HasColumnName("max_price")
            .HasConversion(
                value => decimal.ToInt64(value * 100m),
                value => value / 100m)
            .HasColumnType("INTEGER");
        builder.Property(search => search.Preferences)
            .HasColumnName("preferences")
            .HasMaxLength(500)
            .IsRequired();
        builder.Property(search => search.RankingMode)
            .HasColumnName("ranking_mode")
            .HasMaxLength(8)
            .IsRequired();
        builder.Property(search => search.ResultsJson)
            .HasColumnName("results_json")
            .HasColumnType("TEXT")
            .IsRequired();
        builder.Property(search => search.CreatedAt).HasColumnName("created_at");
        builder.Property(search => search.UpdatedAt).HasColumnName("updated_at");

        builder.HasIndex(search => search.CreatedAt);
    }
}

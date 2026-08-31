using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace Accommodation.Database.Data.Configurations;

public sealed class AccommodationConfiguration
    : BaseEntityTypeConfiguration<Accommodation>
{
    public static class Schema
    {
        public const string TableName = "accommodations";
    }

    protected override string TableName => Schema.TableName;

    protected override void ConfigureTable(TableBuilder<Accommodation> table)
    {
        table.HasCheckConstraint(
            "CK_accommodations_nightly_price",
            "nightly_price >= 0 AND nightly_price <= 10000000");
        table.HasCheckConstraint(
            "CK_accommodations_max_guests",
            "max_guests >= 1 AND max_guests <= 20");
        table.HasCheckConstraint(
            "CK_accommodations_amenities_json",
            "json_valid(amenities) AND json_type(amenities) = 'array'");
    }

    protected override void ConfigurePrimaryKey(
        EntityTypeBuilder<Accommodation> configuration)
    {
        configuration.HasKey(accommodation => accommodation.Id);
    }

    protected override void ConfigureProperties(
        EntityTypeBuilder<Accommodation> configuration)
    {
        configuration.Property(accommodation => accommodation.Id)
            .HasColumnName("id");
        configuration.Property(accommodation => accommodation.Name)
            .HasColumnName("name")
            .HasMaxLength(120)
            .UseCollation("NOCASE")
            .IsRequired();
        configuration.Property(accommodation => accommodation.Destination)
            .HasColumnName("destination")
            .HasMaxLength(100)
            .UseCollation("NOCASE")
            .IsRequired();
        configuration.Property(accommodation => accommodation.Description)
            .HasColumnName("description")
            .HasMaxLength(1000)
            .IsRequired();
        configuration.Property(accommodation => accommodation.NightlyPrice)
            .HasColumnName("nightly_price")
            .HasConversion(
                value => decimal.ToInt64(value * 100m),
                value => value / 100m)
            .HasColumnType("INTEGER");
        configuration.Property(accommodation => accommodation.MaxGuests)
            .HasColumnName("max_guests");
        configuration.Property(accommodation => accommodation.AmenitiesJson)
            .HasColumnName("amenities")
            .HasColumnType("TEXT")
            .IsRequired();
        configuration.Property(accommodation => accommodation.ImageUrl)
            .HasColumnName("image_url")
            .HasMaxLength(2048);
        configuration.Property(accommodation => accommodation.BookingUrl)
            .HasColumnName("booking_url")
            .HasMaxLength(2048);
        configuration.Property(accommodation => accommodation.IsActive)
            .HasColumnName("is_active")
            .HasDefaultValue(true);
        configuration.Property(accommodation => accommodation.CreatedAt)
            .HasColumnName("created_at");
        configuration.Property(accommodation => accommodation.UpdatedAt)
            .HasColumnName("updated_at");
    }

    protected override void ConfigureIndexes(
        EntityTypeBuilder<Accommodation> configuration)
    {
        configuration.HasIndex(accommodation => new
            {
                accommodation.Name,
                accommodation.Destination
            })
            .IsUnique();
        configuration.HasIndex(accommodation => new
        {
            accommodation.Destination,
            accommodation.IsActive
        });
    }
}

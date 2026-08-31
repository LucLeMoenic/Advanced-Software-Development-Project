using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace Accommodation.Database.Data.Configurations;

public sealed class AccommodationConfiguration : IEntityTypeConfiguration<Accommodation>
{
    public void Configure(EntityTypeBuilder<Accommodation> builder)
    {
        builder.ToTable(
            "accommodations",
            table =>
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
            });

        builder.HasKey(item => item.Id);
        builder.Property(item => item.Id).HasColumnName("id");
        builder.Property(item => item.Name)
            .HasColumnName("name")
            .HasMaxLength(120)
            .UseCollation("NOCASE")
            .IsRequired();
        builder.Property(item => item.Destination)
            .HasColumnName("destination")
            .HasMaxLength(100)
            .UseCollation("NOCASE")
            .IsRequired();
        builder.Property(item => item.Description)
            .HasColumnName("description")
            .HasMaxLength(1000)
            .IsRequired();
        builder.Property(item => item.NightlyPrice)
            .HasColumnName("nightly_price")
            .HasConversion(
                value => decimal.ToInt64(value * 100m),
                value => value / 100m)
            .HasColumnType("INTEGER");
        builder.Property(item => item.MaxGuests).HasColumnName("max_guests");
        builder.Property(item => item.AmenitiesJson)
            .HasColumnName("amenities")
            .HasColumnType("TEXT")
            .IsRequired();
        builder.Property(item => item.ImageUrl)
            .HasColumnName("image_url")
            .HasMaxLength(2048);
        builder.Property(item => item.BookingUrl)
            .HasColumnName("booking_url")
            .HasMaxLength(2048);
        builder.Property(item => item.IsActive)
            .HasColumnName("is_active")
            .HasDefaultValue(true);
        builder.Property(item => item.CreatedAt).HasColumnName("created_at");
        builder.Property(item => item.UpdatedAt).HasColumnName("updated_at");

        builder.HasIndex(item => new { item.Name, item.Destination })
            .IsUnique();
        builder.HasIndex(item => new { item.Destination, item.IsActive });
    }
}

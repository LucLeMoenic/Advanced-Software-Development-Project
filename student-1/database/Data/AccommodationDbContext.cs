using Microsoft.EntityFrameworkCore;
using Accommodation.Database.Data.Configurations;

namespace Accommodation.Database.Data;

public sealed class AccommodationDbContext(DbContextOptions<AccommodationDbContext> options)
    : DbContext(options)
{
    public DbSet<Accommodation> Accommodations => Set<Accommodation>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.ApplyConfiguration(new AccommodationConfiguration());
        base.OnModelCreating(modelBuilder);
    }
}

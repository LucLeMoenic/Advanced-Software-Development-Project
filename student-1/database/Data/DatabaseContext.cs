using Microsoft.EntityFrameworkCore;
using Accommodation.Database.Data.Configurations;

namespace Accommodation.Database.Data;

public sealed class DatabaseContext(DbContextOptions<DatabaseContext> options)
    : DbContext(options)
{
    public DbSet<Accommodation> Accommodations => Set<Accommodation>();
    public DbSet<Search> Searches => Set<Search>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.ApplyConfiguration(new AccommodationConfiguration());
        modelBuilder.ApplyConfiguration(new SearchConfiguration());
        base.OnModelCreating(modelBuilder);
    }
}

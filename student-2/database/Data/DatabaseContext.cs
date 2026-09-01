using Microsoft.EntityFrameworkCore;
using Accommodation.Database.Data.Configurations;

namespace Accommodation.Database.Data;

public class DatabaseContext : DbContext
{
    public DatabaseContext(DbContextOptions<DatabaseContext> options)
        : base(options)
    {
    }

    public DbSet<Accommodation> Accommodations { get; set; } = null!;

    public DbSet<Search> Searches { get; set; } = null!;

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.ApplyConfiguration(new AccommodationConfiguration());
        modelBuilder.ApplyConfiguration(new SearchConfiguration());
        base.OnModelCreating(modelBuilder);
    }
}

using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace Accommodation.Database.Data.Configurations;

public abstract class BaseEntityTypeConfiguration<TEntity>
    : IEntityTypeConfiguration<TEntity>
    where TEntity : class
{
    protected abstract string TableName { get; }

    public void Configure(EntityTypeBuilder<TEntity> configuration)
    {
        configuration.ToTable(TableName, ConfigureTable);
        ConfigurePrimaryKey(configuration);
        ConfigureProperties(configuration);
        ConfigureIndexes(configuration);
        ConfigureForeignKeys(configuration);
    }

    protected virtual void ConfigureTable(TableBuilder<TEntity> table)
    {
    }

    protected abstract void ConfigurePrimaryKey(EntityTypeBuilder<TEntity> configuration);

    protected abstract void ConfigureProperties(EntityTypeBuilder<TEntity> configuration);

    protected virtual void ConfigureIndexes(EntityTypeBuilder<TEntity> configuration)
    {
    }

    protected virtual void ConfigureForeignKeys(EntityTypeBuilder<TEntity> configuration)
    {
    }
}

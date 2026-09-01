using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Accommodation.Database.Data;
using AccommodationEntity = Accommodation.Database.Data.Accommodation;

namespace Accommodation.Database.Repositories;

public sealed class AccommodationRepository(DatabaseContext database)
    : IAccommodationRepository
{
    public async Task<IReadOnlyList<AccommodationEntity>> ListAsync(
        string? destination,
        decimal? minimumPrice,
        decimal? maximumPrice,
        int? guests,
        bool? isActive,
        CancellationToken cancellationToken)
    {
        var query = database.Accommodations.AsNoTracking();

        if (destination is not null)
        {
            query = query.Where(item =>
                EF.Functions.Collate(item.Destination, "NOCASE") == destination);
        }

        if (minimumPrice is not null)
        {
            query = query.Where(item => item.NightlyPrice >= minimumPrice);
        }

        if (maximumPrice is not null)
        {
            query = query.Where(item => item.NightlyPrice <= maximumPrice);
        }

        if (guests is not null)
        {
            query = query.Where(item => item.MaxGuests >= guests);
        }

        if (isActive is not null)
        {
            query = query.Where(item => item.IsActive == isActive);
        }

        return await query
            .OrderBy(item => item.Id)
            .ToListAsync(cancellationToken);
    }

    public Task<AccommodationEntity?> GetAsync(
        int id,
        bool trackChanges,
        CancellationToken cancellationToken)
    {
        var query = trackChanges
            ? database.Accommodations
            : database.Accommodations.AsNoTracking();

        return query.SingleOrDefaultAsync(
            item => item.Id == id,
            cancellationToken);
    }

    public Task<bool> DuplicateExistsAsync(
        string name,
        string destination,
        int? excludedId,
        CancellationToken cancellationToken)
    {
        return database.Accommodations.AnyAsync(
            item =>
                (!excludedId.HasValue || item.Id != excludedId.Value)
                && EF.Functions.Collate(item.Name, "NOCASE") == name
                && EF.Functions.Collate(item.Destination, "NOCASE") == destination,
            cancellationToken);
    }

    public void Add(AccommodationEntity accommodation)
    {
        database.Accommodations.Add(accommodation);
    }

    public void Remove(AccommodationEntity accommodation)
    {
        database.Accommodations.Remove(accommodation);
    }

    public async Task SaveChangesAsync(CancellationToken cancellationToken)
    {
        try
        {
            await database.SaveChangesAsync(cancellationToken);
        }
        catch (DbUpdateException exception)
            when (exception.InnerException is SqliteException
            {
                SqliteExtendedErrorCode: 2067
            })
        {
            throw new AccommodationConflictException(exception);
        }
    }
}

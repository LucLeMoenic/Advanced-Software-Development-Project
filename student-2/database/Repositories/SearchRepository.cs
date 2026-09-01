using Microsoft.EntityFrameworkCore;
using Accommodation.Database.Data;
using SearchEntity = Accommodation.Database.Data.Search;

namespace Accommodation.Database.Repositories;

public sealed class SearchRepository(DatabaseContext database) : ISearchRepository
{
    public async Task<IReadOnlyList<SearchEntity>> ListAsync(
        CancellationToken cancellationToken)
    {
        return await database.Searches
            .AsNoTracking()
            .OrderByDescending(search => search.CreatedAt)
            .ThenByDescending(search => search.Id)
            .ToListAsync(cancellationToken);
    }

    public Task<SearchEntity?> GetAsync(
        int id,
        bool trackChanges,
        CancellationToken cancellationToken)
    {
        var query = trackChanges
            ? database.Searches
            : database.Searches.AsNoTracking();

        return query.SingleOrDefaultAsync(
            search => search.Id == id,
            cancellationToken);
    }

    public void Add(SearchEntity search)
    {
        database.Searches.Add(search);
    }

    public void Remove(SearchEntity search)
    {
        database.Searches.Remove(search);
    }

    public Task SaveChangesAsync(CancellationToken cancellationToken)
    {
        return database.SaveChangesAsync(cancellationToken);
    }
}

using Accommodation.Database.Data;
using SearchEntity = Accommodation.Database.Data.Search;

namespace Accommodation.Database.Repositories;

public interface ISearchRepository
{
    Task<IReadOnlyList<SearchEntity>> ListAsync(CancellationToken cancellationToken);

    Task<SearchEntity?> GetAsync(
        int id,
        bool trackChanges,
        CancellationToken cancellationToken);

    void Add(SearchEntity search);

    void Remove(SearchEntity search);

    Task SaveChangesAsync(CancellationToken cancellationToken);
}

using AccommodationEntity = Accommodation.Database.Data.Accommodation;

namespace Accommodation.Database.Repositories;

public interface IAccommodationRepository
{
    Task<IReadOnlyList<AccommodationEntity>> ListAsync(
        string? destination,
        decimal? minimumPrice,
        decimal? maximumPrice,
        int? guests,
        bool? isActive,
        CancellationToken cancellationToken);

    Task<AccommodationEntity?> GetAsync(
        int id,
        bool trackChanges,
        CancellationToken cancellationToken);

    Task<bool> DuplicateExistsAsync(
        string name,
        string destination,
        int? excludedId,
        CancellationToken cancellationToken);

    void Add(AccommodationEntity accommodation);

    void Remove(AccommodationEntity accommodation);

    Task SaveChangesAsync(CancellationToken cancellationToken);
}

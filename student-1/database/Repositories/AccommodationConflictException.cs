namespace Accommodation.Database.Repositories;

public sealed class AccommodationConflictException(Exception innerException)
    : Exception("An accommodation with this name and destination already exists.", innerException);

namespace Accommodation.Database.Data;

public sealed class Accommodation
{
    public int Id { get; set; }
    public required string Name { get; set; }
    public required string Destination { get; set; }
    public required string Description { get; set; }
    public decimal NightlyPrice { get; set; }
    public int MaxGuests { get; set; }
    public required string AmenitiesJson { get; set; }
    public string? ImageUrl { get; set; }
    public string? BookingUrl { get; set; }
    public bool IsActive { get; set; } = true;
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
}

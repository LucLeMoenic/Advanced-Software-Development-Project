namespace Accommodation.Database.Data;

public sealed class Search
{
    public int Id { get; set; }
    public required string Title { get; set; }
    public required string Destination { get; set; }
    public DateOnly CheckIn { get; set; }
    public DateOnly CheckOut { get; set; }
    public int Guests { get; set; }
    public decimal MinimumPrice { get; set; }
    public decimal MaximumPrice { get; set; }
    public required string Preferences { get; set; }
    public required string RankingMode { get; set; }
    public required string ResultsJson { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
}

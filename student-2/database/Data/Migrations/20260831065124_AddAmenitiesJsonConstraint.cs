using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Accommodation.Database.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddAmenitiesJsonConstraint : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddCheckConstraint(
                name: "CK_accommodations_amenities_json",
                table: "accommodations",
                sql: "json_valid(amenities) AND json_type(amenities) = 'array'");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "CK_accommodations_amenities_json",
                table: "accommodations");
        }
    }
}

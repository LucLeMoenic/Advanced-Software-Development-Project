using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Accommodation.Database.Data.Migrations
{
    /// <inheritdoc />
    public partial class InitialAccommodationCatalogue : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "accommodations",
                columns: table => new
                {
                    id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    name = table.Column<string>(type: "TEXT", maxLength: 120, nullable: false, collation: "NOCASE"),
                    destination = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false, collation: "NOCASE"),
                    description = table.Column<string>(type: "TEXT", maxLength: 1000, nullable: false),
                    nightly_price = table.Column<long>(type: "INTEGER", nullable: false),
                    max_guests = table.Column<int>(type: "INTEGER", nullable: false),
                    amenities = table.Column<string>(type: "TEXT", nullable: false),
                    image_url = table.Column<string>(type: "TEXT", maxLength: 2048, nullable: true),
                    booking_url = table.Column<string>(type: "TEXT", maxLength: 2048, nullable: true),
                    is_active = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: true),
                    created_at = table.Column<DateTime>(type: "TEXT", nullable: false),
                    updated_at = table.Column<DateTime>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_accommodations", x => x.id);
                    table.CheckConstraint("CK_accommodations_max_guests", "max_guests >= 1 AND max_guests <= 20");
                    table.CheckConstraint("CK_accommodations_nightly_price", "nightly_price >= 0 AND nightly_price <= 10000000");
                });

            migrationBuilder.CreateIndex(
                name: "IX_accommodations_destination_is_active",
                table: "accommodations",
                columns: new[] { "destination", "is_active" });

            migrationBuilder.CreateIndex(
                name: "IX_accommodations_name_destination",
                table: "accommodations",
                columns: new[] { "name", "destination" },
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "accommodations");
        }
    }
}

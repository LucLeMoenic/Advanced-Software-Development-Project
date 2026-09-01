using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Accommodation.Database.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddSearchHistory : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "searches",
                columns: table => new
                {
                    id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    title = table.Column<string>(type: "TEXT", maxLength: 80, nullable: false),
                    destination = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false, collation: "NOCASE"),
                    check_in = table.Column<DateOnly>(type: "TEXT", nullable: false),
                    check_out = table.Column<DateOnly>(type: "TEXT", nullable: false),
                    guests = table.Column<int>(type: "INTEGER", nullable: false),
                    min_price = table.Column<long>(type: "INTEGER", nullable: false),
                    max_price = table.Column<long>(type: "INTEGER", nullable: false),
                    preferences = table.Column<string>(type: "TEXT", maxLength: 500, nullable: false),
                    ranking_mode = table.Column<string>(type: "TEXT", maxLength: 8, nullable: false),
                    results_json = table.Column<string>(type: "TEXT", nullable: false),
                    created_at = table.Column<DateTime>(type: "TEXT", nullable: false),
                    updated_at = table.Column<DateTime>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_searches", x => x.id);
                    table.CheckConstraint("CK_searches_dates", "check_out > check_in");
                    table.CheckConstraint("CK_searches_guests", "guests >= 1 AND guests <= 20");
                    table.CheckConstraint("CK_searches_prices", "min_price >= 0 AND max_price <= 10000000 AND min_price <= max_price");
                    table.CheckConstraint("CK_searches_ranking_mode", "ranking_mode IN ('ai', 'fallback')");
                    table.CheckConstraint("CK_searches_results_json", "json_valid(results_json) AND json_type(results_json) = 'array'");
                    table.CheckConstraint("CK_searches_text_lengths", "length(trim(title)) BETWEEN 1 AND 80 AND length(trim(destination)) BETWEEN 2 AND 100 AND length(preferences) <= 500");
                });

            migrationBuilder.CreateIndex(
                name: "IX_searches_created_at",
                table: "searches",
                column: "created_at");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "searches");
        }
    }
}

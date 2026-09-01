using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Accommodation.Database.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddProgrammaticRankingMode : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "CK_searches_ranking_mode",
                table: "searches");

            migrationBuilder.AddCheckConstraint(
                name: "CK_searches_ranking_mode",
                table: "searches",
                sql: "ranking_mode IN ('ai', 'fallback', 'programmatic')");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "CK_searches_ranking_mode",
                table: "searches");

            migrationBuilder.AddCheckConstraint(
                name: "CK_searches_ranking_mode",
                table: "searches",
                sql: "ranking_mode IN ('ai', 'fallback')");
        }
    }
}

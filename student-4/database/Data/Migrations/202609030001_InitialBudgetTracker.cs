using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

namespace BudgetTracker.Database.Data.Migrations;

[DbContext(typeof(BudgetDbContext))]
[Migration("202609030001_InitialBudgetTracker")]
public sealed class InitialBudgetTracker : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.Sql(
            """
            CREATE TABLE budgets (
                id INTEGER NOT NULL CONSTRAINT PK_budgets PRIMARY KEY AUTOINCREMENT,
                journey_label TEXT COLLATE NOCASE NOT NULL,
                category TEXT COLLATE NOCASE NOT NULL,
                limit_amount_minor INTEGER NOT NULL,
                base_currency TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                CONSTRAINT CK_budgets_journey_label CHECK (length(trim(journey_label)) BETWEEN 1 AND 80),
                CONSTRAINT CK_budgets_category CHECK (category IN ('accommodation','food','transport','activities','shopping','other')),
                CONSTRAINT CK_budgets_limit CHECK (limit_amount_minor > 0),
                CONSTRAINT CK_budgets_currency CHECK (length(base_currency) = 3 AND base_currency = upper(base_currency)),
                CONSTRAINT CK_budgets_period CHECK (end_date >= start_date)
            );
            CREATE UNIQUE INDEX IX_budgets_journey_label_category_start_date_end_date
                ON budgets (journey_label, category, start_date, end_date);
            CREATE INDEX IX_budgets_journey_label ON budgets (journey_label);
            CREATE TRIGGER TR_budgets_currency_insert
            BEFORE INSERT ON budgets
            WHEN EXISTS (
                SELECT 1 FROM budgets
                WHERE journey_label = NEW.journey_label
                  AND base_currency <> NEW.base_currency
            )
            BEGIN
                SELECT RAISE(ABORT, 'journey_currency_conflict');
            END;
            CREATE TRIGGER TR_budgets_currency_update
            BEFORE UPDATE OF journey_label, base_currency ON budgets
            WHEN EXISTS (
                SELECT 1 FROM budgets
                WHERE journey_label = NEW.journey_label
                  AND base_currency <> NEW.base_currency
                  AND id <> NEW.id
            )
            BEGIN
                SELECT RAISE(ABORT, 'journey_currency_conflict');
            END;

            CREATE TABLE expenses (
                id INTEGER NOT NULL CONSTRAINT PK_expenses PRIMARY KEY AUTOINCREMENT,
                budget_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                original_amount_minor INTEGER NOT NULL,
                original_currency TEXT NOT NULL,
                converted_amount_minor INTEGER NOT NULL,
                conversion_rate_scaled INTEGER NOT NULL,
                rate_as_of TEXT NOT NULL,
                spent_on TEXT NOT NULL,
                notes TEXT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                CONSTRAINT FK_expenses_budgets_budget_id FOREIGN KEY (budget_id) REFERENCES budgets (id) ON DELETE CASCADE,
                CONSTRAINT CK_expenses_description CHECK (length(trim(description)) BETWEEN 1 AND 120),
                CONSTRAINT CK_expenses_original_amount CHECK (original_amount_minor > 0),
                CONSTRAINT CK_expenses_converted_amount CHECK (converted_amount_minor > 0),
                CONSTRAINT CK_expenses_original_currency CHECK (length(original_currency) = 3 AND original_currency = upper(original_currency)),
                CONSTRAINT CK_expenses_rate CHECK (conversion_rate_scaled > 0),
                CONSTRAINT CK_expenses_notes CHECK (notes IS NULL OR length(notes) <= 500)
            );
            CREATE INDEX IX_expenses_budget_id_spent_on ON expenses (budget_id, spent_on);
            """);
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.Sql("DROP TABLE expenses; DROP TABLE budgets;");
    }
}
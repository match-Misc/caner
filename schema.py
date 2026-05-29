import logging

from sqlalchemy import inspect, text


logger = logging.getLogger(__name__)


def ensure_application_schema(db):
    """Apply additive schema updates that db.create_all() will not perform."""
    inspector = inspect(db.engine)
    dialect = db.engine.dialect.name

    meal_columns = {column["name"] for column in inspector.get_columns("meals")}
    if "description_en" not in meal_columns:
        if dialect == "postgresql":
            statement = "ALTER TABLE meals ADD COLUMN IF NOT EXISTS description_en TEXT"
        else:
            statement = "ALTER TABLE meals ADD COLUMN description_en TEXT"

        logger.info("Adding missing meals.description_en column.")
        db.session.execute(text(statement))
        db.session.commit()

    if not inspector.has_table("meal_comments"):
        return

    comment_columns = {
        column["name"] for column in inspector.get_columns("meal_comments")
    }
    column_definitions = {
        "source_language": "VARCHAR(5) NOT NULL DEFAULT 'de'",
        "translation_failed": "BOOLEAN NOT NULL DEFAULT FALSE",
    }
    for column_name, column_definition in column_definitions.items():
        if column_name in comment_columns:
            continue
        if dialect == "postgresql":
            statement = (
                f"ALTER TABLE meal_comments ADD COLUMN IF NOT EXISTS {column_name} "
                f"{column_definition}"
            )
        else:
            statement = (
                f"ALTER TABLE meal_comments ADD COLUMN {column_name} "
                f"{column_definition}"
            )
        logger.info("Adding missing meal_comments.%s column.", column_name)
        db.session.execute(text(statement))
        db.session.commit()

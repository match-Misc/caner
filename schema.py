import logging

from sqlalchemy import inspect, text


logger = logging.getLogger(__name__)


def ensure_application_schema(db):
    """Apply additive schema updates that db.create_all() will not perform."""
    inspector = inspect(db.engine)
    meal_columns = {column["name"] for column in inspector.get_columns("meals")}
    if "description_en" in meal_columns:
        return

    dialect = db.engine.dialect.name
    if dialect == "postgresql":
        statement = "ALTER TABLE meals ADD COLUMN IF NOT EXISTS description_en TEXT"
    else:
        statement = "ALTER TABLE meals ADD COLUMN description_en TEXT"

    logger.info("Adding missing meals.description_en column.")
    db.session.execute(text(statement))
    db.session.commit()

"""ORM models.

Import new models here so Alembic autogenerate and ``Base.metadata`` see them.
"""

from app.models.subscription import Subscription
from app.models.super_admin import SuperAdmin

__all__ = ["SuperAdmin", "Subscription"]

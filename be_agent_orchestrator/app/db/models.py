"""Aggregator that imports every module's models so ``Base.metadata`` is
fully populated. Use this whenever you need the full schema in one place
(tests, scripted DDL, ad-hoc inspections). Alembic's ``env.py`` does its
own imports, so it does not depend on this module."""

from app.modules.agents import models as _agents  # noqa: F401
from app.modules.audit import models as _audit  # noqa: F401
from app.modules.channels import models as _channels  # noqa: F401
from app.modules.llm import models as _llm  # noqa: F401
from app.modules.memory import models as _memory  # noqa: F401
from app.modules.messages import models as _messages  # noqa: F401
from app.modules.runs import models as _runs  # noqa: F401
from app.modules.schedules import models as _schedules  # noqa: F401
from app.modules.tools import models as _tools  # noqa: F401
from app.modules.users import models as _users  # noqa: F401
from app.modules.webhooks import models as _webhooks  # noqa: F401
from app.modules.workflows import models as _workflows  # noqa: F401

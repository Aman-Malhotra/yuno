from collections.abc import Callable
from typing import Any

from arq.connections import RedisSettings

from app.core.config import settings
from app.core.lifespan import worker_shutdown, worker_startup
from app.worker import jobs


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    functions: list[Callable[..., Any]] = [
        jobs.execute_workflow_run_job,
        # jobs.process_channel_message_job,
        # jobs.send_channel_message_job,
    ]

    on_startup = worker_startup
    on_shutdown = worker_shutdown

    max_jobs: int = 10
    job_timeout: int = 300
    keep_result: int = 3600
    health_check_interval: int = 30


_ = jobs  # keep import alive even with no registered jobs yet

"""CrewAI implementation of ArticleGeneratorPort."""

import logging

from adapter.crew.main import run as run_crew
from adapter.crew.models import ReviewedArticle
from adapter.crew.progress_listener import JobProgressListener
from domain.model.article import ArticleInputs, GenerationResult, SourceInfo
from port.job_queue import JobQueuePort

logger = logging.getLogger(__name__)


class CrewAIArticleGenerator:
    """Generates articles using CrewAI pipeline.

    Tracks job progress via JobProgressListener.
    """

    def __init__(self, job_queue: JobQueuePort):
        self.job_queue = job_queue

    def generate(
        self,
        inputs: ArticleInputs,
        vocabulary: list[str],
        job_id: str = "",
        article_id: str = "",
    ) -> GenerationResult:
        """Run CrewAI pipeline and return framework-agnostic result."""
        from crewai.events.event_bus import crewai_event_bus

        crew_inputs = {
            'language': inputs.language,
            'level': inputs.level,
            'length': inputs.length,
            'topic': inputs.topic,
            'vocabulary_list': vocabulary if vocabulary else "",
        }

        with crewai_event_bus.scoped_handlers():
            listener = JobProgressListener(
                job_id=job_id,
                article_id=article_id,
                job_queue=self.job_queue,
            )

            result = run_crew(inputs=crew_inputs)

            if listener.task_failed:
                raise RuntimeError("CrewAI task failed during execution")

        # Convert CrewAI result to domain GenerationResult
        reviewed = result.pydantic
        content = reviewed.article_content if isinstance(reviewed, ReviewedArticle) else result.raw

        edit_history = []
        if isinstance(reviewed, ReviewedArticle):
            edit_history = [s.to_edit_record() for s in reviewed.replaced_sentences]

        agent_usage = result.get_agent_usage()

        return GenerationResult(
            content=content,
            source=SourceInfo(title="", source_name=""),
            edit_history=edit_history,
            agent_usage=agent_usage,
        )

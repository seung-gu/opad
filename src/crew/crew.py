from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool
from crewai.memory import ShortTermMemory, LongTermMemory, EntityMemory
from crewai.memory.storage.rag_storage import RAGStorage
from crewai.memory.storage.ltm_sqlite_storage import LTMSQLiteStorage

from crew.models import NewsArticleList, SelectedArticle, ReviewedArticle
from crew.guardrails import repair_json_output


@CrewBase
class ReadingMaterialCreator():
    " Reading Material Creator Crew - Creates educational reading materials from news articles "

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def get_role_to_key_map(self) -> dict[str, str]:
        """Get mapping of agent role -> agent key for display names.

        Returns:
            Dict mapping role string to key (e.g., "News article finder..." -> "article_finder")
        """
        return {
            config['role'].strip(): key
            for key, config in self.agents_config.items()
            if 'role' in config
        }

    @agent
    def article_finder(self) -> Agent:
        return Agent(
            config=self.agents_config['article_finder'],
            tools=[SerperDevTool()],
            memory=True
        )

    @agent
    def article_picker(self) -> Agent:
        return Agent(config=self.agents_config['article_picker'])

    @agent
    def article_rewriter(self) -> Agent:
        return Agent(config=self.agents_config['article_rewriter'])

    @agent
    def article_reviewer(self) -> Agent:
        return Agent(config=self.agents_config['article_reviewer'])

    @task
    def find_news_articles(self) -> Task:
        return Task(
            config=self.tasks_config['find_news_articles'],
            output_pydantic=NewsArticleList,
            guardrail=repair_json_output
        )

    @task
    def pick_best_article(self) -> Task:
        return Task(
            config=self.tasks_config['pick_best_article'],
            output_pydantic=SelectedArticle,
            guardrail=repair_json_output
        )

    @task
    def adapt_news_article(self) -> Task:
        return Task(
            config=self.tasks_config['adapt_news_article']
        )

    @task
    def review_article_quality(self) -> Task:
        return Task(
            config=self.tasks_config['review_article_quality'],
            output_pydantic=ReviewedArticle,
            guardrail=repair_json_output
        )

    @crew
    def crew(self) -> Crew:
        """ Creates the Reading Material Creator Crew """
        
        short_term_memory = ShortTermMemory(
            storage=RAGStorage(
                embedder_config={
                    "provider": "openai",
                    "config": {
                        "model": "text-embedding-3-small"
                    }
                },
                type="short_term",
                path="./memory/"
            )
        )
        
        long_term_memory = LongTermMemory(
            storage=LTMSQLiteStorage(
                db_path="./memory/long_term_memory_storage.db"
            )
        )
        
        entity_memory = EntityMemory(
            storage=RAGStorage(
                embedder_config={
                    "provider": "openai",
                    "config": {
                        "model": "text-embedding-3-small"
                    }
                },
                type="entity",
                path="./memory/"
            )
        )
        
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,  # sequential process: find articles -> pick best -> adapt for learners
            verbose=True,
            memory=True,
            short_term_memory=short_term_memory,
            long_term_memory=long_term_memory,
            entity_memory=entity_memory
        )
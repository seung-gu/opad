from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool
from crewai.memory import ShortTermMemory, LongTermMemory, EntityMemory
from crewai.memory.storage.rag_storage import RAGStorage
from crewai.memory.storage.ltm_sqlite_storage import LTMSQLiteStorage
from pydantic import BaseModel, Field
from typing import List, Optional


class NewsArticle(BaseModel):
    """A news article with source information"""
    title: str = Field(description="Article title")
    source_name: str = Field(description="Publication or news outlet name")
    source_url: Optional[str] = Field(description="Source URL if available", default=None)
    publication_date: Optional[str] = Field(description="Publication date", default=None)
    author: Optional[str] = Field(description="Author name if available", default=None)
    content: str = Field(description="Full article content/text")


class NewsArticleList(BaseModel):
    """A list of news articles"""
    articles: List[NewsArticle] = Field(description="List of 2-3 news articles")


class SelectedArticle(BaseModel):
    """A selected news article with selection rationale"""
    article: NewsArticle = Field(description="The selected news article")
    selection_rationale: str = Field(description="Explanation of why this article was selected over the alternatives")


class AdaptedReadingMaterial(BaseModel):
    """Adapted reading material for language learners"""
    title: str = Field(description="Title of the adapted reading material")
    content: str = Field(description="Adapted content text")
    original_source_name: str = Field(description="Original source name")
    original_source_url: Optional[str] = Field(description="Original source URL if available", default=None)
    original_publication_date: Optional[str] = Field(description="Original publication date", default=None)
    difficulty_level: str = Field(description="Target difficulty level")
    language: str = Field(description="Language of the content")
    word_count: Optional[int] = Field(description="Approximate word count", default=None)


@CrewBase
class ReadingMaterialCreator():
    " Reading Material Creator Crew - Creates educational reading materials from news articles "

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def paragraph_finder(self) -> Agent:
        return Agent(
            config=self.agents_config['paragraph_finder'], 
            tools=[SerperDevTool()]
        )

    @agent
    def article_picker(self) -> Agent:
        return Agent(
            config=self.agents_config['article_picker'],
            memory=True
        )

    @agent
    def paragraph_writer(self) -> Agent:
        return Agent(
            config=self.agents_config['paragraph_writer']
        )

    @task
    def find_news_articles(self) -> Task:
        return Task(
            config=self.tasks_config['find_news_articles'],
            output_pydantic=NewsArticleList
        )

    @task
    def pick_best_article(self) -> Task:
        return Task(
            config=self.tasks_config['pick_best_article'],
            output_pydantic=SelectedArticle
        )

    @task
    def adapt_news_article(self) -> Task:
        return Task(
            config=self.tasks_config['adapt_news_article']
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
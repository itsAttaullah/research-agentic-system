"""Search tool plugins."""

from sra.tools.search.academic_search import AcademicPaperSearchTool
from sra.tools.search.github_search import GitHubSearchTool
from sra.tools.search.google_search import GoogleSearchTool
from sra.tools.search.news_search import NewsSearchTool
from sra.tools.search.reddit_search import RedditSearchTool
from sra.tools.search.youtube_search import YouTubeSearchTool

__all__ = [
    "AcademicPaperSearchTool",
    "GitHubSearchTool",
    "GoogleSearchTool",
    "NewsSearchTool",
    "RedditSearchTool",
    "YouTubeSearchTool",
]

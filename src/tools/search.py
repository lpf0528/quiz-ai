import logging
import os
from typing import Optional, List

from langchain_community.tools import DuckDuckGoSearchResults, BraveSearch, WikipediaQueryRun, ArxivQueryRun
from langchain_community.utilities import BraveSearchWrapper, ArxivAPIWrapper, WikipediaAPIWrapper
# from langchain_tavily import TavilySearch

from src.config.loader import load_yaml_config
from src.config.tools import SELECTED_SEARCH_ENGINE, SearchEngine
from src.tools.decorators import create_logged_tool
from src.tools.tavily_search import TavilySearchWithImage

LoggedTavilySearch = create_logged_tool(TavilySearchWithImage)
LoggedDuckDuckGoSearch = create_logged_tool(DuckDuckGoSearchResults)
LoggedBraveSearch = create_logged_tool(BraveSearch)
LoggedArxivSearch = create_logged_tool(ArxivQueryRun)
LoggedWikipediaSearch = create_logged_tool(WikipediaQueryRun)
logger = logging.getLogger(__name__)


def get_search_config():
    config = load_yaml_config("conf.yaml")
    search_config = config.get("SEARCH_ENGINE", {})
    return search_config


def get_web_search_tool(max_search_results: int = 5):
    search_config = get_search_config()

    if SELECTED_SEARCH_ENGINE == SearchEngine.TAVILY.value:
        include_domains: Optional[List[str]] = search_config.get("include_domains", [])
        exclude_domains: Optional[List[str]] = search_config.get("exclude_domains", [])

        logger.info(
            f"Searching with {max_search_results} results, include_domains: {include_domains}, exclude_domains: {exclude_domains}")

        return LoggedTavilySearch(
            name="web_search",
            max_results=max_search_results,
            include_raw_content=True,
            include_images=True,
            include_image_descriptions=True,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
        )
    elif SELECTED_SEARCH_ENGINE == SearchEngine.DUCKDUCKGO.value:
        return LoggedDuckDuckGoSearch(
            name="web_search",
            num_results=max_search_results,
        )
    elif SELECTED_SEARCH_ENGINE == SearchEngine.BRAVE_SEARCH.value:
        return LoggedBraveSearch(
            name="web_search",
            search_wrapper=BraveSearchWrapper(
                api_key=os.getenv("BRAVE_SEARCH_API_KEY", ""),
                search_kwargs={"count": max_search_results},
            ),
        )
    elif SELECTED_SEARCH_ENGINE == SearchEngine.ARXIV.value:
        return LoggedArxivSearch(
            name="web_search",
            api_wrapper=ArxivAPIWrapper(
                top_k_results=max_search_results,
                load_max_docs=max_search_results,
                load_all_available_meta=True,
            ),
        )
    elif SELECTED_SEARCH_ENGINE == SearchEngine.WIKIPEDIA.value:
        wiki_lang = search_config.get("wikipedia_lang", "en")
        wiki_doc_content_chars_max = search_config.get(
            "wikipedia_doc_content_chars_max", 4000
        )
        return LoggedWikipediaSearch(
            name="web_search",
            api_wrapper=WikipediaAPIWrapper(
                lang=wiki_lang,
                top_k_results=max_search_results,
                load_all_available_meta=True,
                doc_content_chars_max=wiki_doc_content_chars_max,
            ),
        )
    else:
        raise ValueError(f"Unsupported search engine: {SELECTED_SEARCH_ENGINE}")

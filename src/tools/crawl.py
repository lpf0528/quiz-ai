from typing import Annotated

import logging

from langchain_core.tools import tool

from src.crawler.crawler import Crawler
from src.tools.decorators import log_io

logger = logging.getLogger(__name__)


@tool
@log_io
def crawl_tool(url: Annotated[str, '']):
    """Use this to crawl a url and get a readable content in markdown format."""
    try:
        crawler = Crawler()
        article = crawler.crawl(url)
        return {
            'url': url,
            'crawled_content': article.to_markdown()[:1000]
        }
    except BaseException as e:
        error_msg = f"Failed to crawl. Error: {repr(e)}"
        logger.error(error_msg)
        return error_msg


if __name__ == '__main__':
    data = crawl_tool(
        'https://medium.com/@daniel.puenteviejo/the-science-of-control-how-temperature-top-p-and-top-k-shape-large-language-models-853cb0480dae')
    print(data)

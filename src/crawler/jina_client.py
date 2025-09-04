import logging
import os

import requests
from readabilipy import simple_json_from_html_string

logger = logging.getLogger(__name__)


class JinaClient:
    def crawl(self, url: str, return_format: str = "html") -> str:
        headers = {
            "Content-Type": "application/json",
            "X-Return-Format": return_format,
        }
        if os.getenv('JINA_API_KEY'):
            headers["Authorization"] = f"Bearer {os.getenv('JINA_API_KEY')}"
        else:
            logger.warning(
                "Jina API key is not set. Provide your own key to access a higher rate limit. See https://jina.ai/reader for more information."
            )
        data = {
            "url": url,
        }
        response = requests.post("https://r.jina.ai/", headers=headers, json=data)
        return response.text


if __name__ == '__main__':
    # from dotenv import load_dotenv
    #
    # load_dotenv()
    jina_client = JinaClient()
    html = jina_client.crawl(
        'https://medium.com/@daniel.puenteviejo/the-science-of-control-how-temperature-top-p-and-top-k-shape-large-language-models-853cb0480dae')

    # article = simple_json_from_html_string(html, use_readability=True)
    # print(article)

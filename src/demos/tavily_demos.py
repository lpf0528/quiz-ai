# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
from dotenv import load_dotenv

load_dotenv()
import json
import logging
from typing import Dict, List, Optional, Tuple, Union

from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)

# from langchain_tavily.tavily_search import TavilySearch
from langchain_community.tools.tavily_search.tool import TavilySearchResults
from pydantic import Field

import json
from typing import Dict, List, Optional

import aiohttp
import requests
from langchain_tavily._utilities import TAVILY_API_URL
from langchain_tavily.tavily_search import (
    TavilySearchAPIWrapper as OriginalTavilySearchAPIWrapper, TavilySearch,
)


class EnhancedTavilySearchAPIWrapper(OriginalTavilySearchAPIWrapper):
    def raw_results(
            self,
            query: str,
            max_results: Optional[int] = 5,
            search_depth: Optional[str] = "advanced",
            include_domains: Optional[List[str]] = [],
            exclude_domains: Optional[List[str]] = [],
            include_answer: Optional[bool] = False,
            include_raw_content: Optional[bool] = False,
            include_images: Optional[bool] = False,
            include_image_descriptions: Optional[bool] = False,
    ) -> Dict:
        params = {
            "api_key": self.tavily_api_key.get_secret_value(),
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_domains": include_domains,
            "exclude_domains": exclude_domains,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
            "include_images": include_images,
            "include_image_descriptions": include_image_descriptions,
        }
        response = requests.post(
            # type: ignore
            f"{TAVILY_API_URL}/search",
            json=params,
        )
        response.raise_for_status()
        return response.json()

    async def raw_results_async(
            self,
            query: str,
            max_results: Optional[int] = 5,
            search_depth: Optional[str] = "advanced",
            include_domains: Optional[List[str]] = [],
            exclude_domains: Optional[List[str]] = [],
            include_answer: Optional[bool] = False,
            include_raw_content: Optional[bool] = False,
            include_images: Optional[bool] = False,
            include_image_descriptions: Optional[bool] = False,
    ) -> Dict:
        """Get results from the Tavily Search API asynchronously."""

        # Function to perform the API call
        async def fetch() -> str:
            params = {
                "api_key": self.tavily_api_key.get_secret_value(),
                "query": query,
                "max_results": max_results,
                "search_depth": search_depth,
                "include_domains": include_domains,
                "exclude_domains": exclude_domains,
                "include_answer": include_answer,
                "include_raw_content": include_raw_content,
                "include_images": include_images,
                "include_image_descriptions": include_image_descriptions,
            }
            async with aiohttp.ClientSession(trust_env=True) as session:
                async with session.post(f"{TAVILY_API_URL}/search", json=params) as res:
                    if res.status == 200:
                        data = await res.text()
                        return data
                    else:
                        raise Exception(f"Error {res.status}: {res.reason}")

        results_json_str = await fetch()
        return json.loads(results_json_str)

    def clean_results_with_images(
            self, raw_results: Dict[str, List[Dict]]
    ) -> List[Dict]:
        results = raw_results["results"]
        """Clean results from Tavily Search API."""
        clean_results = []
        for result in results:
            clean_result = {
                "type": "page",
                "title": result["title"],
                "url": result["url"],
                "content": result["content"],
                "score": result["score"],
            }
            if raw_content := result.get("raw_content"):
                clean_result["raw_content"] = raw_content
            clean_results.append(clean_result)
        images = raw_results["images"]
        for image in images:
            clean_result = {
                "type": "image",
                "image_url": image["url"],
                "image_description": image["description"],
            }
            clean_results.append(clean_result)
        return clean_results


logger = logging.getLogger(__name__)


class TavilySearchWithImages(TavilySearchResults):  # type: ignore[override, override]

    include_image_descriptions: bool = False

    api_wrapper: EnhancedTavilySearchAPIWrapper = Field(
        default_factory=EnhancedTavilySearchAPIWrapper
    )  # type: ignore[arg-type]

    def _run(
            self,
            query: str,
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Tuple[Union[List[Dict[str, str]], str], Dict]:
        """Use the tool."""
        # TODO: remove try/except, should be handled by BaseTool
        try:
            raw_results = self.api_wrapper.raw_results(
                query,
                self.max_results,
                self.search_depth,
                self.include_domains,
                self.exclude_domains,
                self.include_answer,
                self.include_raw_content,
                self.include_images,
                self.include_image_descriptions,
            )
        except Exception as e:
            return repr(e), {}
        cleaned_results = self.api_wrapper.clean_results_with_images(raw_results)
        logger.debug(
            "sync: %s", json.dumps(cleaned_results, indent=2, ensure_ascii=False)
        )
        return cleaned_results, raw_results

    async def _arun(
            self,
            query: str,
            run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> Tuple[Union[List[Dict[str, str]], str], Dict]:
        """Use the tool asynchronously."""
        try:
            raw_results = await self.api_wrapper.raw_results_async(
                query,
                self.max_results,
                self.search_depth,
                self.include_domains,
                self.exclude_domains,
                self.include_answer,
                self.include_raw_content,
                self.include_images,
                self.include_image_descriptions,
            )
        except Exception as e:
            return repr(e), {}
        cleaned_results = self.api_wrapper.clean_results_with_images(raw_results)
        logger.debug(
            "async: %s", json.dumps(cleaned_results, indent=2, ensure_ascii=False)
        )
        return cleaned_results, raw_results


tool = TavilySearchWithImages(
    max_results=5,
    include_answer=True,
    include_raw_content=True,
    include_images=True,
    include_image_descriptions=True
)

results, raw_results = tool._run('什么是langchain')
import json

# print(json.dumps(results, ensure_ascii=False))


tool = TavilySearch(
    max_results=5,
    topic="general",
    include_answer=True,
    include_raw_content=True,
    include_images=True,
    include_image_descriptions=True,
)

result = tool.invoke({"query": "什么是langchain"})
print(json.dumps(result, indent=2, ensure_ascii=False))

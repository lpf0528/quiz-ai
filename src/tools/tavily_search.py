from typing import Optional, List, Literal, Dict, Any

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_tavily import TavilySearch


class TavilySearchWithImage(TavilySearch):

    def _run(
            self,
            query: str,
            include_domains: Optional[List[str]] = None,
            exclude_domains: Optional[List[str]] = None,
            search_depth: Optional[Literal["basic", "advanced"]] = None,
            include_images: Optional[bool] = None,
            time_range: Optional[Literal["day", "week", "month", "year"]] = None,
            topic: Optional[Literal["general", "news", "finance"]] = None,
            include_favicon: Optional[bool] = None,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None,
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> List[Dict]:
        raw_results = super()._run(
            query,
            include_domains,
            exclude_domains,
            search_depth,
            include_images,
            time_range,
            topic,
            include_favicon,
            start_date,
            end_date,
            run_manager,
        )
        results = raw_results["results"]
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

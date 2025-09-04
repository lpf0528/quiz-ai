from src.crawler.jina_client import JinaClient
from src.crawler.readability_extractor import ReadabilityExtractor


class Crawler:
    def crawl(self, url: str):
        jina_client = JinaClient()
        html = jina_client.crawl(url, return_format="html")
        extractor = ReadabilityExtractor()

        article = extractor.extract_article(html)
        article.url = url
        return article


if __name__ == '__main__':
    crawler = Crawler()
    article = crawler.crawl(
        "https://medium.com/@daniel.puenteviejo/the-science-of-control-how-temperature-top-p-and-top-k-shape-large-language-models-853cb0480dae")
    print(article.to_markdown())

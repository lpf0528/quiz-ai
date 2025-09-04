from readabilipy import simple_json_from_html_string

from src.crawler.article import Article


class ReadabilityExtractor:

    def extract_article(self, html: str):
        # 从 HTML 源文件中提取文章。
        article = simple_json_from_html_string(html, use_readability=True)

        return Article(title=article.get("title"),
                       html_content=article.get("content"))

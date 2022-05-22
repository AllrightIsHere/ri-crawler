from typing import Optional

from bs4 import BeautifulSoup
from threading import Thread
import requests
from urllib.parse import urlparse, urljoin, ParseResult

from crawler.scheduler import Scheduler


class PageFetcher(Thread):
    def __init__(self, obj_scheduler):
        super().__init__()
        self.obj_scheduler: Scheduler = obj_scheduler

    def request_url(self, obj_url: ParseResult) -> Optional[bytes] or None:
        """
        :param obj_url: Instância da classe ParseResult com a URL a ser requisitada.
        :return: Conteúdo em binário da URL passada como parâmetro, ou None se o conteúdo não for HTML
        """

        response = requests.get(obj_url.geturl(), {
            "headers": {
                "user-agent": self.obj_scheduler.usr_agent
            }
        }, timeout=20)

        return response.content if 'text/html' in response.headers['content-type'] else None

    def discover_links(self, obj_url: ParseResult, depth: int, bin_str_content: bytes):
        """
        Retorna os links do conteúdo bin_str_content da página já requisitada obj_url
        """
        soup = BeautifulSoup(bin_str_content, "lxml")
        for link in soup.select("body a"):
            if not link.has_attr("href"):
                continue

            obj_new_url = link["href"]

            if("://" not in obj_new_url):
                obj_new_url = f'{obj_url.scheme}://{obj_url.hostname}/{obj_new_url}'

            new_depth = depth + 1

            if obj_url.hostname not in obj_new_url:
                new_depth = 0

            yield urlparse(obj_new_url), new_depth

    def crawl_new_url(self):
        """
        Coleta uma nova URL, obtendo-a do escalonador
        """
        base_url, depth = self.obj_scheduler.get_next_url()

        if base_url:
            base_html = self.request_url(base_url)
            if base_html is not None:
                print(f'URL: {base_url.geturl()}')
                self.obj_scheduler.count_fetched_page()
                for link, d in self.discover_links(base_url, depth, base_html):
                    self.obj_scheduler.add_new_page(link, d)

    def run(self):
        """
        Executa coleta enquanto houver páginas a serem coletadas
        """
        while not self.obj_scheduler.has_finished_crawl():
            try:
                self.crawl_new_url()
            except Exception as e:
                print(f'Error: {e}')
        

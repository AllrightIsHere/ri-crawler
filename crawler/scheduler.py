from time import sleep
from urllib import robotparser
from urllib.parse import ParseResult

from util.threads import synchronized
from collections import OrderedDict
from .domain import Domain


class Scheduler:
    # tempo (em segundos) entre as requisições
    TIME_LIMIT_BETWEEN_REQUESTS = 20

    def __init__(self, usr_agent: str, page_limit: int, depth_limit: int, arr_urls_seeds):
        """
        :param usr_agent: Nome do `User agent`. Usualmente, é o nome do navegador, em nosso caso,  será o nome do coletor (usualmente, terminado em `bot`)
        :param page_limit: Número de páginas a serem coletadas
        :param depth_limit: Profundidade máxima a ser coletada
        :param arr_urls_seeds: ?

        Demais atributos:
        - `page_count`: Quantidade de página já coletada
        - `dic_url_per_domain`: Fila de URLs por domínio (explicado anteriormente)
        - `set_discovered_urls`: Conjunto de URLs descobertas, ou seja, que foi extraída em algum HTML e já adicionadas na fila - mesmo se já ela foi retirada da fila. A URL armazenada deve ser uma string.
        - `dic_robots_per_domain`: Dicionário armazenando, para cada domínio, o objeto representando as regras obtidas no `robots.txt`
        """
        self.usr_agent = usr_agent
        self.page_limit = page_limit
        self.depth_limit = depth_limit
        self.page_count = 0

        self.dic_url_per_domain = OrderedDict()
        self.set_discovered_urls = set()
        self.dic_robots_per_domain = {}

        for seed in arr_urls_seeds:
            self.add_new_page(seed, 1)

    @synchronized
    def count_fetched_page(self) -> None:
        """
        Contabiliza o número de paginas já coletadas
        """
        self.page_count += 1

    @synchronized
    def has_finished_crawl(self) -> bool:
        """
        :return: True se finalizou a coleta. False caso contrário.
        """
        return self.page_count >= self.page_limit

    @synchronized
    def can_add_page(self, obj_url: ParseResult, depth: int) -> bool:
        return depth < self.depth_limit \
            and not self.has_finished_crawl() \
            and not (obj_url.geturl() in self.set_discovered_urls)

    @synchronized
    def add_new_page(self, obj_url: ParseResult, depth: int) -> bool:
        if not self.can_add_page(obj_url, depth):
            return False

        domain = Domain(obj_url.hostname, self.TIME_LIMIT_BETWEEN_REQUESTS)
        if domain not in self.dic_url_per_domain.keys():
            self.dic_url_per_domain[
                domain
            ] = [(obj_url, depth)]
        else:
            self.dic_url_per_domain[
                domain
            ].append((obj_url, depth))

        self.set_discovered_urls.add(obj_url.geturl())
        return True

    @synchronized
    def get_next_url(self) -> tuple:

        for domain in self.dic_url_per_domain.keys():
            if domain.is_accessible():
                domain.accessed_now()
                urls = self.dic_url_per_domain[domain]
                if len(urls) > 0:
                    self.count_fetched_page()
                    return self.dic_url_per_domain[domain].pop(0)
                else:
                    self.dic_url_per_domain.pop(domain)

        sleep(self.TIME_LIMIT_BETWEEN_REQUESTS)
        return None, None

    def can_fetch_page(self, obj_url: ParseResult) -> bool:
        domain = Domain(obj_url.hostname, self.TIME_LIMIT_BETWEEN_REQUESTS)

        if domain not in self.dic_robots_per_domain.keys():
            new_parser = robotparser.RobotFileParser()
            new_parser.set_url(
                f'{obj_url.scheme}://{obj_url.hostname}/robots.txt')

            new_parser.read()
            self.dic_robots_per_domain[domain] \
                = new_parser

        robots: robotparser.RobotFileParser = self.dic_robots_per_domain[domain]

        return robots.can_fetch(self.usr_agent, obj_url.geturl())

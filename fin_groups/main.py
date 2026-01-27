from fin_groups.db import init_db
from crawler import CompanyCrawler

conn = init_db()
crawler = CompanyCrawler(conn)

owners = crawler.crawl_company("37079170")
print(owners)
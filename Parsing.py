import csv
import requests
from ProxyChecker import CheckerMain
import time
from alive_progress import alive_bar
from bs4 import BeautifulSoup as bs
import queue
from threading import Thread




def create_csv(filename, order):
    with open(filename, 'w', encoding='utf-8', newline='') as file:
        csv.DictWriter(file, fieldnames=order).writeheader()


def csv_write(filename, data):
    with open(filename, "+a", encoding='utf-8', newline='') as csvfile:
        csv.DictWriter(csvfile, fieldnames=list(data)).writerow(data)
        print(f"{data['Название продукта']} записан")


def catalog_parsing(url, filename):
    category_url = url
    q = get_proxies()
    with open("valid_proxies.txt", "r") as proxies:
        count = len([proxy.replace("\n", "") for proxy in proxies.readlines()])
    Threading(get_working_proxy, count, q)
    print("Просматриваю рабочие прокси")
    with open("works.txt", "r") as proxies:
        proxies = list(map(lambda x: x.replace('\n', ''), proxies.readlines()))
        print(proxies)
    if len(proxies) <= 0:
        print("Ни один прокси не сработал на этом сайте")
        quit()
    else:
        proxies = list(map(lambda x: {"http": f"http://{x}", "https": f"http://{x}"}, [proxy for proxy in proxies]))
    resp = requests.get(url).text
    products_count = int(bs(resp, "lxml").find("span", class_="goods-count").find_all("span")[2].text.replace(" ", "").replace("\n", "").replace("товара", "").replace("товаров", "").replace("товар", "").replace("\xa0", ""))
    keywords = str(input("Введите ключевые слова, разделяя их пробелами\n")).capitalize().lower().split(" ")
    with alive_bar(products_count) as bar:
        bar.text = "-> Парсинг каталога"
        if len(proxies) > 1:
            try:
                response = requests.get(url, proxies=proxies[0]).text
            except Exception:
                try:
                    response = requests.get(url, proxies=proxies[1]).text
                except Exception:
                    if len(proxies) > 2:
                        response = requests.get(url, proxies=proxies[2]).text
        else:
            response = requests.get(url, proxies=proxies[0]).text
        soup = bs(response, "lxml")
        nextpage_url = f'{category_url}?sort=popular&' + str(soup.find("div", class_="pageToInsert pagination__wrapper").find("a", class_="pagination__next")).split('"')[5].split("?")[-1]

        # keywords = ["соль", ]
        cards = list(map(lambda x: rf"https://www.wildberries.ru/catalog/{str(x.find('a')).split('catalog/')[1].split('/detail')[0]}/detail.aspx?",\
                            soup.find(class_="product-card-list").find_all("div", class_="product-card__wrapper")))
        q = queue.Queue()
        for url in cards:
            q.put(url)
        Threading(current_product_parser, 100, q, proxies, keywords, filename, bar)
        catalog_parsing_continue(nextpage_url, filename, keywords, proxies, bar)


def catalog_parsing_continue(nextpage_url, filename, keywords, proxies, bar):
    category_url = nextpage_url.split("?")[0]
    url = nextpage_url
    if len(proxies) > 1:
        try:
            response = requests.get(url, proxies=proxies[0]).text
        except Exception:
            try:
                response = requests.get(url, proxies=proxies[1]).text
            except Exception:
                if len(proxies) > 2:
                    response = requests.get(url, proxies=proxies[2]).text
    else:
        response = requests.get(url, proxies=proxies[0]).text
    soup = bs(response, "lxml")
    nextpage_url = f'{category_url}?sort=popular&'\
                   + str(soup.find("div", class_="pageToInsert pagination__wrapper").find("a", class_="pagination__next")).split('"')[5].split("?")[-1]
    cards = list(map(lambda x: rf"https://www.wildberries.ru/catalog/{str(x.find('a')).split('catalog/')[1].split('/detail')[0]}/detail.aspx?", \
                     soup.find(class_="product-card-list").find_all("div", class_="product-card__wrapper")))
    q = queue.Queue()
    for url in cards:
        q.put(url)
    Threading(current_product_parser, 100, q, proxies, keywords, filename, bar)
    catalog_parsing_continue(nextpage_url, filename, keywords, proxies, bar)


def current_product_parser(q, proxies, keywords, filename, bar):
    url = q.get()
    if len(proxies) > 1:
        try:
            response = requests.get(url, proxies=proxies[0]).text
        except Exception:
            try:
                response = requests.get(url, proxies=proxies[1]).text
            except Exception:
                if len(proxies) > 2:
                    response = requests.get(url, proxies=proxies[2]).text
    else:
        try:
            response = requests.get(url, proxies=proxies[0]).text
        except Exception:
            pass
    try:
        soup = bs(response, "lxml")
        productname = soup.find("h1").text
        for keyword in keywords:
            check = keyword in productname.lower()
        if check:
            bar()
            soup = bs(response, "lxml")
            productname = soup.find("h1").text
            photos = soup.find("div", class_="sw-slider-kt-mix__wrap").find("ul").find_all("img")
            wildnumb = soup.find('span', id="productNmId").text
            photourls = " ".join(list(map(lambda x: "https:" + x.split('"')[3], [str(photoline) for photoline in photos])))
            discountcost = soup.find(class_="price-block__price-wrap").find("span").text.replace("&nbsp;", "").replace("\n", "").strip().replace("\xa0", "")
            try:
                cost = soup.find(class_="price-block__price-wrap").find("del").text.replace("&nbsp;", "").replace("\n", "").strip().replace("\xa0", "")
            except:
                cost = discountcost
            discount = str(str(round(1 - int(discountcost.replace("₽", ""))/int(cost.replace("₽", "")), 3) * 100) + "%")
            reviewscount = soup.find("span", class_="same-part-kt__count-review").text.replace("\n", "").replace("\xa0", "").strip()
            rating = str(soup.find("a", {'data-name-for-wba': "Item_Feedback_Top"}).find_all("span")[0].text.replace("\n", "").strip()) + " звёзд"
            data = {"Артикул": wildnumb, "Ссылка на товар": url, "Ссылки на фото": photourls, "Название продукта": productname, "Стоимость": cost,\
                    "Стоимость со скидкой": discountcost, "Скидка": discount, "Количество отзывов": reviewscount, "Рейтинг": rating}
            csv_write(filename, data)
    except Exception:
        pass
    finally:
        bar()


def get_proxies():
    q = queue.Queue()
    with open("proxy.txt", "r") as proxy:
        rawproxies = len(proxy.read().split("\n"))
        enter = input(f"Хотите отправить прокси на проверку? это займёт примерно {round(rawproxies/128) + 1} секунд\n")
    if enter.lower() in ["y", "yes", "да", "ye", "д"]:
        CheckerMain()
    else:
        pass
    with open("valid_proxies.txt", "r") as proxies:
        proxy_list = [proxy.replace("\n", "") for proxy in proxies.readlines()]
    for proxy in proxy_list:
        q.put(proxy)
    return q


def get_working_proxy(q):
    with open("works.txt", "w"):
        pass
    with open("valid_proxies.txt", "r") as proxies:
        proxy_list = len([proxy.replace("\n", "") for proxy in proxies.readlines()])
    proxy = q.get()
    proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
    url = "https://www.wildberries.ru/"
    try:
        response = requests.get(url, proxies=proxies, timeout=3)
        with open("works.txt", "a") as working:
            working.write(f"{proxy}\n")
            print("Найден рабочий прокси")
    except Exception as ex:
        pass
def Threading(function, count, q, *args):
    Threads = 128
    if len(args) == 4:
        if count >= Threads:
            for a in range(count//Threads):
                for i in range(Threads):
                    th = Thread(target=function, args=(q, args[0], args[1], args[2], args[3]))
                    th.start()
                th.join()
            for b in range(count-Threads*(a+1)):
                th = Thread(target=function, args=(q, args[0], args[1], args[2], args[3]), daemon=True)
                th.start()
            th.join()
            time.sleep(3)
        elif count < Threads:
            for i in range(count):
                th = Thread(target=function, args=(q, args[0], args[1], args[2], args[3]), daemon=True)
                th.start()
            th.join()
            time.sleep(3)
    else:
        if count >= Threads:
            for a in range(count//Threads):
                for i in range(Threads):
                    th = Thread(target=function, args=(q,))
                    th.start()
                th.join()
            for b in range(count-Threads*(a+1)):
                th = Thread(target=function, args=(q,), daemon=True)
                th.start()
            th.join()
            time.sleep(3)
        elif count < Threads:
            for i in range(count):
                th = Thread(target=function, args=(q,), daemon=True)
                th.start()
            th.join()
            time.sleep(3)




def main():
    filename = "result.csv"
    order = ["Артикул", "Ссылка на товар", "Ссылки на фото", "Название продукта", "Стоимость", "Стоимость со скидкой", "Скидка", "Количество отзывов", "Рейтинг"]
    create_csv(filename, order)
    url = "https://www.wildberries.ru/catalog/krasota/uhod-za-kozhey/dlya-vanny-i-dusha/krasota"
    url = str(input("Введите страницу сайта wildberries\n"))
    catalog_parsing(url, filename)


if __name__ == '__main__':
    main()

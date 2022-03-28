import requests
from threading import Thread
from alive_progress import alive_bar
import os
import queue
import time

def CheckerMain():
    q = queue.Queue()
    # os.remove(os.path.join(os.getcwd(), "valid_proxies.txt"))
    with open("valid_proxies.txt", "w") as valid_proxies:
        pass
    with open("proxy.txt", "r") as proxy:
        rawproxies = [{"http": f"http://{proxy.split(' ')[0]}",
                       "https": f"http://{proxy.split(' ')[0]}"}
                      for proxy in proxy.read().split("\n")]
    for proxy in rawproxies:
        q.put(proxy)
    with open("valid_proxies.txt", "+a") as valid_proxies:
        Threading(checker, rawproxies, q)
        proxies = [proxies.replace("\n", "") for proxies in valid_proxies.readlines()]
        print(f'Найдено {len(proxies)} валидных прокси')


def checker(q, bar):
    url = "https://www.wildberries.ru/"
    proxies = q.get()
    try:
        response = requests.get(url, proxies=proxies, timeout=2)
        with open("valid_proxies.txt", "a") as new_valid_proxies:
            with open("valid_proxies.txt", "r") as prx:
                valid_proxies = prx.read().replace(" ", "").split("\n")
            if proxies.get("http").replace("http://", "") not in valid_proxies:
                new_valid_proxies.write(f'{proxies.get("http").replace("http://", "")}\n')
            else:
                pass
    except Exception:
        pass
    finally:
        # os.system('cls')
        bar()


def Threading(function, *args):
    count = len(args[0])
    q = args[1]
    Threads = 4096
    with alive_bar(count) as bar:

        bar.text = "-> Проверка прокси"
        for a in range(1, count//Threads + 1):
            for i in range(Threads):
                th = Thread(target=function, args=(q, bar), daemon=True)
                th.start()
        time.sleep(1)
        ost = count-Threads*a
        for b in list(range(ost)):
            th = Thread(target=function, args=(q, bar), daemon=True)
            th.start()
        th.join()
        time.sleep(3)





if __name__ == "__main__":
    CheckerMain()
    input("Проверка завершена! Нажмите Enter чтобы закрыть консоль\n")
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import time



def setup(q):
    # це функція зупускає гугл хром в акаунті KSEA і повертає данні, з якими можна працювати
    # треба додати можливість надавати функціх посиланя
    print("set up")
    driver_chrome = webdriver.Chrome()

    url = "https://www.google.com/search?q=" + q
    print(url)
    driver_chrome.get(url)

    return driver_chrome

def save_cookies():
    # зберегти кокс
    input("Type any symbol after captcha: ")


def all_pages(driver):
    element = driver.find_element(By.ID, "botstuff")
    element.find_elements(By.CLASS_NAME, "NKTSme")

    pages = []
    next_page_block = element.find_elements(By.TAG_NAME, "a")
    for item in next_page_block:
        # link = item.get_attribute('href')
        print(item.get_attribute('href'))
        print(item, "\n")

        pages.append(item)

    print(f"there are {len(pages)} pages")

    return pages


def search(driver):
    print("Searching...")
    element = driver.find_element(By.ID, "search")
    element.find_elements(By.CLASS_NAME, "MjjYud")

    links = []
    link_block = element.find_elements(By.TAG_NAME, "a")
    for item in link_block:
        link = item.get_attribute('href')
        links.append(link)
    return links


def get_links_from_google(q):
    driver = setup(q)
    save_cookies()


    links = [n for n in search(driver)]
    print(all_pages(driver))

    # for page in all_pages(driver):
    #     page.click()
    #     time.sleep(5)
    #     for item in search(driver):
    #         links.append(item)


    # Save to file
    with open("google_links.txt", "w") as file:
        for item in links:
            file.write(item)
            file.write("\n")

    print(f"Saved {len(links)} links")

    # print("time stop")
    # time.sleep(1000000)

    time.sleep(25)
    driver.close()



q = "Олег%20Нів%27євський"
get_links_from_google(q)



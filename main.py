import sys
import time
from csv import DictWriter

import requests
from lxml import html
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import Chrome, ChromeOptions

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                         'AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Chrome/91.0.4472.124 Safari/537.36'}

FIELDNAMES = ['Город', 'Название клиники', 'Номер телефона', 'Ссылка на сайт',
              'Ссылка на ВК', 'Ссылка на Instagram', 'Информация о клинике',
              'Внутренняя ссылка']

parsed = []


def get_doc(url, params=None, headers=None):
    response = requests.get(url, params=params, headers=headers)
    if not response:
        print(f'Failed to get {url}')
    return html.fromstring(response.text)


def get_driver():
    options = ChromeOptions()
    # options.add_argument('--headless')
    # options.add_argument(f'user-agent={HEADERS["User-Agent"]}')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    return Chrome('binary/chromedriver.exe', options=options)


def list_get(list_, function_, return_attr=None, default=None):
    filtered = list(filter(function_, list_))
    if not filtered:
        return default
    try:
        return (eval(f"filtered[0].{return_attr}")
                if return_attr is not None and isinstance(return_attr, str) else filtered[0])
    except AttributeError:
        return None


def safe_get(list_, idx, default=None):
    try:
        return list_[idx]
    except IndexError:
        return default


def check_captcha(module, url):
    try:
        if ((not isinstance(module, Chrome) and bool(module.xpath('//*[@class="g-recaptcha"]')))
                or (isinstance(module, Chrome) and bool(module.find_element_by_class_name('g-recaptcha')))):
            input(f'Пройдите капчу ({url}) и нажмите Enter: ')
            return True
    except NoSuchElementException:
        return False
    return False


def parse_page(url, city_name, params=None, headers=None):
    doc = get_doc(url, params, headers)
    if doc is None:
        return None
    if check_captcha(doc, url):
        return parse_page(url, city_name, params, headers)
    social_blocks = doc.xpath('//*[@class="link-social__item"]//a')
    return {
        'Город': city_name,
        'Название клиники': (doc.xpath('//h1[@itemprop="name"]/text()')[0].strip()
                             if doc.xpath('//h1[@itemprop="name"]') else 'Не указано'),
        'Номер телефона': (','.join(doc.xpath('////span[@class="telnumb"]/a[@itemprop="telephone"]/@content'))
                           if doc.xpath('//span[@class="telnumb"]/a[@itemprop="telephone"]/@content')
                           else 'Не указан'),
        'Ссылка на сайт': list_get(
            social_blocks, lambda block: 'официальный сайт' in block.text_content().strip().lower(),
            return_attr='get("href")', default='Не указана'),
        'Ссылка на ВК': list_get(
            social_blocks, lambda block: block.get('title') == 'Вконтакте',
            return_attr='get("href")', default='Не указана'),
        'Ссылка на Instagram': list_get(
            social_blocks, lambda block: block.get('title') == 'Инстаграм',
            return_attr='get("href")', default='Не указана'),
        'Информация о клинике': safe_get(
            doc.xpath('//*[@itemprop="description"]/text()'), 0, default='Не указана'),
        'Внутренняя ссылка': url
    }


def parse_category(url, city_name, params=None, headers=None):
    driver = get_driver()
    driver.get(url)
    if check_captcha(driver, url):
        driver.get(url)
    total_count = parse_total_count(driver)
    if not total_count:
        print(f'Failed to get total_count, unable to parse category {url}')
        sys.exit(-1)
    links = []
    while len(links) != total_count:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        links = driver.find_elements_by_xpath('//*[@id="pager_more_clinics"]//a[@class="doctor__item-name"]')
    links = [link.get_attribute('href') for link in links]
    driver.close()
    driver.quit()
    print(f'Category: {url}, total clinics count: {len(links)}')
    for link in links:
        if link not in parsed:
            yield parse_page(link, city_name, params, headers)


def get_url_host(url):
    return '//'.join(url.split('/')[:3:2])


def parse_city_links(doc):
    host = get_url_host(url)
    return [host + link for link in doc.xpath('//*[@class="price-block price-hospital-kol0"]/ul//a/@href')]


def parse_total_city_count(doc):
    try:
        header = doc.xpath('//*[@class="bg-and-offset__h1"]/text()')[0]
        return int(header.split(': ')[-1].split()[1])
    except (IndexError, ValueError):
        return print('Failed to parse total count of city')


def parse_total_count(driver):
    try:
        return int(driver.find_element_by_xpath('//*[@class="doctor-head__number"]/span').text)
    except (ValueError, AttributeError):
        return print('Failed to parse total count of page')


def main(url, city_name, output_filename='output.csv'):
    global parsed
    parsed = []
    doc = get_doc(url, headers=HEADERS)
    links = parse_city_links(doc)
    if not links:
        print(f'Failed to get links of {url}')
    total_count = parse_total_city_count(doc)
    count = 0
    for link in links:
        for clinic in parse_category(link, city_name, start_from):
            if clinic:
                with open(output_filename, 'a', newline='', encoding='utf-8') as f:
                    writer = DictWriter(f, fieldnames=FIELDNAMES, delimiter=';')
                    writer.writerow(clinic)
                parsed.append(link)
                count += 1
                print(f'Parsed {count}/{total_count}', flush=True, end='\r')
            else:
                if link not in parsed:
                    count += 1
                    print(f'Failed to parse {count}/{total_count}. URL: {link}')
                else:
                    print('Skip')
    return f'%s Finished parsing {url} %s' % ('#' * 10, '#' * 10)


if __name__ == '__main__':
    start_time = time.time()
    output_filename = 'output.csv'
    # with open(output_filename, 'w', newline='', encoding='utf-8') as f:
    #     writer = DictWriter(f, fieldnames=FIELDNAMES, delimiter=';')
    #     writer.writeheader()
    with open('links.txt', encoding='utf-8') as f:
        data = [x.strip().split(',') for x in f.readlines()]
    for url, city_name in data:
        print(f'%s Started parsing {url} %s' % ('#' * 10, '#' * 10))
        callback = main(url, city_name, output_filename)
        if callback:
            print(callback)
        print()
    print(f'Completed in {time.time() - start_time:.2f}')

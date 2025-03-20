import time
import sqlite3
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

# Настройки Selenium
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Отключение обнаружения автоматизации
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36")  # Установка User-Agent

# Путь к драйверу Chrome (нужно установить chromedriver на сервере)
service = Service('/usr/bin/chromedriver')  # Укажите правильный путь

# Чтение списка артикулов из файла
def load_links(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file if line.strip()]

# Подключение к локальной SQLite базе данных
def init_db():
    conn = sqlite3.connect('ozon_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            product_code TEXT,
            price REAL,
            card_price REAL,
            original_price REAL,
            price_change TEXT,
            rating REAL,
            questions_count INTEGER,
            reviews_count INTEGER,
            available INTEGER
        )
    ''')
    conn.commit()
    return conn, cursor

# Функция парсинга данных с одной страницы
def parse_product_page(driver, article, cursor, conn):
    url = f"https://www.ozon.ru/product/{article}/"  # Формируем ссылку на основе артикула
    driver.get(url)
    time.sleep(5)  # Увеличенная пауза для загрузки страницы

    # Артикул товара
    product_code = article

    # Текущие дата и время
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Пример XPath (укажите свои)
    xpaths = {
        'price': '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[2]/div/div/div[1]/div[2]/div/div[1]/div/div/div[1]/div[2]/div/div[1]/span[1]',
        'card_price': '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[2]/div/div/div[1]/div[2]/div/div[1]/div/div/div[1]/div[1]/button/span/div/div[1]/div/div/span',
        'original_price': '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[2]/div/div/div[1]/div[2]/div/div[1]/div/div/div[1]/div[2]/div/div[1]/span[2]',  # Убрано /text()
        'rating': '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[1]/div[1]/div[2]/div/div/div/div[2]/div[1]/a/div',
        'questions_count': '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[1]/div[1]/div[2]/div/div/div/div[2]/div[2]/a/div',
        'reviews_count': '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[1]/div[1]/div[2]/div/div/div/div[2]/div[1]/a/div',
        'buy_button': '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[2]/div/div/div[1]/div[3]/div[1]/div[4]/div/div/div[1]/div/div/div/div[1]/button/div[2]'
    }

    # Функция для получения данных по XPath
    def get_element(xpath, default=None):
        try:
            element = driver.find_element(By.XPATH, xpath)
            time.sleep(1)  # Задержка перед чтением текста элемента
            return element.text.strip()
        except NoSuchElementException:
            return default  # Возвращаем значение по умолчанию, если элемент не найден

    # Собираем данные
    price = get_element(xpaths['price'])
    price = float(price.replace('₽', '').replace('\u2009', '').replace('\xa0', '').replace(' ', '')) if price else None

    card_price = get_element(xpaths['card_price'])
    card_price = float(card_price.replace('₽', '').replace('\u2009', '').replace('\xa0', '').replace(' ', '')) if card_price else None

    original_price = get_element(xpaths['original_price'])
    original_price = float(original_price.replace('₽', '').replace('\u2009', '').replace('\xa0', '').replace(' ', '')) if original_price else None

    rating = get_element(xpaths['rating'])
    try:
        rating = float(rating.split('•')[0].strip()) if rating else None
    except (ValueError, AttributeError):
        rating = None  # Устанавливаем значение None, если формат данных некорректен

    questions_count = get_element(xpaths['questions_count'])
    questions_count = int(questions_count.split()[0]) if questions_count else 0

    reviews_count = get_element(xpaths['reviews_count'])
    if reviews_count:
        # Извлекаем только числовую часть из строки
        reviews_count = ''.join(filter(str.isdigit, reviews_count))
        reviews_count = int(reviews_count) if reviews_count else 0
    else:
        reviews_count = 0

    # Проверка наличия кнопки "Купить"
    available = "Доступен" if get_element(xpaths['buy_button']) else "Нет в наличии"  # 1 - доступен, 0 - недоступен

    # Логика для "Стало дешевле"
    price_change = "Без изменений"
    if price is not None and original_price is not None:
        cursor.execute('SELECT original_price FROM products WHERE product_code = ?', (product_code,))
        previous_record = cursor.fetchone()
        if previous_record:
            previous_original_price = previous_record[0]
            if price < previous_original_price:
                price_change = "Стало дешевле"
            elif price > previous_original_price:
                price_change = "Стало дороже"

    # Вызов функции сохранения данных
    save_to_db(cursor, conn, timestamp, product_code, price, card_price, original_price, 
            price_change, rating, questions_count, reviews_count, available)

# Запись или обновление данных в БД
def save_to_db(cursor, conn, timestamp, product_code, price, card_price, original_price, 
            price_change, rating, questions_count, reviews_count, available):
    # Проверяем, существует ли запись с таким product_code
    cursor.execute('SELECT id FROM products WHERE product_code = ?', (product_code,))
    existing_record = cursor.fetchone()

    if existing_record:
        # Обновляем существующую запись
        cursor.execute('''
            UPDATE products
            SET timestamp = ?, price = ?, card_price = ?, original_price = ?, 
                price_change = ?, rating = ?, questions_count = ?, reviews_count = ?, available = ?
            WHERE product_code = ?
        ''', (timestamp, price, card_price, original_price, price_change, rating, 
            questions_count, reviews_count, available, product_code))
    else:
        # Вставляем новую запись
        cursor.execute('''
            INSERT INTO products (timestamp, product_code, price, card_price, original_price, 
                                price_change, rating, questions_count, reviews_count, available)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, product_code, price, card_price, original_price, price_change, 
            rating, questions_count, reviews_count, available))
    conn.commit()

# Основной цикл парсинга
def main():
    file_path = 'SKU_Ozon.txt'  # Путь к вашему файлу с артикулами
    articles = load_links(file_path)
    conn, cursor = init_db()

    driver = webdriver.Chrome(service=service, options=chrome_options)
    try:
        start_time = datetime.now()  # Начало измерения времени
        for article in articles:
            print(f"Парсинг артикула: {article}")
            parse_product_page(driver, article, cursor, conn)
        end_time = datetime.now()  # Конец измерения времени
        elapsed_time = end_time - start_time
        print(f"Парсинг завершен. Затрачено времени: {elapsed_time.total_seconds() / 60:.2f} минут.")
    finally:
        driver.quit()
        conn.close()

# Запуск как процесса с периодичностью (пример для Unix)
if __name__ == "__main__":
    while True:
        print("Запуск парсинга...")
        main()
        print("Ожидание следующего цикла...")

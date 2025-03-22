#!/usr/bin/env python3

import time
import mysql.connector  # Используем MariaDB
from mysql.connector import Error
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from threading import Thread  # Для параллельной обработки
import configparser  # Для чтения конфигурационного файла
import random
import tempfile  # Для создания временных директорий
import undetected_chromedriver as uc  # Импортируем undetected_chromedriver
from selenium.webdriver.support.ui import WebDriverWait  # Для явного ожидания
from selenium.webdriver.support import expected_conditions as EC  # Условия ожидания

# Настройки Selenium
chrome_options = Options()
chrome_options.add_argument("--headless")
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

# Чтение конфигурации из config.txt
def load_db_config(config_path='config.txt'):
    config = configparser.ConfigParser()
    config.read(config_path)
    return {
        'host': config.get('database', 'host'),
        'user': config.get('database', 'user'),
        'password': config.get('database', 'password'),
        'database': config.get('database', 'database')
    }

# Подключение к MariaDB
def init_db():
    try:
        db_config = load_db_config()  # Загружаем конфигурацию
        conn = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ozon_price_parser (
                id INT AUTO_INCREMENT PRIMARY KEY,
                date DATETIME,  
                timestamp BIGINT,  # UNIX-время
                product_code VARCHAR(255),
                price FLOAT,
                card_price FLOAT,
                original_price FLOAT,
                price_change VARCHAR(255),
                rating FLOAT,
                rating_change INT, 
                questions_count INT,
                reviews_count INT,
                available VARCHAR(255)
            )
        ''')
        # Удалено создание таблицы products
        conn.commit()
        return conn, cursor
    except Error as e:
        print(f"Ошибка подключения к MariaDB: {e}")
        exit(1)

# Функция для получения данных по нескольким XPath
def get_element(driver, xpaths, default=None, timeout=10):
    for xpath in xpaths:
        try:
            # Явное ожидание появления элемента
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            return element.text.strip()
        except Exception:
            continue  # Пробуем следующий XPath
    return default  # Возвращаем значение по умолчанию, если ни один XPath не сработал

# Функция парсинга данных с одной страницы
def parse_product_page(driver, article, cursor, conn):
    url = f"https://www.ozon.ru/product/{article}/"  # Формируем ссылку на основе артикула
    driver.get(url)
    time.sleep(2)  # Короткая пауза для начальной загрузки страницы

    # Артикул товара
    product_code = article

    # Текущие дата и время
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    timestamp = int(datetime.now().timestamp())

    # Пример XPath для разных вариантов отображения данных
    xpaths = {
        'price': [
            '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[2]/div/div/div[1]/div[2]/div/div[1]/div/div/div[1]/div[2]/div/div[1]/span[1]',  # Основной блок
            '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[2]/div/div/div[1]/div[3]/div/div[1]/div/div/div[1]/div[1]/button/span/div/div[1]/div/div/span',  # Блок с распродажей
        ],
        'card_price': [
            '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[2]/div/div/div[1]/div[2]/div/div[1]/div/div/div[1]/div[1]/button/span/div/div[1]/div/div/span',
            '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[2]/div/div/div[1]/div[3]/div/div[1]/div/div/div[1]/div[1]/button/span/div/div[1]/div/div/span',  # Альтернативный блок с картой
        ],
        'original_price': [
            '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[2]/div/div/div[1]/div[2]/div/div[1]/div/div/div[1]/div[2]/div/div[1]/span[2]',
            '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[2]/div/div/div[1]/div[3]/div/div[1]/div/div/div[1]/div[2]/div/div[1]/span[2]',  # Альтернативный блок с оригинальной ценой
        ],
        'rating': [
            '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[1]/div[1]/div[2]/div/div/div/div[2]/div[1]/a/div'
        ],
        'questions_count': [
            '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[1]/div[1]/div[2]/div/div/div/div[2]/div[2]/a/div'
        ],
        'reviews_count': [
            '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[1]/div[1]/div[2]/div/div/div/div[2]/div[1]/a/div'
        ],
    }

    # Собираем данные
    price = get_element(driver, xpaths['price'])
    if not price:
        print(f"Предупреждение: Цена не найдена для артикула {product_code}")
    price = float(price.replace('₽', '').replace('\u2009', '').replace('\xa0', '').replace(' ', '')) if price else None

    card_price = get_element(driver, xpaths['card_price'])
    if not card_price:
        print(f"Предупреждение: Цена с картой не найдена для артикула {product_code}")
    card_price = float(card_price.replace('₽', '').replace('\u2009', '').replace('\xa0', '').replace(' ', '')) if card_price else None

    original_price = get_element(driver, xpaths['original_price'])
    if not original_price:
        print(f"Предупреждение: Оригинальная цена не найдена для артикула {product_code}")
    original_price = float(original_price.replace('₽', '').replace('\u2009', '').replace('\xa0', '').replace(' ', '')) if original_price else None

    rating = get_element(driver, xpaths['rating'])
    if not rating:
        print(f"Предупреждение: Рейтинг не найден для артикула {product_code}")
    try:
        rating = float(rating.split('•')[0].strip()) if rating else None
    except (ValueError, AttributeError):
        rating = None

    questions_count = get_element(driver, xpaths['questions_count'])
    if not questions_count:
        print(f"Предупреждение: Количество вопросов не найдено для артикула {product_code}")
    questions_count = int(questions_count.split()[0]) if questions_count else 0

    reviews_count = get_element(driver, xpaths['reviews_count'])
    if not reviews_count:
        print(f"Предупреждение: Количество отзывов не найдено для артикула {product_code}")
    if reviews_count:
        reviews_count = reviews_count.split('•')[-1].strip()
        reviews_count = ''.join(filter(str.isdigit, reviews_count))
        reviews_count = int(reviews_count) if reviews_count else 0
    else:
        reviews_count = 0

    # Проверка наличия кнопки "Купить" на основе цены
    available = 1 if price is not None else 0

    # Логика для "Стало дешевле"
    price_change = 0
    if price is not None and original_price is not None:
        if price < original_price:
            price_change = 1
        elif price > original_price:
            price_change = 1

    # Логика для "Изменения рейтинга"
    rating_change = 0  # По умолчанию без изменений

    # Вызов функции сохранения данных
    save_to_db(cursor, conn, date, timestamp, product_code, price, card_price, original_price, 
            price_change, rating, rating_change, questions_count, reviews_count, available)

# Запись или обновление данных в БД
def save_to_db(cursor, conn, date, timestamp, product_code, price, card_price, original_price, 
            price_change, rating, rating_change, questions_count, reviews_count, available):
    # Проверяем, существует ли запись с таким product_code
    cursor.execute('SELECT id FROM ozon_price_parser WHERE product_code = %s', (product_code,))
    existing_record = cursor.fetchone()

    if existing_record:
        # Обновляем существующую запись
        cursor.execute('''
            UPDATE ozon_price_parser
            SET date = %s, timestamp = %s, price = %s, card_price = %s, original_price = %s, 
                price_change = %s, rating = %s, rating_change = %s, questions_count = %s, 
                reviews_count = %s, available = %s
            WHERE product_code = %s
        ''', (date, timestamp, price, card_price, original_price, price_change, rating, 
            rating_change, questions_count, reviews_count, available, product_code))
    else:
        # Вставляем новую запись
        cursor.execute('''
            INSERT INTO ozon_price_parser (date, timestamp, product_code, price, card_price, original_price, 
                                        price_change, rating, rating_change, questions_count, 
                                        reviews_count, available)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (date, timestamp, product_code, price, card_price, original_price, price_change, 
            rating, rating_change, questions_count, reviews_count, available))
    conn.commit()

# Функция для обработки части артикулов
def process_articles(articles):
    conn, cursor = init_db()  # Создаём подключение к базе данных для каждого потока
    temp_dir = tempfile.TemporaryDirectory()  # Создаём уникальную временную директорию для профиля браузера
    try:
        # Создаём драйвер с использованием undetected_chromedriver
        options = uc.ChromeOptions()
        options.add_argument(f"--user-data-dir={temp_dir.name}")  # Уникальная директория профиля
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")  # Отключение GPU для стабильности
        options.add_argument("--window-size=1920,1080")  # Установка размера окна
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36")
        driver = uc.Chrome(options=options)

        for article in articles:
            print(f"Парсинг артикула: {article}")
            try:
                parse_product_page(driver, article, cursor, conn)
            except Exception as e:
                print(f"Ошибка при обработке артикула {article}: {e}")
    finally:
        driver.quit()  # Закрываем драйвер после завершения работы
        temp_dir.cleanup()  # Удаляем временную директорию
        conn.close()  # Закрываем подключение к базе данных

# Основной цикл парсинга
def main():
    file_path = 'SKU_Ozon.txt'  # Путь к вашему файлу с артикулами
    articles = load_links(file_path)

    while True:  # Цикл для повторного парсинга
        print("Запуск парсинга...")
        process_articles(articles)  # Обрабатываем все артикулы в одном потоке
        print("Ожидание следующего цикла...")
        time.sleep(60)  # Задержка перед следующим кругом парсинга (например, 60 секунд)

# Запуск как процесса с периодичностью (пример для Unix)
if __name__ == "__main__":
    while True:
        main()

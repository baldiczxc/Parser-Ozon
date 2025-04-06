# Ozon Data Parser

This project is a script for automatically parsing product data from the Ozon website. The script uses Selenium for web page interaction and SQLite for data storage.

## Features

- Parsing product data by their SKUs.
- Saving data to a local SQLite database.
- Logging errors to the `errors.log` file.
- Automatically updating product data, including price, rating, review count, and availability.
- Support for periodic execution with a 1-hour interval.

## Installation

1. Ensure you have Python version 3.7 or higher installed.
2. Install dependencies:
   ```bash
   pip install selenium
   ```
3. Install the ChromeDriver compatible with your version of Google Chrome. Ensure the path to the driver is specified in the `service` variable in the code:
   ```python
   service = Service('/usr/bin/chromedriver')  # Specify the correct path
   ```

## Usage

1. Create a file named `SKU_Ozon.txt` in the project's root directory. List the product SKUs in this file, one per line.
2. Run the script:
   ```bash
   python main.py
   ```
3. The script will automatically run every x minutes. To stop it, press `Ctrl+C`.

## Database Structure

The script creates a database `ozon_data.db` with a table `products`. Table fields:

- `id` — unique record identifier.
- `timestamp` — date and time of the last record update.
- `product_code` — product SKU.
- `price` — current product price.
- `card_price` — product price with an Ozon card.
- `original_price` — original product price.
- `price_change` — price change ("Price dropped", "Price increased", "No change").
- `rating` — product rating.
- `questions_count` — number of questions about the product.
- `reviews_count` — number of product reviews.
- `available` — product availability ("Available" or "Out of stock").

## Logging

Errors are logged to the `errors.log` file in the format:
```
<date and time> - ERROR - <error description>
```

## Notes

- The script runs in headless mode (without browser display).
- Ensure the Ozon website is accessible and does not block automated requests.

---

# Парсер данных с Ozon

Этот проект представляет собой скрипт для автоматического парсинга данных о товарах с сайта Ozon. Скрипт использует Selenium для взаимодействия с веб-страницами и SQLite для хранения данных.

## Функциональность

- Парсинг данных о товарах по их артикулам.
- Сохранение данных в локальную базу данных SQLite.
- Логирование ошибок в файл `errors.log`.
- Автоматическое обновление данных о товарах, включая цену, рейтинг, количество отзывов и доступность.
- Поддержка периодического запуска с интервалом в 1 час.

## Установка

1. Убедитесь, что у вас установлен Python версии 3.7 или выше.
2. Установите зависимости:
   ```bash
   pip install selenium
   ```
3. Установите драйвер ChromeDriver, совместимый с вашей версией браузера Google Chrome. Убедитесь, что путь к драйверу указан в переменной `service` в коде:
   ```python
   service = Service('/usr/bin/chromedriver')  # Укажите правильный путь
   ```

## Использование

1. Создайте файл `SKU_Ozon.txt` в корневой директории проекта. В этом файле укажите артикулы товаров, по одному на строку.
2. Запустите скрипт:
   ```bash
   python main.py
   ```
3. Скрипт будет автоматически запускаться каждые x минут. Для остановки нажмите `Ctrl+C`.

## Структура базы данных

Скрипт создает базу данных `ozon_data.db` с таблицей `products`. Поля таблицы:

- `id` — уникальный идентификатор записи.
- `timestamp` — дата и время последнего обновления записи.
- `product_code` — артикул товара.
- `price` — текущая цена товара.
- `card_price` — цена товара по карте Ozon.
- `original_price` — оригинальная цена товара.
- `price_change` — изменение цены ("Стало дешевле", "Стало дороже", "Без изменений").
- `rating` — рейтинг товара.
- `questions_count` — количество вопросов о товаре.
- `reviews_count` — количество отзывов о товаре.
- `available` — доступность товара ("Доступен" или "Нет в наличии").

## Логирование

Ошибки записываются в файл `errors.log` в формате:
```
<дата и время> - ERROR - <описание ошибки>
```

## Примечания

- Скрипт работает в режиме headless (без отображения браузера).
- Для корректной работы убедитесь, что сайт Ozon доступен и не блокирует автоматические запросы.

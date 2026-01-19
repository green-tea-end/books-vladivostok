import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin


class BookvoedParser:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.base_url = "https://www.bookvoed.ru"
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_page(self, url, params=None):
        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception:
            return None

    def parse_book_card(self, card):
        book = {
            'title': '',
            'price': '',
            'old_price': '',
            'discount': '',
            'url': '',
            'image_url': '',
            'author': '',
            'city': 'Владивосток',
            'source': 'bookvoed.ru'
        }

        try:
            # Название и ссылка
            title_elem = card.find('a', class_='product-description__link')
            if title_elem:
                book['title'] = title_elem.text.strip()
                if title_elem.get('href'):
                    book['url'] = urljoin(self.base_url, title_elem['href'])

            # Автор
            author_elem = card.find('ul', class_='product-description__author')
            if author_elem:
                author_link = author_elem.find('a')
                if author_link:
                    book['author'] = author_link.text.strip()

            # Цены
            price_info = card.find('div', class_='price-info')
            if price_info:
                price_elem = price_info.find('span', class_='price-info__price')
                if price_elem:
                    book['price'] = self.clean_price(price_elem.text.strip())

                old_price_elem = price_info.find('span', class_='price-info__old-price')
                if old_price_elem:
                    book['old_price'] = self.clean_price(old_price_elem.text.strip())

            # Изображение
            img_elem = card.find('img')
            if img_elem and img_elem.get('src'):
                src = img_elem['src']
                if src.startswith('//'):
                    src = 'https:' + src
                book['image_url'] = src

        except Exception:
            pass

        return book

    def parse_book_details(self, book_url):
        details = {
            'author': '',
            'isbn': '',
            'publisher': '',
            'year': '',
            'genre': '',
            'description': ''
        }

        try:
            soup = self.get_page(book_url)
            if not soup:
                return details

            # Автор
            author_list = soup.find('ul', class_='product-title-author__list')
            if author_list:
                author_link = author_list.find('a')
                if author_link:
                    details['author'] = author_link.text.strip()

            # ISBN и характеристики
            characteristics_table = soup.find('table', class_='product-characteristics-full__table')
            if characteristics_table:
                rows = characteristics_table.find_all('tr', class_='product-characteristics-full__row')
                for row in rows:
                    th = row.find('th', class_='product-characteristics-full__cell-th')
                    td = row.find('td', class_='product-characteristics-full__cell-td')
                    if th and td:
                        header = th.text.strip().lower()
                        value = td.text.strip()

                        if 'isbn' in header and not details['isbn']:
                            details['isbn'] = value
                        elif 'издательство' in header:
                            publisher_link = td.find('a')
                            if publisher_link:
                                details['publisher'] = publisher_link.text.strip()
                            elif value:
                                details['publisher'] = value
                        elif 'год издания' in header:
                            details['year'] = value.split(',')[0].strip() if ',' in value else value
                        elif 'жанр' in header or 'раздел' in header and not details['genre']:
                            genre_link = td.find('a')
                            if genre_link:
                                details['genre'] = genre_link.text.strip()
                            elif value:
                                details['genre'] = value

            # ISBN в скрытых строках
            if not details['isbn']:
                hidden_rows = soup.find_all('tr', style='display: none;')
                for row in hidden_rows:
                    th = row.find('th', class_='product-characteristics-full__cell-th')
                    if th and 'ISBN' in th.text:
                        td = row.find('td', class_='product-characteristics-full__cell-td')
                        if td:
                            details['isbn'] = td.text.strip()
                            break

            # Описание
            annotation = soup.find('div', class_='product-annotation__text')
            if annotation:
                text = annotation.text.strip()
                if text:
                    details['description'] = text[:200] + '...' if len(text) > 200 else text
            else:
                full_desc = soup.find('div', class_='product-annotation-full__text')
                if full_desc:
                    text = full_desc.text.strip()
                    if text:
                        details['description'] = text[:200] + '...' if len(text) > 200 else text

        except Exception:
            pass

        return details

    def parse_catalog_page(self, page_num):
        url = f"{self.base_url}/catalog/books-18030"
        params = {
            'f[onlyAvailableInCustomerCity]': '1',
            'page': page_num
        }

        soup = self.get_page(url, params)
        if not soup:
            return []

        books = []
        product_cards = soup.find_all('div', class_='product-card')

        for card in product_cards:
            book = self.parse_book_card(card)
            if book.get('url'):
                details = self.parse_book_details(book['url'])
                book.update(details)
                books.append(book)
                time.sleep(0.5)

        return books

    def parse_all_pages(self, max_pages=18):
        all_books = []
        for page_num in range(1, max_pages + 1):
            try:
                books = self.parse_catalog_page(page_num)
                if not books:
                    break
                all_books.extend(books)
            except Exception:
                break
            time.sleep(1)
        return all_books

    def clean_price(self, price_text):
        if not price_text:
            return ''
        cleaned = re.sub(r'[^\d,]', '', price_text)
        return cleaned.replace(',', '.')

    def clean_isbn(self, isbn):
        if not isbn:
            return ''
        return ''.join(filter(str.isdigit, isbn))

    def save_to_json(self, books, filename='books_bookvoed.json'):
        try:
            for book in books:
                if book.get('isbn'):
                    book['isbn_clean'] = self.clean_isbn(book['isbn'])

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(books, f, ensure_ascii=False, indent=2)

            print(f"Всего собрано книг: {len(books)}")
            return True

        except Exception as e:
            print(f"Ошибка при сохранении: {e}")
            return False


def main():
    parser = BookvoedParser()
    books = parser.parse_all_pages(max_pages=18)

    if books:
        parser.save_to_json(books, 'books_bookvoed.json')
    else:
        print("Не удалось собрать данные о книгах.")


if __name__ == "__main__":
    main()
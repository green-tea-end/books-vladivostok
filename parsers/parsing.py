import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin


class ChitaiGorodParser:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.base_url = "https://www.chitai-gorod.ru"
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_page(self, url, params=None):
        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.exceptions.RequestException:
            return None
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
            'city': 'Владивосток',
            'source': 'chitai-gorod.ru'
        }

        try:
            title_elem = card.find('a', class_='product-card__title')
            if title_elem:
                book['title'] = title_elem.text.strip()
                if title_elem.get('href'):
                    book['url'] = urljoin(self.base_url, title_elem['href'])

            price_elem = card.find('span', class_='product-mini-card-price__price')
            if price_elem:
                book['price'] = self.clean_price(price_elem.text.strip())

            old_price_elem = card.find('span', class_='product-mini-card-price__old-price')
            if old_price_elem:
                book['old_price'] = self.clean_price(old_price_elem.text.strip())

            discount_elem = card.find('span', class_='product-mini-card-price__discount')
            if discount_elem:
                book['discount'] = discount_elem.text.strip()

            img_elem = card.find('img', class_='product-card__image')
            if img_elem and img_elem.get('src'):
                book['image_url'] = img_elem['src']
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
            author_section = soup.find('ul', class_='product-authors')
            if author_section:
                author_link = author_section.find('a')
                if author_link:
                    details['author'] = author_link.text.strip()

            # ISBN
            isbn_span = soup.find('span', itemprop='isbn')
            if isbn_span:
                details['isbn'] = isbn_span.text.strip()

            # Издательство, год, жанр
            properties_section = soup.find('ul', class_='product-properties')
            if properties_section:
                property_items = properties_section.find_all('li', class_='product-properties-item')

                for item in property_items:
                    title_span = item.find('span', class_='product-properties-item__title')
                    if title_span:
                        title_text = title_span.text.strip().lower()
                        value_span = item.find('span', class_='product-properties-item__content')
                        if value_span:
                            value_text = value_span.get_text(strip=True)

                            if 'издательство' in title_text:
                                link = value_span.find('a')
                                if link:
                                    details['publisher'] = link.text.strip()
                                elif value_text:
                                    details['publisher'] = value_text
                            elif 'год издания' in title_text:
                                details['year'] = value_text
                            elif 'жанр' in title_text and not details['genre']:
                                details['genre'] = value_text

            # Жанр из тегов
            tag_list = soup.find('ul', class_='product-tag-list')
            if tag_list:
                tags = tag_list.find_all('a', class_='product-tag')
                if tags:
                    details['genre'] = ', '.join([tag.text.strip() for tag in tags])

            # Описание
            description_elem = soup.find('article', class_='product-detail-page__detail-text')
            if description_elem:
                full_description = description_elem.get_text(strip=True, separator=' ')
                sentences = re.split(r'[.!?]', full_description)
                if sentences and sentences[0].strip():
                    details['description'] = sentences[0].strip() + '.'
                else:
                    details['description'] = full_description[:200] + '...' if len(
                        full_description) > 200 else full_description

        except Exception:
            pass

        return details

    def parse_catalog_page(self, page_num):
        url = f"{self.base_url}/catalog/books-18030"
        params = {
            'filters[onlyAvailableInCustomerCity]': '1',
            'page': page_num
        }

        soup = self.get_page(url, params)
        if not soup:
            return []

        books = []
        product_cards = soup.find_all('article', class_='product-card')

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

    def save_to_json(self, books, filename='books_vladivostok.json'):
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
    parser = ChitaiGorodParser()
    books = parser.parse_all_pages(max_pages=18)

    if books:
        parser.save_to_json(books, 'books_vladivostok.json')
    else:
        print("Не удалось собрать данные о книгах.")


if __name__ == "__main__":
    main()
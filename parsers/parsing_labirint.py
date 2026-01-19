import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin
from typing import Set


class LabirintParser:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.base_url = "https://www.labirint.ru"
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.seen_urls: Set[str] = set()

    def get_page(self, url, params=None):
        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception:
            return None

    def parse_book_details(self, book_url):
        """Парсинг детальной страницы книги"""
        details = {
            'title': '',
            'price': '',
            'old_price': '',
            'discount': '',
            'author': '',
            'isbn': '',
            'publisher': '',
            'year': '',
            'genre': '',
            'description': '',
            'url': book_url,
            'city': 'Владивосток',
            'source': 'labirint.ru',
            'image_url': ''
        }

        try:
            soup = self.get_page(book_url)
            if not soup:
                return details

            # Заголовок
            h1 = soup.find('h1', class_='_h1_5o36c_18') or soup.find('h1')
            if h1:
                title_text = h1.get_text(strip=True)
                title_text = re.split(r'[:\-–]', title_text)[0].strip()
                details['title'] = title_text

            # Цены и скидка
            price_section = soup.find('section', class_='area-price')
            if price_section:
                # Текущая цена
                for elem in price_section.find_all('div', class_='rubl'):
                    elem_classes = elem.get('class', [])
                    if 'text-bold-28-md-32' in elem_classes or 'text-bold-20' in elem_classes:
                        details['price'] = re.sub(r'[^\d]', '', elem.get_text(strip=True))
                        break

                # Старая цена
                old_price_elem = price_section.find('div', class_='_priceBase_zuu52_19')
                if old_price_elem:
                    details['old_price'] = re.sub(r'[^\d]', '', old_price_elem.get_text(strip=True))

                # Скидка
                discount_elem = price_section.find('div', class_='_discount_zuu52_25')
                if discount_elem:
                    discount_text = discount_elem.get_text(strip=True)
                    discount_match = re.search(r'([–\-]\s*\d+\s*%)', discount_text)
                    if discount_match:
                        details['discount'] = re.sub(r'\s+', '', discount_match.group(1))

                if not details['discount'] and details['price'] and details['old_price']:
                    try:
                        price = float(details['price'])
                        old_price = float(details['old_price'])
                        if old_price > 0:
                            discount_percent = int((1 - price / old_price) * 100)
                            if discount_percent > 0:
                                details['discount'] = f"-{discount_percent}%"
                    except:
                        pass

            # Характеристики
            features_section = soup.find('div', class_='_wrapper_u86in_1')
            if features_section:
                features = features_section.find_all('div', class_='_feature_mmfyx_1')

                for feature in features:
                    name_div = feature.find('div', class_='_name_mmfyx_9')
                    if not name_div:
                        continue

                    name_text = name_div.get_text(strip=True).lower()

                    # Автор
                    if 'автор' in name_text and not details['author']:
                        author_links = feature.find_all('a', href=re.compile(r'/authors/'))
                        if author_links:
                            authors = [link.get_text(strip=True) for link in author_links]
                            details['author'] = ', '.join(authors)

                    # Издательство и год
                    elif 'издательство' in name_text:
                        publisher_link = feature.find('a', href=re.compile(r'/pubhouse/'))
                        if publisher_link:
                            details['publisher'] = publisher_link.get_text(strip=True)

                        # Год
                        year_span = feature.find('span', string=re.compile(r'^\d{4}$'))
                        if year_span:
                            details['year'] = year_span.get_text(strip=True)
                        else:
                            all_text = feature.get_text()
                            year_match = re.search(r'\b(20\d{2}|19\d{2})\b', all_text)
                            if year_match:
                                details['year'] = year_match.group(1)

                    # Жанр
                    elif 'жанр' in name_text and not details['genre']:
                        genre_links = feature.find_all('a', href=re.compile(r'/genres/'))
                        if genre_links:
                            genres = [link.get_text(strip=True) for link in genre_links]
                            details['genre'] = ', '.join(genres)

            # ISBN
            meta_isbn = soup.find('meta', itemprop='isbn')
            if meta_isbn:
                details['isbn'] = meta_isbn.get('content', '').strip()

            # Описание
            desc_div = soup.find('div', id='annotation') or \
                       soup.find('div', class_=lambda x: x and 'annotation' in str(x).lower())

            if desc_div:
                text = desc_div.get_text(strip=True, separator=' ')
                if text.lower().startswith('аннотация'):
                    text = text[9:].strip()
                if text:
                    details['description'] = text[:300]

            # Изображение
            img = soup.find('img', class_='_image_1qke2_7')
            if img and img.get('src'):
                src = img['src']
                if src.startswith('//'):
                    src = 'https:' + src
                details['image_url'] = src

        except Exception:
            pass

        return details

    def parse_book_card(self, container):
        """Парсинг карточки книги в каталоге"""
        book = {'url': ''}

        for link in container.find_all('a', href=True):
            href = link['href']
            if '/books/' in href or '/product/' in href:
                book_url = urljoin(self.base_url, href)

                if book_url in self.seen_urls:
                    return None

                self.seen_urls.add(book_url)
                book['url'] = book_url
                return book

        return None

    def parse_catalog_page(self, page_num):
        """Парсинг страницы каталога"""
        url = f"{self.base_url}/books/"
        params = {'available': '1', 'page': page_num}

        soup = self.get_page(url, params)
        if not soup:
            return []

        books = []
        containers = soup.find_all('div', class_='_product_wduds_1')

        if not containers:
            containers = soup.find_all('div', class_=lambda x: x and 'product' in str(x).lower())

        for container in containers:
            book_basic = self.parse_book_card(container)

            if book_basic and book_basic.get('url'):
                details = self.parse_book_details(book_basic['url'])
                books.append(details)
                time.sleep(0.3)

        return books

    def parse_all_pages(self, max_pages=18):
        """Парсинг всех страниц"""
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

    def clean_isbn(self, isbn):
        if not isbn:
            return ''
        return ''.join(filter(str.isdigit, isbn))

    def save_to_json(self, books, filename='books_labirint.json'):
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
    parser = LabirintParser()
    books = parser.parse_all_pages(max_pages=18)

    if books:
        parser.save_to_json(books, 'books_labirint.json')
    else:
        print("Не удалось собрать данные о книгах.")


if __name__ == "__main__":
    main()
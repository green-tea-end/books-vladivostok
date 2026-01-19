import json
import mysql.connector
from mysql.connector import Error
import re
import getpass


def get_isbn_clean(book):
    isbn_clean = book.get('isbn_clean')
    if isbn_clean:
        return str(isbn_clean).strip()

    isbn = book.get('isbn')
    if isbn:
        return ''.join(filter(str.isdigit, str(isbn)))[:20]

    return None


def normalize_for_comparison(text):
    if not text:
        return ''

    text = text.lower().strip()
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def import_books():
    password = getpass.getpass("Введите пароль MySQL: ")

    try:
        with open('../data/all_books_raw.json', 'r', encoding='utf-8') as f:
            books = json.load(f)
    except FileNotFoundError:
        return

    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password=password,
            database='books_db',
            charset='utf8mb4'
        )
        cursor = conn.cursor(dictionary=True)
    except Error:
        return

    stats = {
        'total': 0,
        'new_books': 0,
        'duplicates': 0,
        'offers': 0,
        'used_isbn_clean': 0,
        'used_isbn_raw': 0
    }

    try:
        for book in books:
            stats['total'] += 1

            isbn_clean = get_isbn_clean(book)
            title = book.get('title', '').strip()
            author = book.get('author', '').strip()

            if book.get('isbn_clean'):
                stats['used_isbn_clean'] += 1
            elif book.get('isbn'):
                stats['used_isbn_raw'] += 1

            product_id = None

            if isbn_clean:
                cursor.execute(
                    "SELECT id FROM products WHERE isbn_clean = %s",
                    (isbn_clean,)
                )
                result = cursor.fetchone()
                if result:
                    product_id = result['id']

            if not product_id and title and author:
                norm_title = normalize_for_comparison(title)
                norm_author = normalize_for_comparison(author)

                if norm_title and norm_author:
                    cursor.execute("""
                        SELECT id, canonical_name, author 
                        FROM products 
                        WHERE 
                            (LOWER(REPLACE(canonical_name, ' ', '')) LIKE CONCAT('%', REPLACE(%s, ' ', ''), '%')
                            OR LOWER(canonical_name) LIKE CONCAT('%', %s, '%'))
                        LIMIT 5
                    """, (norm_title, norm_title))

                    candidates = cursor.fetchall()

                    for candidate in candidates:
                        cand_title_norm = normalize_for_comparison(candidate['canonical_name'])
                        cand_author_norm = normalize_for_comparison(candidate['author'])

                        if (norm_title in cand_title_norm or cand_title_norm in norm_title) and \
                                (norm_author in cand_author_norm or cand_author_norm in norm_author):
                            product_id = candidate['id']
                            break

            if not product_id:
                year_str = book.get('year', '')
                year_int = None
                if year_str:
                    year_match = re.search(r'\b(20\d{2}|19\d{2})\b', str(year_str))
                    if year_match:
                        year_int = int(year_match.group(1))

                cursor.execute("""
                    INSERT INTO products 
                    (canonical_name, author, isbn_clean, publisher, year, genre, description, image_url)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    title,
                    author,
                    isbn_clean,
                    book.get('publisher', ''),
                    year_int,
                    book.get('genre', ''),
                    book.get('description', ''),
                    book.get('image_url', '')
                ))
                product_id = cursor.lastrowid
                stats['new_books'] += 1
            else:
                stats['duplicates'] += 1

            try:
                price = float(book['price']) if book.get('price') else None
                old_price = float(book['old_price']) if book.get('old_price') else None
            except (ValueError, TypeError):
                price = old_price = None

            cursor.execute("""
                INSERT INTO offers 
                (product_id, website_name, price, old_price, discount, url, city)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                product_id,
                book.get('source', 'unknown'),
                price,
                old_price,
                book.get('discount', ''),
                book.get('url', ''),
                book.get('city', 'Владивосток')
            ))
            stats['offers'] += 1

        conn.commit()

    except Error:
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    import_books()
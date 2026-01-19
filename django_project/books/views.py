from django.shortcuts import render
from django.core.paginator import Paginator
from .db_connection import execute_query


def index(request):
    # Получаем статистику
    stats = execute_query("""
        SELECT 
            (SELECT COUNT(*) FROM products) as total_books,
            (SELECT COUNT(*) FROM offers) as total_offers
    """, fetch_one=True)

    # Последние книги
    recent_books = execute_query("""
        SELECT p.*, MIN(o.price) as min_price, COUNT(o.id) as offers_count
        FROM products p
        LEFT JOIN offers o ON p.id = o.product_id
        GROUP BY p.id
        ORDER BY p.created_at DESC
        LIMIT 10
    """)

    return render(request, 'index.html', {
        'total_books': stats['total_books'] if stats else 0,
        'total_offers': stats['total_offers'] if stats else 0,
        'recent_books': recent_books or [],
    })


def search(request):
    """Поиск книг"""
    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    per_page = 20

    # SQL запрос
    if query:
        sql = """
            SELECT p.*, MIN(o.price) as min_price, COUNT(o.id) as offers_count
            FROM products p
            LEFT JOIN offers o ON p.id = o.product_id
            WHERE p.canonical_name LIKE %s OR p.author LIKE %s
            GROUP BY p.id
            ORDER BY p.canonical_name
        """
        params = [f'%{query}%', f'%{query}%']
        count_sql = """
            SELECT COUNT(*) as total FROM products 
            WHERE canonical_name LIKE %s OR author LIKE %s
        """
    else:
        sql = """
            SELECT p.*, MIN(o.price) as min_price, COUNT(o.id) as offers_count
            FROM products p
            LEFT JOIN offers o ON p.id = o.product_id
            GROUP BY p.id
            ORDER BY p.created_at DESC
        """
        params = []
        count_sql = "SELECT COUNT(*) as total FROM products"

    # Общее количество
    total_result = execute_query(count_sql, params, fetch_one=True)
    total = total_result['total'] if total_result else 0

    # Пагинация
    offset = (page - 1) * per_page
    sql_paged = f"{sql} LIMIT {per_page} OFFSET {offset}"

    books = execute_query(sql_paged, params) or []

    # Пагинатор
    paginator = Paginator(range(total), per_page)
    page_obj = paginator.get_page(page)

    return render(request, 'search.html', {
        'books': books,
        'page_obj': page_obj,
        'query': query,
        'total': total,
    })


def book_detail(request, book_id):
    """Детальная страница книги"""
    book = execute_query("SELECT * FROM products WHERE id = %s", [book_id], fetch_one=True)

    if not book:
        return render(request, 'book.html', {'book': None, 'offers': []})

    offers = execute_query("""
        SELECT * FROM offers 
        WHERE product_id = %s 
        ORDER BY price
    """, [book_id]) or []

    return render(request, 'book.html', {
        'book': book,
        'offers': offers,
    })
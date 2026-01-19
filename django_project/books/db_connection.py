import mysql.connector


def get_db_config():
    return {
        'host': 'localhost',
        'user': 'root',
        'password': 'S!ka1625',
        'database': 'books_db',
        'charset': 'utf8mb4'
    }


def execute_query(query, params=None, fetch_one=False):
    try:
        conn = mysql.connector.connect(**get_db_config())
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())

        if fetch_one:
            result = cursor.fetchone()
        else:
            result = cursor.fetchall()

        cursor.close()
        conn.close()
        return result

    except Exception as e:
        print(f"Ошибка БД: {e}")
        return None
import json
import os

def merge_json_files():
    # Список файлов для объединения
    files_to_merge = [
        'books_vladivostok.json',
        'books_labirint.json',
        'books_bookvoed.json'
    ]

    all_books = []  # Общий список для всех книг

    # Чтение и объединение данных из каждого файла
    for filename in files_to_merge:
        if not os.path.exists(filename):
            print(f"Файл не найден: {filename}. Пропускаем.")
            continue

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_books.extend(data)
                print(f"Загружено {len(data)} записей из {filename}")
        except json.JSONDecodeError:
            print(f"Ошибка: файл {filename} содержит некорректный JSON.")
        except Exception as e:
            print(f"Ошибка при чтении файла {filename}: {e}")

    # Сохранение объединенных данных
    if all_books:
        try:
            output_filename = '../data/all_books_raw.json'
            with open(output_filename, 'w', encoding='utf-8') as out_file:
                json.dump(all_books, out_file, ensure_ascii=False, indent=2)
            print(f"\nУспешно. Объединено {len(all_books)} записей.")
            print(f"Результат сохранен в {output_filename}")
        except Exception as e:
            print(f"Ошибка при сохранении файла: {e}")
    else:
        print("Не удалось загрузить ни одной записи.")

# Точка входа
if __name__ == "__main__":
    merge_json_files()
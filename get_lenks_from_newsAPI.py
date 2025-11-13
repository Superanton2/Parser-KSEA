from serpapi import GoogleSearch
import csv

def serpapi_search(q, api_key):
    # Параметри для пошукового запиту
    params = {
        "tbm": "nws",  # tbm=nws означає пошук у розділі "Новини"
        "q": q,  # Пошуковий запит
        "num": "100",  # Максимальна кількість результатів
        "api_key": api_key,
        "gl": "uk", # пошук по країнам
    }

    # Виконуємо запит до SerpApi
    search = GoogleSearch(params)
    results_dict = search.get_dict()

    return results_dict

def write_to_csv(results_dict, writer):
    # Перевіряємо, чи є в результатах блок 'news_results'
    if 'news_results' in results_dict:

        # Якщо є, проходимо по кожній знайденій новині
        for news_item in results_dict['news_results']:
            # Записуємо рядок у CSV
            writer.writerow({
                'Людина': person,
                'Заголовок': news_item.get('title'),
                'Дата': news_item.get('date'),
                'Джерело': news_item.get('source'),
                'Посилання': news_item.get('link')
            })
        print(f"✅ Знайдено {len(results_dict['news_results'])} новин.")

    else:
        # Якщо результатів немає, записуємо про це в файл
        writer.writerow({
            'Людина': person,
            'Заголовок': '❌ Нічого не знайдено',
            'Дата': '',
            'Посилання': ''
        })
        print("❌ Новин не знайдено.")



def get_lenks_from_newsAPI(SEARCH_QUERY, SERP_API_KEY):
    with open("links_results.csv", 'w', newline='', encoding='utf-8') as csvfile:
        # Створюємо "записувач" і визначаємо назви колонок
        fieldnames = ['Людина', 'Заголовок', 'Дата', 'Джерело','Посилання']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Записуємо заголовки в файл
        writer.writeheader()


        print("Searching...")
        # Проходимося по кожній людині зі списку
        for person in SEARCH_QUERY:

            results_dict = serpapi_search(person ,SERP_API_KEY)



    print(f"\n🎉 Вся робота завершена! Результати збережено у файл 'links_results.csv'")
    # Відкриваємо CSV-файл для запису ОДИН РАЗ на початку
    # newline='' - це стандартна рекомендація, щоб уникнути порожніх рядків


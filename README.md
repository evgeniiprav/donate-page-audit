Репозиторий donate-page-audit.

Раз в день GitHub Actions проверяет страницу для сбора донатов по адресу из audit.yml и складывает отчёты в reports/audit.

Что проверяется:

Наличие кнопки доната по ключевому слову.
Наличие ссылок на DonationAlerts, Boosty, Telegram.
Наличие реквизитов и политики конфиденциальности.
Отсутствие текста про ошибку на странице.
Код ответа 200.

Отчёты:

reports/audit/audit_ГГГГ-ММ-ДД.json — полный отчёт в машинном виде.
reports/audit/audit_ГГГГ-ММ-ДД.txt — человекочитаемая сводка.
reports/audit/last_status.json — последний статус одной строкой.

Настройка:

В audit.yml замени url на свою страницу и при желании правь список проверок.
В Settings → Actions → General включи Read and write permissions, иначе push из workflow не пройдёт.
Запустить вручную можно во вкладке Actions, workflow Audit donate page, кнопка Run workflow.
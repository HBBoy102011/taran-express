# -*- coding: utf-8 -*-
"""Электронная таблица тест-кейсов: 16_Тест-кейсы.xlsx."""
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from assign_data import AUTHOR, BUGS, CHECKS_TOTAL, DATE, F06, GROUP, TEST_CASES

NAVY = "1F365D"
LIGHT = "DCE6F1"
GREEN = "E2EFDA"
YELLOW = "FFF2CC"
RED = "FCE4E4"
GREY = "F2F2F2"
THIN = Side(style="thin", color="B4B4B4")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def _header(ws, row, headers, widths):
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=i, value=h)
        c.font = Font(name="Times New Roman", size=11, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=NAVY)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDER
        ws.column_dimensions[get_column_letter(i)].width = widths[i - 1]
    ws.row_dimensions[row].height = 34


def _cell(ws, row, col, value, fill=None, bold=False, center=False):
    c = ws.cell(row=row, column=col, value=value)
    c.font = Font(name="Times New Roman", size=10, bold=bold)
    c.alignment = Alignment(
        horizontal="center" if center else "left",
        vertical="top", wrap_text=True)
    c.border = BORDER
    if fill:
        c.fill = PatternFill("solid", fgColor=fill)
    return c


def _title(ws, text, subtitle):
    ws.merge_cells("A1:H1")
    c = ws["A1"]
    c.value = text
    c.font = Font(name="Times New Roman", size=18, bold=True, color=NAVY)
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 34

    ws.merge_cells("A2:H2")
    c = ws["A2"]
    c.value = subtitle
    c.font = Font(name="Times New Roman", size=11, italic=True, color="444A55")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 24


def build():
    wb = Workbook()

    # ---------------------------------------------------------------- сводка
    ws = wb.active
    ws.title = "Сводка"
    _title(ws, "ТЕСТ-КЕЙСЫ · «ТАРАН-ЭКСПРЕСС» 3.2",
           "Приложение к плану тестирования (документ 15)")
    info = [
        ("Проект", "«ТАРАН-ЭКСПРЕСС» — кликер-аркада на Python/Pygame"),
        ("Версия", "3.2"),
        ("Автор", AUTHOR),
        ("Группа", GROUP),
        ("Дата", DATE),
        ("Всего тест-кейсов", len(TEST_CASES)),
        ("Автоматических", sum(1 for t in TEST_CASES if t[2] == "авто")),
        ("Ручных", sum(1 for t in TEST_CASES if t[2] == "ручной")),
        ("Пройдено", sum(1 for t in TEST_CASES if t[6] == "пройден")),
        ("Не проведено", sum(1 for t in TEST_CASES if t[6] == "не проведён")),
        ("Заблокировано", sum(1 for t in TEST_CASES if t[6] == "заблокирован")),
        ("Автоматических проверок в коде", CHECKS_TOTAL),
    ]
    r = 4
    for k, v in info:
        a = ws.cell(row=r, column=1, value=k)
        a.font = Font(name="Times New Roman", size=11, bold=True)
        a.fill = PatternFill("solid", fgColor=LIGHT)
        a.border = BORDER
        a.alignment = Alignment(vertical="center")
        b = ws.cell(row=r, column=2, value=v)
        b.font = Font(name="Times New Roman", size=11)
        b.border = BORDER
        b.alignment = Alignment(vertical="center", wrap_text=True)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=5)
        r += 1

    r += 1
    ws.cell(row=r, column=1, value="Статусы").font = Font(
        name="Times New Roman", size=12, bold=True, color=NAVY)
    r += 1
    _header(ws, r, ["Статус", "Количество", "Доля", "", "", "", "", ""],
            [22, 14, 12, 12, 12, 12, 12, 12])
    ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=4)
    r += 1
    for label, count in (("пройден", sum(1 for t in TEST_CASES if t[6] == "пройден")),
                         ("не проведён", sum(1 for t in TEST_CASES if t[6] == "не проведён")),
                         ("заблокирован", sum(1 for t in TEST_CASES if t[6] == "заблокирован"))):
        _cell(ws, r, 1, label, GREEN if label == "пройден" else (YELLOW if label == "не проведён" else RED))
        _cell(ws, r, 2, count, center=True)
        _cell(ws, r, 3, f"{count / len(TEST_CASES) * 100:.0f}%", center=True)
        r += 1

    r += 1
    ws.cell(row=r, column=1, value="Легенда").font = Font(
        name="Times New Roman", size=12, bold=True, color=NAVY)
    r += 1
    for text, fill in (
        ("Пройден — проверка выполнена, результат совпал с ожидаемым", GREEN),
        ("Не проведён — проверка запланирована, но ещё не выполнена", YELLOW),
        ("Заблокирован — проверка невозможна по внешней причине", RED),
    ):
        c = ws.cell(row=r, column=1, value=text)
        c.font = Font(name="Times New Roman", size=10)
        c.fill = PatternFill("solid", fgColor=fill)
        c.border = BORDER
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
        r += 1
    ws.column_dimensions["A"].width = 22

    # ------------------------------------------------------------ тест-кейсы
    ws = wb.create_sheet("Тест-кейсы")
    _title(ws, "ТЕСТ-КЕЙСЫ", "30 проверок: предусловия, шаги и ожидаемый результат")
    headers = ["ID", "Проверка", "Тип", "Предусловие", "Шаги",
               "Ожидаемый результат", "Статус", "Примечание"]
    widths = [8, 34, 9, 30, 34, 36, 13, 26]
    _header(ws, 4, headers, widths)
    for i, tc in enumerate(TEST_CASES, 5):
        fill = { "пройден": GREEN, "не проведён": YELLOW,
                 "заблокирован": RED }.get(tc[6])
        for j, val in enumerate(tc, 1):
            _cell(ws, i, j, val, fill=fill if j == 7 else None,
                  bold=(j == 1), center=(j in (1, 3, 7)))
        ws.row_dimensions[i].height = 58
    ws.freeze_panes = "A5"
    ws.auto_filter.ref = f"A4:H{4 + len(TEST_CASES)}"

    # --------------------------------------------------------------- ошибки
    ws = wb.create_sheet("Ошибки")
    _title(ws, "РЕЕСТР ДЕФЕКТОВ", "12 записей: 11 закрыто, 1 открыт (BR-12)")
    headers = ["ID", "Дефект", "Категория", "Severity", "Версия", "Статус",
               "Причина и исправление", "Проверка"]
    widths = [8, 34, 18, 11, 9, 12, 52, 38]
    _header(ws, 4, headers, widths)
    for i, b in enumerate(BUGS, 5):
        vals = [b["id"], b["title"], b["cat"], b["sev"], b["ver"], b["status"],
                b["cause"], b["retest"]]
        fill = GREEN if b["status"] == "закрыт" else RED
        for j, val in enumerate(vals, 1):
            _cell(ws, i, j, val, fill=fill if j == 6 else None,
                  bold=(j == 1), center=(j in (1, 4, 5, 6)))
        ws.row_dimensions[i].height = 68
    ws.freeze_panes = "A5"

    # --------------------------------------------------------------- среда
    ws = wb.create_sheet("Среда")
    _title(ws, "ТЕСТОВОЕ ОКРУЖЕНИЕ", "Фактическая конфигурация, на которой получены результаты")
    headers = ["Компонент", "Значение", "Примечание", "", "", "", "", ""]
    _header(ws, 4, headers, [26, 42, 48, 12, 12, 12, 12, 12])
    env = [
        ("ОС", "Windows 11", "основная среда разработки"),
        ("Python", "3.14.5", "64-bit"),
        ("pygame", "pygame-ce 2.5.8", "SDL 2.32.10"),
        ("Разрешение", "1280×720 / 1920×1080", "окно и полный экран"),
        ("Сейв", "save.json в корне проекта", "копия перед ручным прогоном"),
        ("Headless", "SDL dummy", "мета-тесты и профиль"),
        ("Звук", "18 WAV + 5 OGG", "микшер 22050 Гц, 24 канала"),
        ("Заставка", "45 кадров", "intro_frames/"),
    ]
    r = 5
    for a, b, c in env:
        _cell(ws, r, 1, a, fill=LIGHT, bold=True)
        _cell(ws, r, 2, b)
        _cell(ws, r, 3, c)
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=6)
        r += 1

    # ------------------------------------------------------------- покрытие
    ws = wb.create_sheet("Покрытие")
    _title(ws, "МАТРИЦА ПОКРЫТИЯ", "Связь групп требований с тест-кейсами")
    headers = ["Группа требований", "Тест-кейсы", "Результат", "", "", "", "", ""]
    _header(ws, 4, headers, [42, 30, 30, 12, 12, 12, 12, 12])
    cover = [
        ("FR-01 — FR-05: толчок, типы, поезд, награда, серия", "TC-01 — TC-06", "пройдено"),
        ("FR-06 — FR-08: магазин, Shift, расходники", "TC-08 — TC-11", "пройдено"),
        ("FR-09 — FR-11: станции и боссы", "TC-20, TC-22, TC-23", "пройдено"),
        ("FR-12 — FR-14: хардкор и перерождение", "TC-12, TC-17, TC-23", "пройдено"),
        ("FR-15 — FR-20: дерево, реликвии, контракты", "TC-13 — TC-18", "пройдено"),
        ("FR-21 — FR-24: офлайн, сохранения", "TC-18, TC-19", "пройдено"),
        ("FR-25 — FR-30: сборки, пауза, заставка, скины", "TC-21, TC-23", "частично"),
        ("Мобильные сборки", "TC-24 — TC-27", "не проведено"),
        ("Производительность", "TC-28", "не проведено"),
        ("Юзабилити", "TC-29", "не проведено"),
        ("Публикация в Google Play", "TC-30", "заблокировано"),
    ]
    r = 5
    for a, b, c in cover:
        fill = GREEN if c == "пройдено" else (YELLOW if c in ("частично", "не проведено") else RED)
        _cell(ws, r, 1, a)
        _cell(ws, r, 2, b)
        _cell(ws, r, 3, c, fill=fill, center=True)
        r += 1

    for sheet in wb.worksheets:
        sheet.sheet_view.showGridLines = False
        sheet.page_setup.orientation = "landscape"
        sheet.page_setup.fitToWidth = 1
        sheet.sheet_properties.pageSetUpPr.fitToPage = True

    path = os.path.join(F06, "16_Тест-кейсы.xlsx")
    os.makedirs(F06, exist_ok=True)
    wb.save(path)
    return path


if __name__ == "__main__":
    print("OK", build())

-- ============================================================================
--  «ТАРАН-ЭКСПРЕСС» · схема базы данных (SQLite 3)
--
--  Игра хранит прогресс в save.json; эта схема — его нормализованная
--  реляционная модель плюс справочники контента из taran/config.py
--  и progression.py. 22 таблицы, версия схемы меты — 4.
--
--  Запуск:  sqlite3 taran.db < Схема_БД.sql
-- ============================================================================
PRAGMA foreign_keys = ON;

-- чистый пересоздаваемый набор (дочерние таблицы удаляются первыми)
DROP TABLE IF EXISTS save_notices;
DROP TABLE IF EXISTS save_achievements;
DROP TABLE IF EXISTS save_contracts;
DROP TABLE IF EXISTS save_relic_choices;
DROP TABLE IF EXISTS save_relics;
DROP TABLE IF EXISTS save_meta_tree;
DROP TABLE IF EXISTS save_meta;
DROP TABLE IF EXISTS save_stats;
DROP TABLE IF EXISTS save_skins;
DROP TABLE IF EXISTS save_items;
DROP TABLE IF EXISTS save_upgrades;
DROP TABLE IF EXISTS saves;
DROP TABLE IF EXISTS achievements;
DROP TABLE IF EXISTS contract_kinds;
DROP TABLE IF EXISTS relics;
DROP TABLE IF EXISTS meta_upgrades;
DROP TABLE IF EXISTS run_mods;
DROP TABLE IF EXISTS skins;
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS upgrades;
DROP TABLE IF EXISTS bosses;
DROP TABLE IF EXISTS themes;

-- ----------------------------------------------------------------------------
--  Справочники рейса
-- ----------------------------------------------------------------------------
CREATE TABLE themes (
    theme_id        INTEGER PRIMARY KEY,              -- индекс локации 0..19
    name            TEXT    NOT NULL,
    kills_required  INTEGER NOT NULL DEFAULT 0 CHECK (kills_required >= 0),
    kind            TEXT    NOT NULL,                 -- day / night / neon / ...
    light           REAL    NOT NULL DEFAULT 0 CHECK (light BETWEEN 0 AND 1)
);

CREATE TABLE bosses (
    boss_id     INTEGER PRIMARY KEY,
    theme_id    INTEGER NOT NULL REFERENCES themes(theme_id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,
    hp          INTEGER NOT NULL CHECK (hp > 0),
    speed       REAL    NOT NULL CHECK (speed > 0),
    time_limit  REAL    NOT NULL CHECK (time_limit > 0),   -- секунды на бой
    flags       TEXT    NOT NULL DEFAULT ''               -- поведения через запятую
);

CREATE TABLE upgrades (
    upgrade_key TEXT    PRIMARY KEY,                  -- power, income, flow, ...
    tab         INTEGER NOT NULL CHECK (tab BETWEEN 0 AND 2),
    req_level   INTEGER NOT NULL DEFAULT 0 CHECK (req_level >= 0),
    name        TEXT    NOT NULL,
    base_cost   INTEGER NOT NULL CHECK (base_cost > 0),
    growth      REAL    NOT NULL CHECK (growth >= 1),  -- множитель цены
    max_level   INTEGER NOT NULL CHECK (max_level > 0)
);

CREATE TABLE items (
    item_key      TEXT    PRIMARY KEY,
    name          TEXT    NOT NULL,
    duration_sec  INTEGER NOT NULL DEFAULT 0 CHECK (duration_sec >= 0),
    price         INTEGER NOT NULL CHECK (price > 0),
    descr         TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE skins (
    skin_id  INTEGER PRIMARY KEY,                     -- 0 — «Классика»
    name     TEXT    NOT NULL,
    palette  TEXT    NOT NULL DEFAULT '{}'            -- цвета в JSON
);

-- ----------------------------------------------------------------------------
--  Сохранение игрока
-- ----------------------------------------------------------------------------
CREATE TABLE saves (
    save_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    money       INTEGER NOT NULL DEFAULT 0 CHECK (money >= 0),    -- баланс
    earned      INTEGER NOT NULL DEFAULT 0 CHECK (earned >= 0),   -- доход за всё время
    kills       INTEGER NOT NULL DEFAULT 0 CHECK (kills >= 0),    -- поездки (толчки)
    theme_id    INTEGER NOT NULL REFERENCES themes(theme_id),     -- текущая станция
    won         INTEGER NOT NULL DEFAULT 0 CHECK (won IN (0, 1)),
    muted       INTEGER NOT NULL DEFAULT 0 CHECK (muted IN (0, 1)),
    created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    updated_at  INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE save_upgrades (
    save_id     INTEGER NOT NULL REFERENCES saves(save_id) ON DELETE CASCADE,
    upgrade_key TEXT    NOT NULL REFERENCES upgrades(upgrade_key),
    level       INTEGER NOT NULL DEFAULT 0 CHECK (level >= 0),
    PRIMARY KEY (save_id, upgrade_key)
);

CREATE TABLE save_items (
    save_id  INTEGER NOT NULL REFERENCES saves(save_id) ON DELETE CASCADE,
    item_key TEXT    NOT NULL REFERENCES items(item_key),
    count    INTEGER NOT NULL DEFAULT 0 CHECK (count >= 0),
    PRIMARY KEY (save_id, item_key)
);

CREATE TABLE save_skins (
    save_id     INTEGER NOT NULL REFERENCES saves(save_id) ON DELETE CASCADE,
    skin_id     INTEGER NOT NULL REFERENCES skins(skin_id),
    unlocked_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    PRIMARY KEY (save_id, skin_id)
);

CREATE TABLE save_stats (
    save_id        INTEGER PRIMARY KEY REFERENCES saves(save_id) ON DELETE CASCADE,
    pushes         INTEGER NOT NULL DEFAULT 0 CHECK (pushes >= 0),
    bosses         INTEGER NOT NULL DEFAULT 0 CHECK (bosses >= 0),
    coins          INTEGER NOT NULL DEFAULT 0 CHECK (coins >= 0),
    stations       INTEGER NOT NULL DEFAULT 0 CHECK (stations >= 0),
    contracts_done INTEGER NOT NULL DEFAULT 0 CHECK (contracts_done >= 0),
    max_combo      INTEGER NOT NULL DEFAULT 0 CHECK (max_combo >= 0),
    best_hard_sec  REAL    NOT NULL DEFAULT 0 CHECK (best_hard_sec >= 0)
);

CREATE TABLE save_notices (
    notice_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    save_id    INTEGER NOT NULL REFERENCES saves(save_id) ON DELETE CASCADE,
    text       TEXT    NOT NULL,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

-- ----------------------------------------------------------------------------
--  Мета-прогрессия
-- ----------------------------------------------------------------------------
CREATE TABLE save_meta (
    save_id         INTEGER PRIMARY KEY REFERENCES saves(save_id) ON DELETE CASCADE,
    version         INTEGER NOT NULL DEFAULT 4,        -- meta.v
    reborn          INTEGER NOT NULL DEFAULT 0 CHECK (reborn >= 0),
    bp              INTEGER NOT NULL DEFAULT 0 CHECK (bp >= 0),   -- чертежи
    lifetime_earned INTEGER NOT NULL DEFAULT 0 CHECK (lifetime_earned >= 0),
    best_station    INTEGER NOT NULL DEFAULT 0 CHECK (best_station BETWEEN 0 AND 20),
    epoch           INTEGER NOT NULL DEFAULT 1 CHECK (epoch >= 1),
    mod_key         TEXT    NOT NULL DEFAULT 'calm' REFERENCES run_mods(mod_key),
    run_bosses      INTEGER NOT NULL DEFAULT 0 CHECK (run_bosses >= 0),
    runs            INTEGER NOT NULL DEFAULT 0 CHECK (runs >= 0),
    income_rate     REAL    NOT NULL DEFAULT 0 CHECK (income_rate >= 0),
    last_seen       INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    offline_gain    REAL    NOT NULL DEFAULT 0 CHECK (offline_gain >= 0),
    offline_sec     REAL    NOT NULL DEFAULT 0 CHECK (offline_sec >= 0),
    play_time       REAL    NOT NULL DEFAULT 0 CHECK (play_time >= 0)
);

CREATE TABLE save_meta_tree (
    save_id  INTEGER NOT NULL REFERENCES saves(save_id) ON DELETE CASCADE,
    meta_key TEXT    NOT NULL REFERENCES meta_upgrades(meta_key),
    level    INTEGER NOT NULL DEFAULT 0 CHECK (level >= 0),
    PRIMARY KEY (save_id, meta_key)
);

CREATE TABLE save_relics (
    save_id   INTEGER NOT NULL REFERENCES saves(save_id) ON DELETE CASCADE,
    relic_key TEXT    NOT NULL REFERENCES relics(relic_key),
    level     INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1),
    PRIMARY KEY (save_id, relic_key)
);

CREATE TABLE save_relic_choices (
    save_id    INTEGER NOT NULL REFERENCES saves(save_id) ON DELETE CASCADE,
    relic_key  TEXT    NOT NULL REFERENCES relics(relic_key),
    offered_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    PRIMARY KEY (save_id, relic_key)
);

CREATE TABLE save_contracts (
    contract_id INTEGER PRIMARY KEY AUTOINCREMENT,
    save_id     INTEGER NOT NULL REFERENCES saves(save_id) ON DELETE CASCADE,
    kind_key    TEXT    NOT NULL REFERENCES contract_kinds(kind_key),
    slot        INTEGER NOT NULL CHECK (slot BETWEEN 0 AND 2),   -- 3 слота
    target      INTEGER NOT NULL CHECK (target > 0),
    progress    INTEGER NOT NULL DEFAULT 0 CHECK (progress >= 0),
    reward_bp   INTEGER NOT NULL DEFAULT 0 CHECK (reward_bp >= 0),
    done        INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1))
);

CREATE TABLE save_achievements (
    save_id         INTEGER NOT NULL REFERENCES saves(save_id) ON DELETE CASCADE,
    achievement_key TEXT    NOT NULL REFERENCES achievements(achievement_key),
    unlocked_at     INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    PRIMARY KEY (save_id, achievement_key)
);

-- ----------------------------------------------------------------------------
--  Справочники меты
-- ----------------------------------------------------------------------------
CREATE TABLE run_mods (
    mod_key     TEXT    PRIMARY KEY,
    name        TEXT    NOT NULL,
    descr       TEXT    NOT NULL DEFAULT '',
    income_mult REAL    NOT NULL DEFAULT 1 CHECK (income_mult > 0),
    boss_mult   REAL    NOT NULL DEFAULT 1 CHECK (boss_mult > 0),
    flow_mult   REAL    NOT NULL DEFAULT 1 CHECK (flow_mult > 0)
);

CREATE TABLE meta_upgrades (
    meta_key  TEXT    PRIMARY KEY,
    branch    INTEGER NOT NULL CHECK (branch BETWEEN 0 AND 2),   -- тяга/броня/логистика
    name      TEXT    NOT NULL,
    descr     TEXT    NOT NULL DEFAULT '',
    max_level INTEGER NOT NULL CHECK (max_level > 0),
    base_cost INTEGER NOT NULL CHECK (base_cost > 0),
    growth    REAL    NOT NULL CHECK (growth >= 1),
    req_level INTEGER NOT NULL DEFAULT 0 CHECK (req_level >= 0)
);

CREATE TABLE relics (
    relic_key TEXT    PRIMARY KEY,
    name      TEXT    NOT NULL,
    rarity    INTEGER NOT NULL CHECK (rarity BETWEEN 0 AND 2),
    stat      TEXT    NOT NULL,
    value     REAL    NOT NULL,
    descr     TEXT    NOT NULL DEFAULT '',
    max_level INTEGER NOT NULL DEFAULT 5 CHECK (max_level > 0)
);

CREATE TABLE contract_kinds (
    kind_key TEXT PRIMARY KEY,
    name     TEXT NOT NULL,
    stat     TEXT NOT NULL
);

CREATE TABLE achievements (
    achievement_key TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    descr           TEXT NOT NULL DEFAULT ''
);

-- ----------------------------------------------------------------------------
--  Индексы по внешним ключам (составные PK уже проиндексированы)
-- ----------------------------------------------------------------------------
CREATE INDEX idx_bosses_theme    ON bosses(theme_id);
CREATE INDEX idx_saves_theme     ON saves(theme_id);
CREATE INDEX idx_save_items_key  ON save_items(item_key);
CREATE INDEX idx_save_skins_key  ON save_skins(skin_id);
CREATE INDEX idx_notices_save    ON save_notices(save_id);
CREATE INDEX idx_meta_mod        ON save_meta(mod_key);
CREATE INDEX idx_tree_key        ON save_meta_tree(meta_key);
CREATE INDEX idx_relics_key      ON save_relics(relic_key);
CREATE INDEX idx_choices_key     ON save_relic_choices(relic_key);
CREATE INDEX idx_contracts_save  ON save_contracts(save_id);
CREATE INDEX idx_contracts_kind  ON save_contracts(kind_key);
CREATE INDEX idx_ach_key         ON save_achievements(achievement_key);

-- ============================================================================
--  Заполнение справочников (данные из taran/config.py и progression.py)
-- ============================================================================

INSERT INTO themes (theme_id, name, kills_required, kind, light) VALUES
  (0, 'Утро', 0, 'day', 0),
  (1, 'Закат', 25, 'sunset', 0.3),
  (2, 'Ночь', 70, 'night', 1),
  (3, 'Зима', 150, 'snow', 0.2),
  (4, 'Ливень', 270, 'rain', 0.6),
  (5, 'Неон-сити', 430, 'neon', 1),
  (6, 'Пустыня', 640, 'desert', 0),
  (7, 'Вулкан', 900, 'lava', 0.8),
  (8, 'Космос', 1210, 'space', 1),
  (9, 'Последняя станция', 1580, 'finale', 1),
  (10, 'Северное сияние', 2010, 'night', 1),
  (11, 'Штормовой порт', 2500, 'rain', 0.7),
  (12, 'Золотые дюны', 3050, 'desert', 0),
  (13, 'Ледяной дворец', 3660, 'snow', 0.3),
  (14, 'Мегаполис 2099', 4340, 'neon', 1),
  (15, 'Преисподняя', 5090, 'lava', 0.9),
  (16, 'Орбита', 5910, 'space', 1),
  (17, 'Затмение', 6800, 'night', 1),
  (18, 'Временной разлом', 7760, 'finale', 1),
  (19, 'Трон вокзала', 8800, 'finale', 1);

INSERT INTO bosses (boss_id, theme_id, name, hp, speed, time_limit, flags) VALUES
  (0, 0, 'Начальник станции', 40, 70, 45, ''),
  (1, 1, 'Бегун-спринтер', 70, 170, 45, 'erratic'),
  (2, 2, 'Тень', 100, 90, 50, 'ghost,acid'),
  (3, 3, 'Снеговик-гигант', 140, 60, 50, 'regen'),
  (4, 4, 'Громила с зонтом', 180, 80, 55, 'shield,acid'),
  (5, 5, 'Киборг-директор', 260, 110, 60, 'erratic,shield,regen'),
  (6, 6, 'Песчаный страж', 340, 130, 60, 'erratic,regen,acid'),
  (7, 7, 'Лавовый голем', 460, 75, 65, 'shield,regen,rage'),
  (8, 8, 'Пришелец-капитан', 620, 150, 70, 'ghost,erratic,blink'),
  (9, 9, 'Хозяйка вокзала', 900, 140, 90, 'erratic,shield,regen,ghost,rage,acid'),
  (10, 10, 'Смотритель полярного пути', 1000, 120, 85, 'regen,shield,dodge'),
  (11, 11, 'Капитан шторма', 1100, 165, 85, 'erratic,rage,acid'),
  (12, 12, 'Хранитель дюн', 1200, 115, 90, 'shield,regen,tough'),
  (13, 13, 'Ледяная королева', 1320, 135, 90, 'ghost,blink,acid,dodge'),
  (14, 14, 'Синт-директор', 1450, 175, 95, 'erratic,shield,regen,frenzy'),
  (15, 15, 'Владыка пепла', 1580, 105, 95, 'rage,regen,acid,tough,heal'),
  (16, 16, 'Командор орбиты', 1720, 185, 100, 'erratic,blink,shield,dodge,frenzy'),
  (17, 17, 'Тень затмения', 1870, 155, 100, 'ghost,blink,regen,acid,timesteal'),
  (18, 18, 'Хранитель времени', 2030, 165, 105, 'erratic,shield,regen,heal,frenzy,timesteal'),
  (19, 19, 'Император вокзала', 2250, 175, 115, 'erratic,shield,regen,ghost,rage,acid,heal,dodge,tough,frenzy');

INSERT INTO upgrades (upgrade_key, tab, req_level, name, base_cost, growth, max_level) VALUES
  ('power', 0, 0, 'Сила толчка', 50, 1.9, 10),
  ('income', 0, 0, 'Цена билета', 30, 1.6, 40),
  ('flow', 0, 0, 'Поток людей', 40, 1.55, 15),
  ('trains', 0, 0, 'Частота поездов', 60, 1.6, 12),
  ('helper', 0, 0, 'Помощник', 100, 1.7, 8),
  ('combo', 0, 0, 'Комбо', 80, 1.65, 12),
  ('gold', 0, 0, 'Золотые пассажиры', 120, 1.7, 8),
  ('smash', 0, 0, 'Удар по боссам', 60, 1.75, 20),
  ('crit', 1, 1, 'Критический клик', 150, 1.7, 10),
  ('idle', 1, 2, 'Пассивный доход', 200, 1.65, 15),
  ('gtrain', 1, 3, 'Золотой поезд', 300, 1.75, 10),
  ('timebonus', 1, 4, 'Время на боссов', 250, 1.7, 8),
  ('bot', 1, 5, 'Помощник-боец', 400, 1.7, 12),
  ('mult', 1, 6, 'Экспресс-билет', 600, 1.75, 20),
  ('cap', 1, 7, 'Вместимость', 500, 1.8, 6),
  ('combot', 1, 8, 'Долгое комбо', 700, 1.8, 8);

INSERT INTO items (item_key, name, duration_sec, price, descr) VALUES
  ('p_flow', 'Зелье потока', 30, 260, 'x2 приток людей, 30с'),
  ('p_train', 'Сжатое расписание', 45, 340, 'поезда x2 чаще, 45с'),
  ('p_money', 'Двойная касса', 30, 520, 'x2 весь доход, 30с'),
  ('p_power', 'Супер-толчок', 30, 420, 'радиус клика x2, 30с'),
  ('grenade', 'Граната', 0, 300, 'сбивает всех сразу'),
  ('antidote', 'Противоядие', 0, 150, 'смывает кислоту');

INSERT INTO skins (skin_id, name, palette) VALUES
  (0, 'Классика', '{}'),
  (1, 'Дед Мороз', '{"color": [200, 44, 44], "skin": [245, 210, 170], "hair": [240, 240, 245], "extra": "hat"}'),
  (2, 'Киборг', '{"color": [118, 130, 152], "skin": [175, 185, 195], "hair": [60, 66, 78], "extra": "visor"}'),
  (3, 'Призрак', '{"color": [206, 228, 255], "skin": [225, 235, 250], "hair": [200, 215, 240], "glow": [150, 200, 255]}'),
  (4, 'Неон', '{"color": [40, 255, 200], "skin": [198, 255, 240], "hair": [20, 40, 36], "glow": [0, 255, 200]}'),
  (5, 'Пират', '{"color": [72, 52, 42], "hair": [30, 24, 20], "extra": "tricorn", "eyepatch": true}'),
  (6, 'Астронавт', '{"color": [234, 240, 248], "skin": [200, 210, 225], "hair": [180, 190, 205], "extra": "helmet", "glow": [180, 210, 255]}'),
  (7, 'Дьявол', '{"color": [168, 32, 32], "skin": [198, 62, 52], "hair": [30, 12, 12], "extra": "horns", "glow": [255, 70, 40]}'),
  (8, 'Золотой', '{"color": [252, 202, 44], "skin": [252, 224, 132], "hair": [150, 110, 30], "extra": "crown", "glow": [255, 210, 60]}'),
  (9, 'Кот', '{"color": [92, 92, 122], "hair": [40, 40, 56], "extra": "ears"}'),
  (10, 'Король', '{"color": [122, 44, 162], "hair": [24, 18, 30], "extra": "crown", "glow": [200, 120, 255]}'),
  (11, 'Ледяной', '{"color": [122, 192, 242], "skin": [214, 238, 255], "hair": [230, 246, 255], "glow": [140, 210, 255]}');

INSERT INTO run_mods (mod_key, name, descr, income_mult, boss_mult, flow_mult) VALUES
  ('calm', 'Спокойный рейс', 'Без модификаторов', 1, 1, 1),
  ('fog', 'Туман', 'Доход +20%, боссы +20% HP', 1.2, 1.2, 1),
  ('holiday', 'Праздник', 'Поток +25%, доход +10%', 1.1, 1, 1.25),
  ('strike', 'Забастовка', 'Поток -20%, доход +35%', 1.35, 1, 0.8),
  ('race', 'Гонка', 'Поезда +20%, боссы +15%', 1.15, 1.15, 1),
  ('night', 'Ночная смена', 'Доход +25%, офлайн +15%', 1.25, 1, 1);

INSERT INTO meta_upgrades (meta_key, branch, name, descr, max_level, base_cost, growth, req_level) VALUES
  ('capital', 0, 'Оборотный капитал', 'Старт рейса', 20, 2, 1.42, 0),
  ('profit', 0, 'Коммерческая жилка', 'Весь доход', 25, 3, 1.38, 0),
  ('fare', 0, 'Гибкие тарифы', 'Цены ниже', 10, 4, 1.55, 0),
  ('offline', 0, 'Ночная смена', 'Офлайн-доход', 10, 5, 1.5, 1),
  ('market', 0, 'Оптовые закупки', 'Зелья дешевле', 8, 4, 1.5, 1),
  ('luck', 0, 'Счастливый билет', 'Золотые пассажиры', 10, 5, 1.5, 2),
  ('legacy', 0, 'Наследие', 'Бонус за ранг', 1, 25, 2, 5),
  ('tips', 0, 'Щедрые чаевые', 'Монеты', 10, 6, 1.5, 2),
  ('premia', 0, 'Премия за рейс', 'Чертежи за станции', 5, 10, 1.7, 4),
  ('fist', 1, 'Стальной кулак', 'Урон клика', 15, 2, 1.4, 0),
  ('radius', 1, 'Широкий замах', 'Радиус клика', 10, 3, 1.45, 0),
  ('bosstime', 1, 'Терпение', 'Время на босса', 10, 4, 1.5, 0),
  ('life', 1, 'Крепкие нервы', 'Жизни в хардкоре', 5, 6, 1.7, 1),
  ('crit', 1, 'Точный удар', 'Шанс крита', 10, 5, 1.5, 1),
  ('loot', 1, 'Трофейная команда', 'Награда за босса', 10, 5, 1.55, 2),
  ('execute', 1, 'Добивание', 'Урон по слабому боссу', 5, 8, 1.7, 4),
  ('sharp', 1, 'Точный расчёт', 'Урон крита x3', 8, 6, 1.55, 2),
  ('revive', 1, 'Второе дыхание', 'Спасение забега', 1, 30, 2, 5),
  ('autopush', 2, 'Автотолчок', 'Толкает сам', 8, 3, 1.45, 0),
  ('autobuy', 2, 'Автозакупка', 'Покупает сам', 5, 4, 1.6, 1),
  ('flow', 2, 'Логистика толпы', 'Приток людей', 10, 3, 1.45, 0),
  ('trains', 2, 'Диспетчер', 'Поезда чаще', 10, 4, 1.45, 1),
  ('start', 2, 'Экспресс-маршрут', 'Стартовая станция', 5, 8, 1.9, 3),
  ('keep', 2, 'Архив чертежей', 'Сохранить прокачку', 5, 6, 1.75, 2),
  ('archive', 2, 'Методичка', 'Больше чертежей', 10, 4, 1.5, 0),
  ('seat', 2, 'Плотная посадка', 'Мест на перроне', 10, 5, 1.5, 2),
  ('peak', 2, 'Разгон', 'Час пик', 6, 7, 1.55, 4);

INSERT INTO relics (relic_key, name, rarity, stat, value, descr, max_level) VALUES
  ('compass', 'Медный компас', 0, 'income', 0.06, '+6% доход', 5),
  ('coupon', 'Старый талон', 0, 'price', 0.04, '-4% цены', 5),
  ('glove', 'Кожаная перчатка', 0, 'click', 1, '+1 урон клика', 5),
  ('lamp', 'Красный фонарь', 0, 'flow', 0.06, '+6% поток', 5),
  ('coin', 'Счастливая монета', 1, 'coin', 0.15, '+15% монеты', 5),
  ('watch', 'Часы машиниста', 1, 'bosstime', 2, '+2с на босса', 5),
  ('flask', 'Фляга обходчика', 1, 'life', 1, '+1 жизнь', 5),
  ('book', 'Блокнот ревизора', 1, 'bp', 0.08, '+8% чертежей', 5),
  ('gear', 'Шестерня экспресса', 1, 'trains', 0.08, '+8% поезда', 5),
  ('mask', 'Маска начальника', 2, 'boss', 0.15, '+15% награда за босса', 5),
  ('crown', 'Корона вокзала', 2, 'income', 0.18, '+18% доход', 5),
  ('core', 'Ядро времени', 2, 'offline', 0.15, '+15% офлайн', 5);

INSERT INTO contract_kinds (kind_key, name, stat) VALUES
  ('push', 'Столкнуть пассажиров', 'push'),
  ('boss', 'Победить боссов', 'boss'),
  ('earn', 'Заработать на билетах', 'earn'),
  ('coins', 'Поймать монеты', 'coins'),
  ('station', 'Пройти станций', 'station'),
  ('combo', 'Собрать серию', 'combo');

INSERT INTO achievements (achievement_key, name, descr) VALUES
  ('first_push', 'Первый пассажир', 'Столкнуть 1 пассажира'),
  ('push_100', 'Работяга', 'Столкнуть 100 пассажиров'),
  ('push_1000', 'Машинист дня', 'Столкнуть 1000 пассажиров'),
  ('push_10000', 'Живая легенда', 'Столкнуть 10 000 пассажиров'),
  ('first_boss', 'Первый босс', 'Победить 1 босса'),
  ('boss_10', 'Гроза вокзалов', 'Победить 10 боссов'),
  ('boss_50', 'Кошмар депо', 'Победить 50 боссов'),
  ('boss_100', 'Император путей', 'Победить 100 боссов'),
  ('first_rebirth', 'Новый рейс', 'Переродиться 1 раз'),
  ('rebirth_5', 'Ветеран', 'Переродиться 5 раз'),
  ('rebirth_20', 'Бессмертный', 'Переродиться 20 раз'),
  ('station_5', 'Дальний маршрут', 'Дойти до станции 5'),
  ('station_10', 'Ночной экспресс', 'Дойти до станции 10'),
  ('station_20', 'Трон вокзала', 'Пройти все 20 станций'),
  ('earn_1m', 'Миллионер', 'Заработать $1M за всё время'),
  ('earn_1b', 'Магнат путей', 'Заработать $1B за всё время'),
  ('combo_25', 'Серия', 'Собрать комбо x25'),
  ('combo_100', 'Конвейер', 'Собрать комбо x100'),
  ('coins_50', 'Кладоискатель', 'Поймать 50 монет'),
  ('coins_500', 'Золотая касса', 'Поймать 500 монет'),
  ('relics_8', 'Коллекционер', 'Собрать 8 реликвий'),
  ('tree_30', 'Инженер', 'Открыть 30 уровней депо'),
  ('contracts_20', 'Подрядчик', 'Выполнить 20 контрактов'),
  ('hard_10m', 'Несокрушимый', 'Продержаться 10 минут в хардкоре');

-- Проверка: 22 таблицы, 20 локаций, 20 боссов, 16 улучшений, 6 расходников,
-- 12 скинов, 6 модификаторов, 27 узлов депо, 12 реликвий, 6 типов контрактов,
-- 24 достижения. Демо-сейв не добавляется: его создаёт игра при первом запуске.

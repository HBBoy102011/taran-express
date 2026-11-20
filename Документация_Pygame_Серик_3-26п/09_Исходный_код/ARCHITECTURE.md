# Архитектура «ТАРАН-ЭКСПРЕСС»

Документ фиксирует, как игра разделена на модули сейчас и куда двигаться
дальше. Главное правило: **поведение, сейвы и мобильная сборка не меняются**.
Рефакторинг идёт маленькими шагами, после каждого — тесты и скриншоты.

## Текущая схема

```
game.py                 точка входа и композиционный корень:
                        окно, масштаб, рисование, сущности, главный цикл
progression.py          мета-прогресс (чертежи, дерево, реликвии, контракты)
prog_ui.py              тонкий реэкспорт taran/ui/hud.py (совместимость)
taran/
  config.py             статические данные: геометрия, темы, боссы,
                        улучшения, предметы, скины, константы баланса
  logic.py              чистые расчёты: цены, инфляция, пороги, жребий публики
  saves.py              чтение/запись save.json с миграцией старых сейвов
  audio.py              SoundKit: эффекты и музыка
  world.py              World: небо, город, платформа, пути, погода
  train.py              train_sprite + Train
  effects.py            Effect, TapFX, Particle, Coin, Decal, SkullFly, Acid
  creatures.py          спрайты боссов-зверей (pigeon … dragon)
  assets.py             виньетка, конусы, тени, череп, кислота, фон магазина
  ui/
    theme.py            единая палитра интерфейса
    shop.py             панель «Мастерская»: карточки, вкладки, цены, пульс
    hud.py              HUD рейса, сердца, звук, полоса босса, экран «Депо»
mobile/
  make_mobile.py        патчит game.py под pygbag и копирует модули
  game_app.py           результат сборки (не редактировать вручную)
```

`game.py` остаётся точкой входа: он импортирует `taran.config` и
`taran.ui.theme` звёздочкой, поэтому старые обращения `game.W`,
`game.THEMES`, `game.UI_GOLD`, `game.KIND_HP` продолжают работать — на них
завязаны тесты и `prog_ui.py`. Вынесенные функции и классы (`game.cost`,
`game.World`, `game.Train`, `game.Effect`, `game.creature_surf` и т.д.)
реэкспортируются из своих модулей, так что старый код не ломается.

## Правила зависимостей

1. `taran/config.py` и `taran/ui/theme.py` — **чистые данные**. Они не
   импортируют `pygame`, `game` или UI. Их можно тестировать отдельно.
2. `taran/logic.py` и `taran/saves.py` — **чистая логика**. Зависят только от
   `taran.config` и `progression.py`; путь к сейву передаётся аргументом.
3. `taran/audio.py` не знает про игру: `SoundKit(base_dir)` создаётся в
   `game.py`, все ошибки микшера глушатся внутри.
4. Модули с отрисовкой (`world`, `train`, `effects`, `creatures`, `assets`,
   `taran/ui/shop.py`, `taran/ui/hud.py`) **не импортируют `game.py`**.
   Связь — через `bind(game_module)` и `_sync()`: перед рисованием модуль
   подтягивает актуальные `K`, шрифты, `D` и кэши. Это позволяет менять
   масштаб и ассеты без перезапуска.
5. `progression.py` и `prog_ui.py` по-прежнему получают игру через `G`.
6. `game.py` — единственное место, где создаётся окно и запускается цикл.

Мост `_sync()` временный: когда появится общий `taran/ui/kit.py` с `D`,
`text`, шрифтами и палитрой, модули будут импортировать его напрямую,
а `bind()` можно будет убрать.

## Мобильная сборка

`mobile/make_mobile.py` читает `game.py` и патчит его по точным строкам.
Поэтому:

* **не менять** патчимые строки без правки `make_mobile.py`;
* новые модули должны копироваться в `mobile/` рядом с `game_app.py`;
  сейчас это `progression.py`, `prog_ui.py` и пакет `taran/`;
* подсказки магазина живут в `taran/ui/shop.py`, поэтому скрипт патчит уже
  скопированный модуль (а не `game.py`);
* `pygbag.ini` исключает служебные файлы сборки, а `.py`-файлы `taran/`
  попадают в архив автоматически.

Проверка после изменений:

```bat
py test_smoke.py
py _meta_test.py
py _shot.py
py mobile/make_mobile.py
```

## Что уже вынесено

| Этап | Модуль | Что внутри |
|---|---|---|
| A | `taran/config.py` | 20 тем, 20 боссов, 16 улучшений, 6 предметов, скины, геометрия, константы |
| B | `taran/ui/theme.py` | палитра `UI_*` |
| C | `taran/ui/shop.py` | `draw_panel`, карточки, «пилюли» цен, вкладки, пульс покупки |
| D | `taran/audio.py` | `SoundKit`, эффекты, музыка, приглушение на паузе |
| E | `taran/logic.py` | `cost`, `inflation`, `item_price`, `boss_at`, `stage_for`, `pick_kind`, `pick_skin` |
| F | `taran/saves.py` | `new_save`, `load_save`, `write_save` с терпимостью к старым сейвам |
| G | `taran/world.py` | `World`: статичные слои, кэш, погода, станция, фонари |
| H | `taran/train.py` | `train_sprite`, `Train`, кэш состава |
| I | `taran/effects.py` | `Effect`, `TapFX`, `Particle`, `Coin`, `Decal`, `SkullFly`, `Acid` |
| J | `taran/creatures.py` | `_c_*`, `creature_surf`, кэш `SPR` |
| K | `taran/ui/hud.py` | HUD, сердца, кнопка звука, полоса босса, «Депо» |
| L | `taran/assets.py` | `make_vignette`, `make_cone`, `make_shadow`, `make_skull`, `make_acid_overlay`, `build_panel_bg` |

## Следующие этапы

1. **`taran/ui/kit.py`** — общие примитивы рисования (`D`, `text`, `lerp_c`,
   `ellipsize`, `twidth`, шрифты). Убирает `_sync()` из UI-модулей.
2. **`taran/ui/depot.py`** — выделить экран «Депо» из `taran/ui/hud.py`.
3. **`taran/entities.py`** — `Person`, `Boss`, секретные боссы и слизень.
4. **`taran/app.py`** — главный цикл и состояния (заставка, пауза, игра).
   `game.py` превращается в тонкую точку входа.
5. **`taran/assets.py`**: осталось перенести `build_assets` и заставку —
   сами строители ресурсов уже там.

После каждого этапа: тесты, скриншоты, затем `py mobile/make_mobile.py`.

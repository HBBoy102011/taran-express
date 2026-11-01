# Поезд-кликер (train_game)

Кликер на pygame. Десктопная версия — `game.py`; мобильная собирается в
**офлайн-APK** через pygbag (pygame → WebAssembly) и упаковку в Android-APK
без Gradle.

## Структура

| Путь | Что это |
|---|---|
| `game.py` | исходник игры (десктоп, pygame) |
| `intro_frames/` | кадры заставки |
| `test_smoke.py` | дымовой тест десктопной логики |
| `mobile/` | весь пайплайн мобильной сборки |
| `mobile/make_mobile.py` | патчит `game.py` под веб → `mobile/game_app.py` |
| `mobile/rebuild.py` | сборка APK одной командой |
| `mobile/build_apk.py` | упаковка и подпись APK (aapt2/d8/apksigner) |
| `mobile/setup.py` | проверка/докачка инструментов (`--fetch`) |
| `apk/` | AndroidManifest, MainActivity, иконка |
| `pygbag.ini` | что НЕ паковать в архив игры |

Каталоги `android_sdk/`, `.apkbuild/`, `packages/`, `mobile/cdn_cache/`,
`mobile/build/` в git не входят — они восстанавливаются (см. ниже).

## Сборка APK

Нужен Python 3.12+ (`py`), интернет — только при первой настройке:

```bash
py mobile/setup.py --fetch   # один раз: JDK, build-tools, рантайм pygbag
py mobile/rebuild.py         # полная сборка -> mobile/build/train_game_v4.0.apk
```

Готовый APK: `mobile/build/train_game_v4.0.apk` (~22 МБ). Ставится на телефон
обычной копией файла (разрешение «установка из неизвестных источников»).
Игра работает **полностью офлайн**: CPython-WASM, pygame и все ассеты лежат
внутри APK, внешних запросов нет.

APK подписан самоподписанным debug-ключом (`android_sdk/debug.keystore`) —
для себя/друзей этого достаточно, для Google Play нужен выпускной ключ.

## Публикация в Google Play (кратко)

1. Аккаунт разработчика Play Console — $25 разово, верификация личности.
2. Play принимает только **`.aab`** (Android App Bundle), не APK.
3. `targetSdkVersion` для новых приложений — **36** (Android 16); сейчас в
   сборке 33, поэтому перед публикацией надо поднять `--target-sdk-version`
   в `mobile/build_apk.py` и положить `android_sdk/platform` версии 36.
4. Нужны: приватная политика (ссылка в магазине и в приложении), форма
   «Безопасность данных», рейтинг IARC, 64-bit (у нас нет нативных библиотек —
   выполняется автоматически).
5. Для личного аккаунта перед выходом в прод — закрытое тестирование:
   12 тестировщиков, 14 дней подряд.
6. Подписи: Play App Signing — Google хранит выпускной ключ, первый `.aab`
   подписывается вашим ключом (`keytool -genkeypair`), дальше Play сам
   подписывает выдаваемые APK.

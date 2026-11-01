#!/bin/sh
# Скачивает всё, что нужно для сборки APK: JDK 17 и Android build-tools с android.jar.
cd "C:/Users/Zhanik/Desktop/PyGames/train_game_v3.0/android_sdk" || exit 1
for u in \
 "https://dl.google.com/android/repository/build-tools_r34-windows.zip|bt.zip" \
 "https://dl.google.com/android/repository/platform-34-ext7_r03.zip|platform.zip" \
 "https://api.adoptium.net/v3/binary/latest/17/ga/windows/x64/jdk/hotspot/normal/eclipse|jdk.zip"
do
  url="${u%%|*}"; f="${u##*|}"
  curl -L --retry 5 --retry-delay 3 -C - -sS -o "$f" "$url" && echo "OK $f $(stat -c %s "$f")" || echo "FAIL $f"
done
echo ALLDONE

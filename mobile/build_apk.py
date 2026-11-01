# -*- coding: utf-8 -*-
"""Собирает APK из веб-версии игры (mobile/build/web) без Gradle.

Три архива скачиваются заранее (см. mobile/dl_sdk.sh) и распаковываются в
android_sdk/: JDK 17, build-tools (aapt2, d8, apksigner, zipalign) и android.jar.

    py mobile/build_apk.py          ->  mobile/build/train_game_v4.0.apk

АПК подписывается debug-ключом (self-signed) — для себя и друзей этого хватает,
для Google Play нужен свой выпускной ключ.
"""
import os
import shutil
import subprocess
import sys
import zipfile

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SDK = os.path.join(ROOT, "android_sdk")
WEB = os.path.join(HERE, "build", "web")
WORK = os.path.join(HERE, "build", "apk_work")
OUT_APK = os.path.join(HERE, "build", "train_game_v4.0.apk")
PKG = "com.ice.trainclicker"


def die(msg):
    sys.exit("СБОРКА ОСТАНОВЛЕНА: " + msg)


ENV = None          # JAVA_HOME из распакованного JDK: d8.bat/apksigner.bat требуют его


def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, errors="replace",
                       encoding="utf-8", env=ENV)
    if p.returncode != 0:
        print(p.stdout[-3000:])
        print(p.stderr[-3000:])
        die("команда не прошла: " + " ".join(str(c) for c in cmd))
    return p.stdout


def find_under(base, *names):
    """Ищет файл/папку в распакованном архиве (там вложенная папка вида android-14)."""
    for dirpath, dirnames, filenames in os.walk(base):
        for n in names:
            p = os.path.join(dirpath, n)
            if os.path.exists(p):
                return p
    return None


def main():
    if not os.path.exists(os.path.join(WEB, "index.html")):
        die("нет веб-сборки: сначала py mobile/make_mobile.py и pygbag build")

    # ---------- 1. распаковка инструментов ----------
    jdk = os.path.join(SDK, "jdk")
    bt = os.path.join(SDK, "build-tools")
    plat = os.path.join(SDK, "platform")
    if not os.path.isdir(jdk):
        print("распаковываю JDK...")
        shutil.unpack_archive(os.path.join(SDK, "jdk.zip"), jdk, "zip")
    if not os.path.isdir(bt):
        print("распаковываю build-tools...")
        shutil.unpack_archive(os.path.join(SDK, "bt.zip"), bt, "zip")
    if not os.path.isdir(plat):
        print("распаковываю платформу Android...")
        shutil.unpack_archive(os.path.join(SDK, "platform.zip"), plat, "zip")

    javac = find_under(jdk, "javac.exe")
    java = find_under(jdk, "java.exe")
    keytool = find_under(jdk, "keytool.exe")
    aapt2 = find_under(bt, "aapt2.exe")
    d8 = find_under(bt, "d8.bat") or find_under(bt, "d8")
    apksigner = find_under(bt, "apksigner.bat") or find_under(bt, "apksigner")
    zipalign = find_under(bt, "zipalign.exe")
    android_jar = find_under(plat, "android.jar")
    missing = [n for n, v in (("javac", javac), ("java", java), ("keytool", keytool),
                              ("aapt2", aapt2), ("d8", d8), ("apksigner", apksigner),
                              ("zipalign", zipalign), ("android.jar", android_jar)) if not v]
    if missing:
        die("не найдено в android_sdk: " + ", ".join(missing) + " — дополни dl_sdk.sh")
    print("инструменты на месте")
    global ENV
    ENV = dict(os.environ)
    ENV["JAVA_HOME"] = os.path.dirname(os.path.dirname(javac))
    ENV["PATH"] = ENV["JAVA_HOME"] + r"\bin" + os.pathsep + ENV.get("PATH", "")

    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)

    # ---------- 2. assets: копия веб-сборки ----------
    print("копирую веб-сборку в assets (~23 МБ)...")
    assets = os.path.join(WORK, "assets", "web")
    shutil.copytree(WEB, assets,
                    ignore=shutil.ignore_patterns("*.log", "*.tar.gz", "mobile.apk"))

    # ---------- 3. манифест и ресурсы ----------
    manifest = os.path.join(ROOT, "apk", "AndroidManifest.xml")
    res_dir = os.path.join(WORK, "res")
    os.makedirs(res_dir, exist_ok=True)
    icon_src = os.path.join(ROOT, "apk", "icon.png")
    if not os.path.exists(icon_src):
        icon_src = os.path.join(WEB, "favicon.png")
    if os.path.exists(icon_src):
        d = os.path.join(res_dir, "drawable")
        os.makedirs(d, exist_ok=True)
        shutil.copy(icon_src, os.path.join(d, "ic_launcher.png"))

    res_zip = os.path.join(WORK, "res.zip")
    if os.path.exists(os.path.join(res_dir, "drawable")):
        run([aapt2, "compile", "--dir", res_dir, "-o", res_zip])
    else:
        res_zip = None

    base_apk = os.path.join(WORK, "base.apk")
    cmd = [aapt2, "link", "-I", android_jar, "--manifest", manifest,
           "-o", base_apk, "--min-sdk-version", "23", "--target-sdk-version", "33",
           "--auto-add-overlay", "--no-version-vectors"]
    if res_zip:
        cmd += [res_zip]
    run(cmd)

    # ---------- 4. Java -> classes.dex ----------
    print("компилирую Java...")
    src = os.path.join(ROOT, "apk", "MainActivity.java")
    classes = os.path.join(WORK, "classes")
    os.makedirs(classes, exist_ok=True)
    run([javac, "-source", "8", "-target", "8", "-classpath", android_jar,
         "-d", classes, src])
    print("делаю dex (d8)...")
    classes_jar = os.path.join(WORK, "classes.jar")
    with zipfile.ZipFile(classes_jar, "w") as z:
        for dp, dn, fns in os.walk(classes):
            for fn in fns:
                full = os.path.join(dp, fn)
                z.write(full, os.path.relpath(full, classes))
    dex_out = os.path.join(WORK, "dex")
    os.makedirs(dex_out, exist_ok=True)
    run([d8, "--release", "--lib", android_jar, "--output", dex_out, classes_jar])
    dex_file = os.path.join(dex_out, "classes.dex")
    if not os.path.exists(dex_file):
        die("d8 не создал classes.dex")

    # ---------- 5. упаковка apk ----------
    with zipfile.ZipFile(base_apk, "a", zipfile.ZIP_DEFLATED) as z:
        z.write(dex_file, "classes.dex")
        for dp, dn, fns in os.walk(assets):
            for fn in fns:
                full = os.path.join(dp, fn)
                # путь в архиве = assets/web/... — так его ищет getAssets().open("web/...")
                arc = "assets/" + os.path.relpath(full, os.path.dirname(assets)).replace(os.sep, "/")
                # сжатие мешает отдавать файл потоком — бинарники кладём без сжатия
                mode = zipfile.ZIP_STORED if fn.endswith((".wasm", ".data", ".js", ".whl", ".ogg")) else zipfile.ZIP_DEFLATED
                if mode == zipfile.ZIP_STORED:
                    with open(full, "rb") as fh:
                        z.writestr(zipfile.ZipInfo(arc), fh.read(), zipfile.ZIP_STORED)
                else:
                    z.write(full, arc, mode)

    aligned = os.path.join(WORK, "aligned.apk")
    run([zipalign, "-f", "4", base_apk, aligned])

    # ---------- 6. подпись ----------
    ks = os.path.join(SDK, "debug.keystore")
    if not os.path.exists(ks):
        print("создаю самоподписанный ключ (debug)...")
        run([keytool, "-genkeypair", "-keystore", ks, "-storepass", "android",
             "-keypass", "android", "-alias", "androiddebugkey", "-keyalg", "RSA",
             "-keysize", "2048", "-validity", "10000",
             "-dname", "CN=Android Debug,O=Android,C=US"])
    run([apksigner, "sign", "--ks", ks, "--ks-pass", "pass:android",
         "--key-pass", "pass:android", "--out", OUT_APK, aligned])
    run([apksigner, "verify", "--print-certs", OUT_APK])

    need = ["classes.dex", "assets/web/index.html", "assets/web/cdn/0.9.3/pythons.js",
            "assets/web/cdn/0.9.3/cpython312/main.wasm",
            "assets/web/cdn/0.9.3/cpython312/main.data",
            "assets/web/cdn/index-0.9.3-cp312.json",
            "assets/web/cdn/cp312/pygame_ce-2.5.7-cp312-cp312-wasm32_bi_emscripten.whl"]
    with zipfile.ZipFile(OUT_APK) as z:
        names = z.namelist()
    miss = [k for k in need if k not in names]
    if miss:
        die("в APK не попало: " + ", ".join(miss))

    size = os.path.getsize(OUT_APK) / 1024 / 1024
    print(f"\nГОТОВО: {OUT_APK}  ({size:.1f} МБ)")


if __name__ == "__main__":
    main()

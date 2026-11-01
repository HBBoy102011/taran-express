package com.ice.trainclicker;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.WindowManager;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.HashMap;
import java.util.Map;

/**
 * Обёртка вокруг веб-сборки игры (pygbag/WASM).
 *
 * Файлы игры лежат в assets/web. Запросы к https://game.local/ перехватываются и
 * отдаются из APK — так у страницы есть настоящий origin (иначе не работает
 * localStorage с прогрессом) и корректные MIME-типы для .wasm.
 */
public class MainActivity extends Activity {
    private static final String HOST = "https://game.local/";

    private WebView web;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(false);
        s.setSupportZoom(false);
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(true);
        web.setBackgroundColor(0xFF0A0C18);

        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest req) {
                String url = req.getUrl().toString();
                if (!url.startsWith(HOST)) {
                    return null;                       // всё внешнее блокируем: игра офлайновая
                }
                String path = url.substring(HOST.length());
                int cut = path.indexOf('?');
                if (cut >= 0) {
                    path = path.substring(0, cut);
                }
                if (path.isEmpty()) {
                    path = "index.html";
                }
                try {
                    InputStream in = getAssets().open("web/" + path);
                    Map<String, String> h = new HashMap<String, String>();
                    h.put("Access-Control-Allow-Origin", "*");
                    h.put("Cross-Origin-Opener-Policy", "same-origin");
                    h.put("Cross-Origin-Embedder-Policy", "require-corp");
                    h.put("Cross-Origin-Resource-Policy", "cross-origin");
                    WebResourceResponse res =
                            new WebResourceResponse(mime(path), encoding(path), in);
                    res.setResponseHeaders(h);
                    return res;
                } catch (IOException e) {
                    return new WebResourceResponse("text/plain", "utf-8",
                            new ByteArrayInputStream(("нет файла: " + path).getBytes()));
                }
            }
        });

        setContentView(web);
        hideSystemUi();
        web.loadUrl(HOST + "index.html");
    }

    private static String mime(String path) {
        String p = path.toLowerCase();
        if (p.endsWith(".html")) return "text/html";
        if (p.endsWith(".js")) return "text/javascript";
        if (p.endsWith(".css")) return "text/css";
        if (p.endsWith(".wasm")) return "application/wasm";
        if (p.endsWith(".json")) return "application/json";
        if (p.endsWith(".png")) return "image/png";
        if (p.endsWith(".ogg")) return "audio/ogg";
        if (p.endsWith(".ttf")) return "font/ttf";
        return "application/octet-stream";
    }

    private static String encoding(String path) {
        String m = mime(path);
        if (m.startsWith("text/") || m.equals("application/json")) {
            return "utf-8";
        }
        return null;
    }

    private void hideSystemUi() {
        View d = getWindow().getDecorView();
        d.setSystemUiVisibility(View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                | View.SYSTEM_UI_FLAG_FULLSCREEN
                | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
    }

    @Override
    public void onWindowFocusChanged(boolean focused) {
        super.onWindowFocusChanged(focused);
        if (focused && web != null) {
            hideSystemUi();
        }
    }

    @Override
    public void onBackPressed() {
        // назад — пауза: игра сохраняет прогресс сама, окно просто не закрываем случайно
        if (web != null && web.canGoBack()) {
            web.goBack();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (web != null) {
            web.onPause();
            web.pauseTimers();
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (web != null) {
            web.resumeTimers();
            web.onResume();
        }
        if (Build.VERSION.SDK_INT >= 19) {
            hideSystemUi();
        }
    }
}

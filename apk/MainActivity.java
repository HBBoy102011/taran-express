package com.ice.trainclicker;

import android.annotation.SuppressLint;
import android.annotation.TargetApi;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.webkit.ConsoleMessage;
import android.webkit.JavascriptInterface;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.URLDecoder;
import java.util.HashMap;
import java.util.Map;

/**
 * Обёртка вокруг веб-сборки игры (pygbag/WASM).
 *
 * Файлы игры лежат в assets/web. Запросы к https://game.local/ перехватываются и
 * отдаются из APK — так у страницы есть настоящий origin (иначе не работает
 * localStorage с прогрессом) и корректные MIME-типы для .wasm.
 *
 * Пока страница грузится, сверху висит тёмная заставка с названием: никакого
 * серого экрана. Дальше эстафету принимает HTML-экран загрузки с процентами.
 */
public class MainActivity extends Activity {
    private static final String TAG = "TaranExpress";
    private static final String HOST = "https://game.local/";
    private static final int BG = 0xFF070B18;

    private FrameLayout root;
    private WebView web;
    private LinearLayout splash;
    private TextView splashTitle;
    private TextView splashSub;
    private ProgressBar splashBar;
    private Button splashRetry;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().setBackgroundDrawable(new android.graphics.drawable.ColorDrawable(BG));

        root = new FrameLayout(this);
        root.setBackgroundColor(BG);

        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setJavaScriptCanOpenWindowsAutomatically(false);
        s.setSupportZoom(false);
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(true);
        if (Build.VERSION.SDK_INT >= 21) {
            s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        }
        web.setBackgroundColor(BG);
        web.setVerticalScrollBarEnabled(false);
        web.setHorizontalScrollBarEnabled(false);
        if (Build.VERSION.SDK_INT >= 19) {
            WebView.setWebContentsDebuggingEnabled(true);
        }

        web.addJavascriptInterface(new Bridge(), "AndroidApp");
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onConsoleMessage(ConsoleMessage m) {
                Log.d(TAG, m.message() + " @ " + m.sourceId() + ":" + m.lineNumber());
                return true;
            }
        });
        web.setWebViewClient(new GameClient());

        root.addView(web, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        buildSplash();
        root.addView(splash, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        setContentView(root);

        hideSystemUi();
        web.loadUrl(HOST + "index.html?v=" + versionName());
    }

    private String versionName() {
        try {
            return getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
        } catch (PackageManager.NameNotFoundException e) {
            return "2";
        }
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }

    private void buildSplash() {
        splash = new LinearLayout(this);
        splash.setOrientation(LinearLayout.VERTICAL);
        splash.setGravity(Gravity.CENTER);
        splash.setBackgroundColor(BG);
        splash.setPadding(dp(28), dp(24), dp(28), dp(24));

        splashTitle = new TextView(this);
        splashTitle.setText("ТАРАН-ЭКСПРЕСС");
        splashTitle.setTextColor(Color.WHITE);
        splashTitle.setTextSize(28);
        splashTitle.setGravity(Gravity.CENTER);
        splashTitle.setLetterSpacing(0.08f);
        splashTitle.setTypeface(splashTitle.getTypeface(), android.graphics.Typeface.BOLD);

        splashSub = new TextView(this);
        splashSub.setText("Рельсы. Толпа. Хаос.");
        splashSub.setTextColor(0xFFFFD76A);
        splashSub.setTextSize(13);
        splashSub.setGravity(Gravity.CENTER);
        splashSub.setLetterSpacing(0.12f);
        LinearLayout.LayoutParams subLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        subLp.topMargin = dp(8);
        subLp.bottomMargin = dp(26);

        splashBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        splashBar.setIndeterminate(true);
        if (Build.VERSION.SDK_INT >= 21) {
            splashBar.setIndeterminateTintList(ColorStateList.valueOf(0xFF6FE3FF));
        }
        LinearLayout.LayoutParams barLp = new LinearLayout.LayoutParams(dp(210), dp(4));
        barLp.bottomMargin = dp(18);

        TextView wait = new TextView(this);
        wait.setText("Загрузка…");
        wait.setTextColor(0xFF8FA3C8);
        wait.setTextSize(13);
        wait.setGravity(Gravity.CENTER);

        splashRetry = new Button(this);
        splashRetry.setText("Перезапустить");
        splashRetry.setVisibility(View.GONE);
        splashRetry.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                showSplash();
                web.loadUrl(HOST + "index.html?v=" + versionName());
            }
        });

        splash.addView(splashTitle);
        splash.addView(splashSub, subLp);
        splash.addView(splashBar, barLp);
        splash.addView(wait);
        splash.addView(splashRetry);
    }

    private void hideSplash() {
        if (splash == null || splash.getVisibility() != View.VISIBLE) {
            return;
        }
        splash.animate().alpha(0f).setDuration(380).withEndAction(new Runnable() {
            @Override
            public void run() {
                if (splash != null) {
                    splash.setVisibility(View.GONE);
                }
            }
        }).start();
    }

    private void showSplash() {
        if (splash == null) {
            return;
        }
        splash.setAlpha(1f);
        splash.setVisibility(View.VISIBLE);
        splashTitle.setText("ТАРАН-ЭКСПРЕСС");
        splashSub.setText("Загрузка…");
        splashBar.setVisibility(View.VISIBLE);
        splashRetry.setVisibility(View.GONE);
    }

    private void showFatal(String message) {
        if (splash == null) {
            return;
        }
        splash.setAlpha(1f);
        splash.setVisibility(View.VISIBLE);
        splashTitle.setText("Не удалось запустить");
        splashSub.setText(message == null ? "Неизвестная ошибка" : message);
        splashBar.setVisibility(View.GONE);
        splashRetry.setVisibility(View.VISIBLE);
    }

    private class Bridge {
        @JavascriptInterface
        public void gameReady() {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    hideSplash();
                }
            });
        }

        @JavascriptInterface
        public void bootError(final String msg) {
            Log.e(TAG, "boot error: " + msg);
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    showFatal(msg);
                }
            });
        }

        @JavascriptInterface
        public void log(String msg) {
            Log.i(TAG, msg);
        }
    }

    private class GameClient extends WebViewClient {
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
            cut = path.indexOf('#');
            if (cut >= 0) {
                path = path.substring(0, cut);
            }
            try {
                path = URLDecoder.decode(path, "UTF-8");
            } catch (Exception ignored) {
                // оставляем как есть
            }
            if (path.isEmpty() || path.endsWith("/")) {
                path = path + "index.html";
            }
            if (path.contains("..")) {
                return new WebResourceResponse("text/plain", "utf-8",
                        new ByteArrayInputStream("bad path".getBytes()));
            }
            String asset = "web/" + path;
            try {
                InputStream in = getAssets().open(asset);
                Map<String, String> h = new HashMap<String, String>();
                h.put("Access-Control-Allow-Origin", "*");
                h.put("Cross-Origin-Opener-Policy", "same-origin");
                h.put("Cross-Origin-Embedder-Policy", "require-corp");
                h.put("Cross-Origin-Resource-Policy", "cross-origin");
                h.put("Cache-Control", "no-cache");
                long size = assetSize(asset);
                if (size >= 0) {
                    h.put("Content-Length", Long.toString(size));
                }
                WebResourceResponse res =
                        new WebResourceResponse(mime(path), encoding(path), in);
                res.setResponseHeaders(h);
                return res;
            } catch (IOException e) {
                Log.e(TAG, "нет asset: " + asset);
                return new WebResourceResponse("text/plain", "utf-8",
                        new ByteArrayInputStream(("нет файла: " + path).getBytes()));
            }
        }

        @Override
        public void onPageFinished(WebView view, String url) {
            super.onPageFinished(view, url);
            // HTML-экран загрузки уже на экране — нативную заставку можно убрать
            hideSplash();
        }

        @Override
        public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
            super.onReceivedError(view, request, error);
            if (request.isForMainFrame()) {
                Log.e(TAG, "ошибка страницы: " + error.getDescription());
                showFatal("Ошибка загрузки страницы: " + error.getDescription());
            }
        }

        @Override
        @TargetApi(26)
        public boolean onRenderProcessGone(WebView view, RenderProcessGoneDetail detail) {
            Log.e(TAG, "процесс WebView завершился, перезапускаем");
            recreate();
            return true;
        }
    }

    private long assetSize(String asset) {
        android.content.res.AssetFileDescriptor afd = null;
        try {
            afd = getAssets().openFd(asset);
            return afd.getLength();
        } catch (IOException e) {
            return -1;                 // сжатый asset: длину не узнать, это нормально
        } finally {
            if (afd != null) {
                try {
                    afd.close();
                } catch (IOException ignored) {
                }
            }
        }
    }

    private static String mime(String path) {
        String p = path.toLowerCase();
        if (p.endsWith(".html")) return "text/html";
        if (p.endsWith(".js") || p.endsWith(".mjs")) return "text/javascript";
        if (p.endsWith(".css")) return "text/css";
        if (p.endsWith(".wasm")) return "application/wasm";
        if (p.endsWith(".json")) return "application/json";
        if (p.endsWith(".png")) return "image/png";
        if (p.endsWith(".jpg") || p.endsWith(".jpeg")) return "image/jpeg";
        if (p.endsWith(".webp")) return "image/webp";
        if (p.endsWith(".svg")) return "image/svg+xml";
        if (p.endsWith(".ogg") || p.endsWith(".oga")) return "audio/ogg";
        if (p.endsWith(".wav")) return "audio/wav";
        if (p.endsWith(".mp3")) return "audio/mpeg";
        if (p.endsWith(".ttf")) return "font/ttf";
        if (p.endsWith(".otf")) return "font/otf";
        if (p.endsWith(".woff")) return "font/woff";
        if (p.endsWith(".woff2")) return "font/woff2";
        return "application/octet-stream";
    }

    private static String encoding(String path) {
        String m = mime(path);
        if (m.startsWith("text/") || m.equals("application/json") || m.equals("image/svg+xml")) {
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
        // прогресс сохраняется сам: назад сворачивает игру, а не убивает процесс
        if (web != null && web.canGoBack()) {
            web.goBack();
        } else {
            moveTaskToBack(true);
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

    @Override
    protected void onDestroy() {
        if (web != null) {
            web.removeJavascriptInterface("AndroidApp");
            web.destroy();
            web = null;
        }
        super.onDestroy();
    }
}

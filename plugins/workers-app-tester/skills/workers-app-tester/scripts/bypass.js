// bypass.js — Universal SSL pinning bypass for Android apps
// Usage: frida -U -f <package> -l scripts/bypass.js

Java.perform(function () {
    console.log("[ssl-bypass] Starting universal SSL pinning bypass...");

    // 1. TrustManagerImpl (Android 7+)
    try {
        var TrustManagerImpl = Java.use("com.android.org.conscrypt.TrustManagerImpl");
        TrustManagerImpl.checkTrustedRecursive.implementation = function () {
            console.log("[ssl-bypass] Bypassed TrustManagerImpl.checkTrustedRecursive");
            return Java.use("java.util.ArrayList").$new();
        };
    } catch (e) {
        console.log("[ssl-bypass] TrustManagerImpl not found, skipping");
    }

    // 2. OkHttp3 CertificatePinner
    try {
        var CertificatePinner = Java.use("okhttp3.CertificatePinner");
        CertificatePinner.check.overload("java.lang.String", "java.util.List").implementation = function (hostname, peerCertificates) {
            console.log("[ssl-bypass] Bypassed OkHttp3 CertificatePinner.check for " + hostname);
        };
    } catch (e) {
        console.log("[ssl-bypass] OkHttp3 CertificatePinner not found, skipping");
    }

    // 3. OkHttp3 CertificatePinner (older overload)
    try {
        var CertificatePinner2 = Java.use("okhttp3.CertificatePinner");
        CertificatePinner2.check.overload("java.lang.String", "[Ljava.security.cert.Certificate;").implementation = function (hostname, certs) {
            console.log("[ssl-bypass] Bypassed OkHttp3 CertificatePinner.check (array) for " + hostname);
        };
    } catch (e) {
        // This overload may not exist
    }

    // 4. SSLContext.init — replace TrustManagers with a permissive one
    try {
        var X509TrustManager = Java.use("javax.net.ssl.X509TrustManager");
        var SSLContext = Java.use("javax.net.ssl.SSLContext");

        var PermissiveTrustManager = Java.registerClass({
            name: "com.workers.PermissiveTrustManager",
            implements: [X509TrustManager],
            methods: {
                checkClientTrusted: function (chain, authType) {},
                checkServerTrusted: function (chain, authType) {},
                getAcceptedIssuers: function () {
                    return [];
                }
            }
        });

        SSLContext.init.overload(
            "[Ljavax.net.ssl.KeyManager;",
            "[Ljavax.net.ssl.TrustManager;",
            "java.security.SecureRandom"
        ).implementation = function (keyManagers, trustManagers, secureRandom) {
            console.log("[ssl-bypass] Bypassed SSLContext.init with permissive TrustManager");
            var permissive = Java.array("Ljavax.net.ssl.TrustManager;", [PermissiveTrustManager.$new()]);
            this.init(keyManagers, permissive, secureRandom);
        };
    } catch (e) {
        console.log("[ssl-bypass] SSLContext.init hook failed: " + e);
    }

    // 5. WebViewClient.onReceivedSslError — proceed on SSL errors
    try {
        var WebViewClient = Java.use("android.webkit.WebViewClient");
        WebViewClient.onReceivedSslError.implementation = function (view, handler, error) {
            console.log("[ssl-bypass] Bypassed WebViewClient SSL error, proceeding");
            handler.proceed();
        };
    } catch (e) {
        console.log("[ssl-bypass] WebViewClient hook not needed, skipping");
    }

    // 6. NetworkSecurityPolicy — allow cleartext traffic
    try {
        var NetworkSecurityPolicy = Java.use("android.security.NetworkSecurityPolicy");
        NetworkSecurityPolicy.isCleartextTrafficPermitted.overload().implementation = function () {
            console.log("[ssl-bypass] Allowing cleartext traffic");
            return true;
        };
        NetworkSecurityPolicy.isCleartextTrafficPermitted.overload("java.lang.String").implementation = function (hostname) {
            console.log("[ssl-bypass] Allowing cleartext traffic for " + hostname);
            return true;
        };
    } catch (e) {
        console.log("[ssl-bypass] NetworkSecurityPolicy hook not needed, skipping");
    }

    // 7. Conscrypt (modern Android TLS stack)
    try {
        var ConscryptPlatform = Java.use("org.conscrypt.Platform");
        ConscryptPlatform.checkServerTrusted.overload(
            "javax.net.ssl.X509TrustManager",
            "[Ljava.security.cert.X509Certificate;",
            "java.lang.String",
            "com.android.org.conscrypt.AbstractConscryptSocket"
        ).implementation = function (tm, chain, authType, socket) {
            console.log("[ssl-bypass] Bypassed Conscrypt Platform.checkServerTrusted");
        };
    } catch (e) {
        // Conscrypt internals vary by Android version
    }

    // 8. Apache HttpClient (legacy apps)
    try {
        var AbstractVerifier = Java.use("org.apache.http.conn.ssl.AbstractVerifier");
        AbstractVerifier.verify.overload("java.lang.String", "[Ljava.lang.String;", "[Ljava.lang.String;", "boolean").implementation = function () {
            console.log("[ssl-bypass] Bypassed Apache AbstractVerifier");
        };
    } catch (e) {
        // Not present in most modern apps
    }

    console.log("[ssl-bypass] All hooks installed. SSL pinning bypass active.");
});

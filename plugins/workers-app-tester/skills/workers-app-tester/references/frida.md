# Frida Reference

## Start frida-server

```bash
adb shell "su -c 'pgrep frida-server || /data/local/tmp/frida-server -D &'"
```

Verify:

```bash
frida-ps -U | head -5
```

List running apps:

```bash
frida-ps -Uia
```

## SSL Pinning Bypass

When HTTPS traffic is missing after the proxy is set, the app uses certificate pinning.

Bundled bypass (covers TrustManagerImpl, OkHttp3, SSLContext, WebViewClient, Conscrypt):

```bash
adb shell am force-stop <package>
frida -U -f <package> -l scripts/bypass.js```

When using `-f` (spawn mode), Frida launches the app. Do not also use `monkey`.

### Codeshare alternatives

Universal SSL unpinning:

```bash
frida --codeshare pcipolloni/universal-android-ssl-pinning-bypass-with-frida -U -f <package>
```

Masbog SSL unpinning:

```bash
frida --codeshare masbog/frida-android-unpinning-ssl -U -f <package>
```

Flutter apps (uses BoringSSL, normal hooks don't work):

```bash
frida --codeshare TheDauntless/disable-flutter-tls-v1 -U -f <package>
```

## Root Detection Bypass

If the app detects root and refuses to run:

```bash
frida --codeshare dzonerzy/fridantiroot -U -f <package>
```

Multiple bypass (root + SSL + debug):

```bash
frida --codeshare fdciabdul/frida-multiple-bypass -U -f <package>
```

## Hook a Specific Method

Watch what a method receives and returns:

```javascript
Java.perform(function () {
    var cls = Java.use("<full.class.name>");
    cls["<methodName>"].implementation = function () {
        console.log("args: " + JSON.stringify(arguments));
        var ret = this["<methodName>"].apply(this, arguments);
        console.log("return: " + ret);
        return ret;
    };
});
```

Save to `$SESSION_DIR/hook.js` and load:

```bash
frida -U -n <process> -l "$SESSION_DIR/hook.js"
```

## Load Multiple Scripts

```bash
frida -U -f <package> -l scripts/bypass.js -l "$SESSION_DIR/hook.js"```

## Frida with Custom Certificate

If the bypass script needs to load a specific cert (e.g. Burp):

```bash
openssl x509 -in burpsuite.cer -out cert-der.crt -outform DER
adb push cert-der.crt /data/local/tmp/
adb shell chmod 644 /data/local/tmp/cert-der.crt
```

Then in the Frida script, load it:

```javascript
var fileInputStream = FileInputStream.$new("/data/local/tmp/cert-der.crt");
var bufferedInputStream = BufferedInputStream.$new(fileInputStream);
```

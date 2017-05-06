
# DevTools.py

A set of automatically generated python bindings for the devtools protocol


# Example

Take a screenshot of a webpage
```
import base64, devtools

c = devtools.Client("localhost:9222")
c.page.navigate("http://www.shishnet.org")
b64data = c.page.captureScreenshot()['data']

open('screenshot.png', 'w').write(base64.b64decode(b64data))
```


# Build

```
$ git clone https://github.com/shish/devtools-py
$ make -C devtools-py
```


# Smoke Test

This should open chrome, then connect to it, and open shishnet.org in the new browser

```
$ /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=~/.chrome-test
$ python devtools-py/devtools.py
```


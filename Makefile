all: devtools.py

browser_protocol.json:
	wget https://raw.githubusercontent.com/ChromeDevTools/devtools-protocol/master/json/browser_protocol.json

devtools.py: gen-devtools.py browser_protocol.json
	python gen-devtools.py

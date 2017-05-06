#!/usr/bin/env python

import json

js = json.load(open("browser_protocol.json"))

def paramToPython(p):
    if p.get('optional'):
        return "%s=None" % (p['name'])
    else:
        return p['name']

def paramToDoc(p):
    return ":param {name} {type} - {doc}".format(
        name=p.get('name'),
        type=p.get('type', ""),
        doc=p.get('description')
    )

data = """
import json
import requests
import websocket

"""

data += """
class _DevToolsDomain(object):
    def __init__(self, instance):
        self.instance = instance
"""

for d in js['domains']:
    data += """
class _DevTools{domain}(_DevToolsDomain):
    def __init__(self, instance):
        _DevToolsDomain.__init__(self, instance)
        self.experimental = {experimental}
""".format(
    domain = d['domain'],
    experimental = repr(d.get('experimental', False))
)
    for c in d['commands']:
        params = c.get('parameters', [])
        data += """
    def {method}({args}):
        '''
        {doc}
        {paramDocs}
        '''
        return self.instance.send(method="{domain}.{method}", {sendArgs})
""".format(
            domain=d['domain'],
            method=c['name'],
            args=", ".join(['self'] + [paramToPython(p) for p in params]),
            doc=c.get('description'),
            paramDocs="\n        ".join([paramToDoc(p) for p in params]),
            sendArgs=", ".join(["%s=%s" % (p['name'], p['name']) for p in params]),
        )


data += """

class Client(object):
    def __init__(self, url, tab=-1):
        self._url = url  # FIXME
        self._tablist = requests.get("http://localhost:9222/json").json()
        for n, t in enumerate(self._tablist):
            print("Tab %d" % n)
            for k, v in t.items():
                print("- ", k, v)
        self._tab = websocket.create_connection(self._tablist[tab]['webSocketDebuggerUrl'])
        self._id = 0
        self._extraEvents = []

        self.version = "{version}"

        {domains}


    def send(self, method, **kwargs):
        print("send[%03d] %s(%r)" % (self._id, method, kwargs))
        self._tab.send(json.dumps({{
            "id": self._id,
            "method": method,
            "params": kwargs
        }}))

        retval = None
        while not retval:
            data = json.loads(self._tab.recv())
            print("recv[%03d] %s" % (data['id'], repr(data['result'])[:100]))
            if data['id'] == self._id:
                retval = data
            else:
                self._extraEvents.append(data)

        self._id += 1
        return retval['result']

    def recv(self):
        return json.loads(self._tab.recv())


if __name__ == "__main__":
    from base64 import b64decode

    c = Client("localhost:9222")
    c.page.navigate("http://www.shishnet.org")
    data = c.page.captureScreenshot()
    print(data['data'][:20])
    #data = b64decode(data['data'])
""".format(
    version = js['version']['major'] + "." + js['version']['minor'],
    domains="\n        ".join(["self.%s = _DevTools%s(self)" % (d['domain'].lower(), d['domain']) for d in js['domains']])
)

open('devtools.py', 'w').write(data)

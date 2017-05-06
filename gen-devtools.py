#!/usr/bin/env python

import json


def paramToPython(p):
    """
    >>> paramToPython(dict(name="foo"))
    'foo'
    >>> paramToPython(dict(name="foo", optional=True))
    'foo=None'
    >>> paramToPython(dict(name="foo", type="integer"))
    'foo: int'
    >>> paramToPython(dict(name="foo", type="integer", optional=True))
    'foo: int=None'
    """
    name = p['name']

    # Add type hint
    name += {
        "integer": ": int",
        "string": ": str",
        "number": ": float",
    }.get(p.get("type"), "")

    if p.get("optional"):
        name += "=None"

    return name


def paramToDoc(p):
    """
    >>> paramToDoc(dict(name="aParam", description="A parameter"))
    ':param aParam: A parameter'
    >>> paramToDoc(dict(name="aParam"))
    ':param aParam'
    """
    return ":param {name}{spc}{doc}".format(
        name=p.get("name"),
        spc=": " if "description" in p else "",
        doc=p.get("description", "")
    )


def domainToAttrName(domain):
    """
    >>> domainToAttrName("CSS")
    'css'
    >>> domainToAttrName("DOMDebugger")
    'domDebugger'
    >>> domainToAttrName("IndexedDB")
    'indexedDB'
    """
    ret = ""
    init = True
    for n, c in enumerate(domain):
        if n == 0:
            ret += c.lower()
        elif init and domain[n-1].isupper():
            if n+1 < len(domain) and domain[n+1].islower():
                ret += c
            else:
                ret += c.lower()
            if c.islower():
                init = False
        else:
            ret += c
    return ret


def genHeader():
    """
    >>> type(genHeader())
    <class 'str'>
    """
    data = """#!/usr/bin/env python

import json
import requests
import websocket


class _DevToolsDomain(object):
    def __init__(self, instance):
        self.instance = instance
"""
    return data


def genDomain(d):
    """
    >>> type(genDomain(dict(
    ...     domain='Test',
    ...     commands=[],
    ... )))
    <class 'str'>
    """
    # Domain Header
    data = """

class _DevTools{domain}(_DevToolsDomain):
    def __init__(self, instance):
        _DevToolsDomain.__init__(self, instance)
        self.experimental = {experimental}
""".format(
    domain=d['domain'],
    experimental=repr(d.get('experimental', False))
)

    # Commands
    for c in d['commands']:
        params = c.get('parameters', [])
        fullDoc = (
            '\n        """' +
            "\n        ".join(
                ["", c.get('description', '')] +
                [paramToDoc(p) for p in params]
            ) +
            '\n        """'
        )
        if fullDoc.strip('\n" ') == "":
            fullDoc = ""

        data += """
    def {method}({args}):{fullDoc}
        return self.instance.call(
            "{domain}.{method}",
            dict({sendArgs})
        )
""".format(
        domain=d['domain'],
        method=c['name'],
        args=", ".join(['self'] + [paramToPython(p) for p in params]),
        fullDoc=fullDoc,
        sendArgs=", ".join(["%s=%s" % (p['name'], p['name']) for p in params]),
    )

    return data


def genClient(js):
    """
    >>> type(genClient(dict(
    ...     version=dict(major="0", minor="1"),
    ...     domains=[],
    ... )))
    <class 'str'>
    """

    return """

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

    def call(self, method, args):
        print("send[%03d] %s(%r)" % (self._id, method, args))
        self._tab.send(json.dumps({{
            "id": self._id,
            "method": method,
            "params": args
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


def _selfTest():
    c = Client("localhost:9222")
    c.page.navigate("http://www.shishnet.org")
    data = c.page.captureScreenshot()
    print(data['data'][:60])
    # from base64 import b64decode
    # data = b64decode(data['data'])


if __name__ == "__main__":
    _selfTest()
""".format(
        version = js['version']['major'] + "." + js['version']['minor'],
        domains="\n        ".join([
            "self.%s = _DevTools%s(self)" % (domainToAttrName(d['domain']), d['domain'])
            for d
            in js['domains']
        ])
    )


def genFile(inFile, outFile):
    js = json.load(open(inFile))

    data = genHeader()
    for d in js['domains']:
        data += genDomain(d)
    data += genClient(js)

    open(outFile, 'w').write(data)


if __name__ == "__main__":
    genFile("browser_protocol.json", "devtools.py")

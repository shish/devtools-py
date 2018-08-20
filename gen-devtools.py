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
import websocket
import logging

log = logging.getLogger(__name__)


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

def _urlopen(url):
    try:
        from urllib import urlopen
    except ImportError:
        from urllib.request import urlopen
    return urlopen(url).read().decode('utf8')
    
    
class Client(object):
    def __init__(self, url, tab=-1):
        self._url = url  # FIXME
        self._tabList = json.loads(_urlopen("http://localhost:9222/json"))
        self._tabs = [
            websocket.create_connection(
                t['webSocketDebuggerUrl']
            ) for t in self._tabList
        ]
        self._tab = tab
        self._id = 0
        self._extraEvents = []
        if tab == -1:
            self.focus("")

        self.version = "{version}"

        {domains}
    
    def focus(self, tabName):
        for n, t in enumerate(self._tabList):
            if t['type'] == 'page' and tabName in t['title']:
                tab = n
                break
        else:
            print("Failed to focus on %s" % tabName)
            tab = 0
        self._tab = tab

    def call(self, method, args):
        for arg in list(args.keys()):
            if args[arg] is None:
                del args[arg]
        log.debug("send[%03d] %s(%r)" % (self._id, method, args))
        self._tabs[self._tab].send(json.dumps({{
            "id": self._id,
            "method": method,
            "params": args
        }}))

        retval = None
        while not retval:
            data = json.loads(self._tabs[self._tab].recv())
            log.debug("recv[%03d] %s" % (data['id'], repr(data)[:200]))
            if data['id'] == self._id:
                retval = data
            else:
                self._extraEvents.append(data)

        self._id += 1
        if 'error' in retval:
            raise Exception(retval['error'])
        return retval['result']


def _cli():
    c = Client("localhost:9222")

    for n, t in enumerate(c._tabList):
        print("Tab %d" % n)
        for k, v in t.items():
            print("- %s: %s" % (k, v))

    import code
    code.interact(
        local=c.__dict__,
        banner='''=== DevTools Interactive Mode ===
- Loaded modules: %s
- have fun!''' % ", ".join([m for m in c.__dict__.keys() if m[0] != '_'])
    )
    
    # c.page.navigate("http://www.shishnet.org")
    # data = c.page.captureScreenshot()
    # print(data['data'][:60])
    # from base64 import b64decode
    # data = b64decode(data['data'])


if __name__ == "__main__":
    _cli()
""".format(
        version=js['version']['major'] + "." + js['version']['minor'],
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

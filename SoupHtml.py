from bs4 import BeautifulSoup, NavigableString
from bs4.element import Comment
from distutils.util import strtobool
from ac_auto import *
import json, re, copy
import wordninja

DEBUG_TRACE = False

class SoupHTML:
    def __init__(self) -> None:
        self.MAX_MAIN_BLOCK_NUM = 2
        self.ignore_tags = set(["script", "noscript", "iframe", "img", "figure", "aside", "style", "button", "link", "svg", "nav", "meta", "select", "option"])
        self.good_tags = set(["main"])
        self.full_words = ["header", "head", "menu", "sider", "nav", "footer", "foot", "advertise", "hidden", "hide", "breadcrum"]
        self.words = ["menu", "sider", "nav", "footer", "foot", "advertise", "hidden", "hide", "breadcrum", "data-dismiss"]
        self.good_words = ["main-container", "main-content", "main_content", "main_container"]
        self.full_trie = Trie(self.full_words)
        self.trie = Trie(self.words)
        self.good_trie = Trie(self.good_words)
        self.ignore_patterns = re.compile("(^|[-_\|])ad[s]?([-_\|]|$)|(bread[-_]*crum)|(site[-_]*desc)|((?<!content[-_\s])sidebar(?![-_\s]enabled))|(site[-_]*head)|(language[-_]*list)|(cookie[-_]*banner)|(top[-_]*bar)|(display[:\s]*none)")
        self.short_reserve_attrs = set(["id", "type", "role"])
        self.reserve_attrs = set(["title", "datetime"])
        self.remove_attrs = set(["style"])
        self.keep_no_matter_len = ["video"]
        self.keep_no_matter_len_trie = Trie(self.keep_no_matter_len)

    def _trie_search(self, obj, trie = None):
        if not obj:
            return None
        if not trie:
            trie = self.trie
        if isinstance(obj, str):
            return trie.search(obj.lower())
        if isinstance(obj, list):
            return trie.search(("|".join(obj)).lower())

    def _pattern_search(self, obj):
        if not obj:
            return None
        if isinstance(obj, str):
            return self.ignore_patterns.search(obj.lower())
        if isinstance(obj, list):
            return self.ignore_patterns.search(("|".join(obj)).lower())

    def _check_ignore(self, obj):
        if obj.name in self.good_tags:
            return False
        attrs = [obj.name]
        for attr in obj.attrs:
            value = obj[attr]
            if isinstance(value, str):
                #attrs.append("%s|%s" % (attr, value))
                if len(value) > 50: #超过50个字长度的value暂时不拼接
                    continue
                attrs.append("%s" % (value))
            elif isinstance(value, list):
                #attrs.append("%s|%s" % (attr, "|".join(value)))
                attrs.append("%s" % ("|".join(value)))
        attrstr = "|".join(attrs)
        if self._trie_search(attrstr, self.good_trie):
            return False
        if self._trie_search(attrstr):
            if DEBUG_TRACE:
                print("%s :in: %s" % (self._trie_search(attrstr), attrstr))
            return True
        if self._pattern_search(attrstr):
            if DEBUG_TRACE:
                print("%s :in: %s" % (self._pattern_search(attrstr), attrstr))
            return True
        return False

    def _check_ariahidden(self, obj):
        if not obj:
            return None
        if isinstance(obj, str):
            objl = obj.lower()
            if objl == "false":
                return False
            if objl == "true" or objl == "hidden":
                return True
            return False
        if isinstance(obj, bool):
            return obj
        return None

    def decompose_recursive(self, obj):
        #print("------%s------%s" % (type(obj), str(obj)))
        if isinstance(obj, Comment):
            obj.extract()
            return
        if isinstance(obj, NavigableString):
            return
        if obj.children is None:
            return
        if self._check_ariahidden(obj.get("aria-hidden")) or \
            self._check_ariahidden(obj.get("aria-hiden")) or \
            self._check_ariahidden(obj.get("hidden")) or \
            self._check_ariahidden(obj.get("hiden")):
            if DEBUG_TRACE:
                print("%s||%s HIDDEN" % (obj.get("class"), obj.get("id")))
            obj.decompose()
            return
        if obj.name in self.ignore_tags:
            if DEBUG_TRACE:
                print("%s is ignore_tags" % (obj.name))
            obj.decompose()
        elif self._check_ignore(obj):
            obj.decompose()
        else:
            children = list(obj.children)
            for c in children:
                self.decompose_recursive(c)

    def check_if_string_words(self, s):
        if not s:
            return False
        slen = len(re.sub("[()\-_]", "", s))
        ss = wordninja.split(s)
        if len(ss) >= (slen / 2):
            return False
        return True

    def check_lens_empty(self, obj):
        if not obj:
            return True
        objname = obj.name
        if self._trie_search(objname, self.keep_no_matter_len_trie):
            return False
        if len(obj.get_text(strip=True)) < 2:
            return True
        return False


    def extract_empty(self, obj, pobj=None, pidx=None, pctyped=None):
        if isinstance(obj, NavigableString):
            return
        #当字符串长度小于2的时候丢弃该element
        if self.check_lens_empty(obj):
            obj.extract()
            return
        children = list(obj.children)
        ctyped = {idx:type(c) for idx, c in enumerate(children)}
        #用来删除文本中的超链接等tag包围, ctyped是当前obj的children，pctyped是当前obj并列的对象
        if pobj is not None and pidx is not None and pctyped is not None:
            pclen = len(pctyped)
            #表示当前obj的child就是一个string，同时跟当前obj平行的前后对象都是string
            #满足条件的事实上也是一个string了，结束后直接return
            if len(ctyped) == 1 and ctyped[0] == NavigableString:
                if (pidx == 0 and pidx + 1 < pclen and pctyped[pidx + 1] == NavigableString) or \
                    (pidx == pclen - 1 and pidx - 1 >= 0 and pctyped[pidx - 1] == NavigableString) or \
                    (pidx > 0 and pidx < pclen - 1 and pctyped[pidx - 1] == NavigableString \
                        and pctyped[pidx + 1] == NavigableString):
                    obj.extract()
                    pobj.insert(pidx, children[0])
                    return

        for idx, c in enumerate(children):
            self.extract_empty(c, obj, idx, ctyped)
        #过滤attributes
        attrs = [attr for attr in obj.attrs]
        for attr in attrs:
            value = obj.get(attr)
            if attr == "class":
                #检查class value的长度和是否是正常单词组合而不是随机字符串
                if value and len(value[0]) <= 15 and self.check_if_string_words(value[0]):
                    obj[attr] = [value[0]]
                else:
                    del obj[attr]
            elif attr == "href":
                obj[attr] = ""
            elif attr == "id":
                if len(value) > 15 or not self.check_if_string_words(value):
                    del obj[attr]
            elif attr in self.short_reserve_attrs:
                if len(value) > 15:
                    del obj[attr]
            elif attr in self.reserve_attrs:
                continue
            elif attr in self.remove_attrs:
                del obj[attr]
            else:
                del obj[attr]



    def slim(self, html_str):
        html_str = re.sub("[ \n\r\t]+", " ", html_str)
        soup = BeautifulSoup(html_str, "html.parser")
        if soup.body is None:
            return
        #第一层粗筛
        deflag = False
        children = list(soup.body.children)
        #for c in soup.body.children:
        for c in children:
            if isinstance(c, Comment):
                c.extract()
                continue
            if isinstance(c, NavigableString):
                continue
            if deflag:
                c.decompose()
                continue
            cname = str(c.name).lower()
            if cname in self.good_tags:
                continue
            if cname == "footer":
                c.decompose()
                deflag = True
                continue
            if cname in self.ignore_tags or cname == "header":
                c.decompose()
                continue
            if self._trie_search(c.get("class"), self.full_trie) or \
                self._trie_search(c.get("id"), self.full_trie):
                if DEBUG_TRACE:
                    if self._trie_search(c.get("class"), self.full_trie):
                        print("%s |in| %s" % (self._trie_search(c.get("class"), self.full_trie), c.get("class")))
                    if self._trie_search(c.get("id"), self.full_trie):
                        print("%s |in| %s" % (self._trie_search(c.get("id"), self.full_trie), c.get("id")))
                c.decompose()
                continue
        #第一层挑选正文块
        mainbs = []
        cidx = 0
        for c in soup.body.children:
            cidx += 1
            if isinstance(c, NavigableString):
                continue
            if self._check_ignore(c):
                continue
            clen = len(str(c))
            if len(mainbs) < self.MAX_MAIN_BLOCK_NUM or clen > mainbs[0][0]:
                if len(mainbs) >= self.MAX_MAIN_BLOCK_NUM:
                    mainbs.pop(0)
                mainbs.append((clen, cidx, c))
                mainbs = sorted(mainbs, key=lambda x:x[0]) #按长度正序，最短的在第一个
        #递归过滤无用的内容
        for b in mainbs:
            self.decompose_recursive(b[-1])
        new_mainbs = []
        for b in mainbs:
            if self.check_lens_empty(b[-1]): #根节点开始即无内容的，extract方法不能去除
                continue
            self.extract_empty(b[-1])
            new_mainbs.append(b)
        if not new_mainbs:
            return
        mainbs = [(len(str(b[2])), b[1], b[2]) for b in new_mainbs]
        mainbs = sorted(mainbs, key=lambda x:x[0])
        threslen = mainbs[-1][0] * 0.1
        smallcount = len([b for b in mainbs[:-1] if b[0] <= threslen])
        for i in range(smallcount):
            mainbs.pop(0)
        mainbs = sorted(mainbs, key=lambda x:x[1]) #按实际顺序排序
        return [b[-1] for b in mainbs if b[-1] is not None]

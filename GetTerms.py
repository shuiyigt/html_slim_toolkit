import json, sys, re
from collections import defaultdict
from bs4 import BeautifulSoup, NavigableString
from bs4.element import Comment

SHORT_TERMS = True

fname = sys.argv[1]
fout = sys.argv[2]
if not SHORT_TERMS:
    fw = open("items_test_%s" % fout, "w+")
else:
    fw = open("items_test_short_%s" % fout, "w+")

objnames = defaultdict(int)

k_attrs = ["href", "title", "datetime"]
kv_attrs = ["id", "class", "role", "type"]
keep_ss = set(["ad"])

def get_attrs(obj):
    tmpwords = []
    objattrs = set(obj.attrs)
    for attr in k_attrs:
        if attr not in objattrs:
            continue
        tmpwords.append(attr)
    for attr in kv_attrs:
        if attr not in objattrs:
            continue
        val = obj[attr]
        if isinstance(val, list):
            val = " ".join(val)
        val = val.strip()
        if not val:
            continue
        tmpwords.append(attr)
        #value里切分后长度为1的放弃
        ss = [word for word in re.split("[-_\s]+", val) if (len(word) > 2 or (word.lower() in keep_ss))]
        if not SHORT_TERMS:
            tmpwords.extend(ss)
        else:
            tmpwords.append(" ".join(ss))
    return [word for word in tmpwords if len(word.strip()) > 0]

def words_append(words, obj, just_tags=False):
    if isinstance(obj, Comment):
        return
    if isinstance(obj, NavigableString):
        if not just_tags:
            ss = [w for w in re.split("[\s]+", obj) if len(w.strip()) > 0]
            if len(ss) > 0:
                words.append("<|>")
            if not SHORT_TERMS:
                words.extend(ss)
            else:
                words.append(" ".join(ss))
        return
    objname = obj.name
    if not just_tags:
        objnames[objname] += 1

    words.append("<%s" % objname)
    attrs = get_attrs(obj)
    words.extend(attrs)
    #words.append("<|>")

    for c in obj.children:
        words_append(words, c, just_tags)

def html2words(html_str, just_tags=False):
    soup = BeautifulSoup(html_str, "html.parser")
    words = []
    for c in soup.children:
        words_append(words, c, just_tags)
    return [word for word in words if len(word.strip()) > 0]


lensum = []
lensum2 = []
urlset = set()
for line in open(fname):
    jo = json.loads(line)
    url, htmls = jo["url"], jo["htmls"]
    if url in urlset:
        continue
    urlset.add(url)

    outs = []
    tag_outs = []
    for html in htmls:
        outs.extend(html2words(html))
        tag_outs.extend(html2words(html, True))
    olen = len(outs)
    tolen = len(tag_outs)
    lensum.append(olen)
    lensum2.append(tolen)
    del jo["htmls"]
    jo["full_len"] = olen
    jo["tag_len"] = tolen
    jo["full_words"] = outs
    jo["tag_words"] = tag_outs
    fw.write("%s\r\n" % json.dumps(jo, ensure_ascii=False))

avg = sum(lensum) / len(lensum)
print("avg_len:%s\nlen:%s" % (avg, len(lensum)))
avg2 = sum(lensum2) / len(lensum2)
print("avg_len:%s\nlen:%s" % (avg2, len(lensum2)))

fwname = open("tag_names_%s" % fout, "w+")
snames = sorted(objnames.items(), key=lambda x:x[1], reverse=True)
for name, count in snames:
    fwname.write("%s\t%s\n" % (name, count))
from collections import defaultdict

class TrieNode(object):
    def __init__(self, value=None):
        # 值
        self.value = value
        # fail指针
        self.fail = None
        # 尾标志：标志为i表示第i个模式串串尾，默认为0
        self.tail = 0
        # 子节点，{value:TrieNode}
        self.children = {}


class Trie(object):
    def __init__(self, words):
        #print("初始化")
        # 根节点
        self.root = TrieNode()
        # 模式串个数
        self.count = 0
        self.words = words
        for word in words:
            self.insert(word)
        self.ac_automation()
        #print("初始化完毕")

    def insert(self, sequence):
        """
        基操，插入一个字符串
        :param sequence: 字符串
        :return:
        """
        self.count += 1
        cur_node = self.root
        for item in sequence:
            if item not in cur_node.children:
                # 插入结点
                child = TrieNode(value=item)
                cur_node.children[item] = child
                cur_node = child
            else:
                cur_node = cur_node.children[item]
        cur_node.tail = self.count

    def ac_automation(self):
        """
        构建失败路径
        :return:
        """
        queue = [self.root]
        # BFS遍历字典树
        while len(queue):
            temp_node = queue[0]
            # 取出队首元素
            queue.remove(temp_node)
            for value in temp_node.children.values():
                # 根的子结点fail指向根自己
                if temp_node == self.root:
                    value.fail = self.root
                else:
                    # 转到fail指针
                    p = temp_node.fail
                    while p:
                        # 若结点值在该结点的子结点中，则将fail指向该结点的对应子结点
                        if value.value in p.children:
                            value.fail = p.children[value.value]
                            break
                        # 转到fail指针继续回溯
                        p = p.fail
                    # 若为None，表示当前结点值在之前都没出现过，则其fail指向根结点
                    if not p:
                        value.fail = self.root
                # 将当前结点的所有子结点加到队列中
                queue.append(value)

    def search(self, text):
        """
        模式匹配
        :param self:
        :param text: 长文本
        :return:
        """
        p = self.root
        # 记录匹配起始位置下标
        start_index = 0
        # 成功匹配结果集
        rst = defaultdict(list)
        for i in range(len(text)):
            single_char = text[i]
            while single_char not in p.children and p is not self.root:
                p = p.fail
            # 有一点瑕疵，原因在于匹配子串的时候，若字符串中部分字符由两个匹配词组成，此时后一个词的前缀下标不会更新
            # 这是由于KMP算法本身导致的，目前与下文循环寻找所有匹配词存在冲突
            # 但是问题不大，因为其标记的位置均为匹配成功的字符
            if single_char in p.children and p is self.root:
                start_index = i
            # 若找到匹配成功的字符结点，则指向那个结点，否则指向根结点
            if single_char in p.children:
                p = p.children[single_char]
            else:
                start_index = i
                p = self.root
            temp = p
            while temp is not self.root:
                # 尾标志为0不处理，但是tail需要-1从而与敏感词字典下标一致
                # 循环原因在于，有些词本身只是另一个词的后缀，也需要辨识出来
                if temp.tail:
                    rst[self.words[temp.tail - 1]].append((start_index, i))
                temp = temp.fail
        #修改20220526，解决匹配bug
        outrst = defaultdict(list)
        only_check_set = set()
        for key, tups in rst.items():
            klen = len(key)
            for start, end in tups:
                real_key = text[start:end+1]
                okey = "%s_%s_%s" % (real_key, start, end)
                if okey not in only_check_set:
                    outrst[real_key].append((start, end))
                    only_check_set.add(okey)
                if end - start + 1 != klen and text[end-klen+1:end+1] == key:
                    okey = "%s_%s_%s" % (key, end-klen+1, end)
                    if okey not in only_check_set:
                        outrst[key].append((end-klen+1, end))
                        only_check_set.add(okey)
        return outrst


if __name__ == "__main__":
    test_words = ["中国", "很行"]
    test_text = "中国银行很行"
    model = Trie(test_words)
    # defaultdict(<class 'list'>, {'中国': [(0, 1)], '很行': [(4, 5)]})
    print(len(model.search(test_text)))
    print(len(model.search("hello")))
    print(str(model.search(test_text)))
    res = model.search(test_text)
    for k, v in res.items():
        print(k, v)

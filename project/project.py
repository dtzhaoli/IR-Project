#coding=utf-8
import os
import struct


class DicItem:
    def __init__(self):
        self.token = ""       # 词项内容
        self.df = 0           # 文档频率
        self.index = list()   # 倒排索引


def token(str):            # 将文档词条化
    str = str.replace("<speaker>"," ")
    str = str.replace("</speaker>", " ")
    str = str.replace("<title>", " ")
    str = str.replace("</title>", " ")
    str = str.replace("\n", "")

    # 将非数字或字母的字符替换为空格
    str = list(str)
    for i in range(len(str)):
        if not str[i].isalnum():
            str[i] = " "
    str = "".join(str)
    strList = str.split()

    #去除纯数字词项
    strListTemp = strList
    strList = list()
    for i in range(len(strListTemp)):
        if not strListTemp[i].isdigit():
            strList.append(strListTemp[i])

    return strList


def GammaEncode(num):       # 将单个数字用gamma编码，转换成字符串
    offset = bin(num)[3:]
    length = len(offset)
    result = ""
    for i in range(length):
        result += "1"
    result += "0"
    result += offset

    return result


def Gammadecode(gammastr):     # 将一串01Gamma串解码成int型list
    result = list()
    offsetlen = 0
    i = 0
    while i < len(gammastr):
        if gammastr[i] == '1':
            offsetlen += 1
            i += 1
        else:
            if offsetlen == 0:
                result.append(1)
                i += 1
            else:
                i += 1
                result.append(int('1'+gammastr[i:i+offsetlen], 2))
                i += offsetlen
            offsetlen = 0
    result[0] -= 1                # 因为编码的时候首位会+1，所以解码时要减去
    return result


def ConstructIndex( filein ):   # 读取文件，构建倒排索引并合并

    global DOCNO           # 使用全局词项表
    global dic             # 使用全局词典和索引
    global countofwords    # 使用全局词条总数

    f = open(filein)
    for line in f:
        # 去掉<DOC>和</DOC>
        if "<DOC>" in line:
            continue
        if "</DOC>" in line:
            continue

        # 处理<DOCNO>
        if "<DOCNO>" in line:
            line = line.replace("<DOCNO>", "")
            line = line.replace("</DOCNO>", "")
            line = line.replace("\n", "")
            DOCNO.append(line)
            continue

        tokenlist = token(line)
        countofwords += len(tokenlist)
        for i in range(len(tokenlist)):
            for j in range(len(dic)):
                if tokenlist[i] == dic[j].token:
                    if (dic[j].index)[len(dic[j].index) - 1] != len(DOCNO) - 1:
                        dic[j].index.append(len(DOCNO) - 1)
                        dic[j].df += 1
                    break
            else:
                dicitem = DicItem()
                dicitem.token = tokenlist[i]
                dicitem.df = 1
                dicitem.index.append(len(DOCNO) - 1)
                dic.append(dicitem)
    f.close()


def SaveIndex(fileout):         # 压缩并保存倒排索引到磁盘

    global DOCNO               # 使用全局词项表
    global dic                 # 使用全局词典和索引
    global countofwords        # 使用全局词条总数

    f = open(fileout, "wb")

    # 写入词条总数
    f.write(str(countofwords) + "\n")

    # 写入文档id和对应的DOCNO
    f.write(str(len(DOCNO)) + "\n")
    for i in range(len(DOCNO)):
        f.write(str(DOCNO[i]) + "\n")

    # 写入字典和倒排索引
    # 单一字符串压缩，写入字典字符串
    for i in range(len(dic)):
        f.write(dic[i].token)
    f.write("\n")

    # 写入每个词项的在单一字符串中的起始位置，df，倒排索引
    p = 0     # 表示在单一字符串中的位置
    f.write(str(len(dic)) + "\n")
    for i in range(len(dic)):
        f.write(str(p)+" ")            # 在单一字符串中的起始位置
        p += len(dic[i].token)
        f.write(str(p)+" ")            # 在单一字符串中的结束位置
        f.write(str(dic[i].df)+"\n")   # 词项的df

        # 写入词项的倒排索引
        # 将索引转换为gamma编码
        gammastr = ""
        gammastr += GammaEncode(dic[i].index[0]+1)     # gamma编码的第一个数+1
        for j in range(1, dic[i].df):
            gammastr += GammaEncode( dic[i].index[j] - dic[i].index[j-1] )
        # f.write(dic[i].token + " " +gammastr)
        # 将gamma编码以二进制流的形式写入
        f.write(struct.pack('I', len(gammastr)))       # 先写入字符串的长度，为了读取方便
        for j in range(0, len(gammastr), 8):
            if j + 8 < len(gammastr):
                f.write(struct.pack('B', int(gammastr[j:j + 8], 2)))
            else:
                f.write(struct.pack('B', int(gammastr[j:], 2)))
        f.write("\n")

    f.close()


def ReadIndex(fileindex):         # 从磁盘读取倒排索引并解压

    global DOCNO  # 使用全局词项表
    global dic  # 使用全局词典和索引
    global countofwords  # 使用全局词条总数

    DOCNO = list()
    dic = list()

    f = open(fileindex,"rb")

    # 读入词条总数
    countofwords = int(f.readline())

    # 读入文档DOCNO和对应的文档id
    DocNum = int(f.readline())
    for i in range(DocNum):
        docno = f.readline().replace("\n", "")
        DOCNO.append(docno)

    # 读入单一字符串
    dicStr = f.readline().replace("\n", "")

    # 读入字典和倒排索引
    DicNum = int(f.readline())
    for i in range(DicNum):

        dicitem = DicItem()

        token_df_list = f.readline().replace("\n", "").split()
        for j in range(int(token_df_list[0]), int(token_df_list[1])):
            dicitem.token += dicStr[j]
        dicitem.df = int(token_df_list[2])

        # 读取二进制流索引并还原成01字符串，然而Gamma解码
        gammalen = struct.unpack('I', f.read(4))[0]
        gammastr = ""
        for j in range(0, gammalen, 8):
            tempstr = bin(struct.unpack('B', f.read(1))[0])[2:]
            # 补全“0”，以为转成二进制流的时候按Byte切分，丢失了每个Byte中前面的“0”
            if j + 8 < gammalen:
                tempstr = "0"*(8 - len(tempstr)) + tempstr
                gammastr += tempstr
            else:
                tempstr = "0" * ((gammalen % 8) - len(tempstr)) + tempstr
                gammastr += tempstr
        result = Gammadecode(gammastr)
        # print result

        # 将间隔转换成文档id
        dicitem.index.append(result[0])
        for j in range(1, len(result)):
            dicitem.index.append(dicitem.index[j-1]+result[j])
        f.readline()
        # print dicitem.index
        dic.append(dicitem)

    f.close()
    # for i in range(len(dic)):
    #     print dic[i].token, dic[i].df, dic[i].index


def Search(word):         # 在倒排索引中查询关键字并在命令行中打印出倒排记录表

    global DOCNO  # 使用全局词项表
    global dic    # 使用全局词典和索引

    for i in range(len(dic)):
        if dic[i].token == word:
            print "the records of " + word + " :"
            for j in range(dic[i].df):
                print DOCNO[dic[i].index[j]]
            break
    else:
        print "no record of " + word


def Information():        # 输出语料统计信息

    print "the number of tokens : " + str(len(dic))
    print "the number of docs : " + str(len(DOCNO))
    print "the number of words : " + str(countofwords)
    print "the average word of doc : " + str(countofwords/len(DOCNO))


# 主程序
DOCNO = list()     # 词项表，list的位置和内容分别为词项的id和词项的内容
dic = list()       # 词典
countofwords = 0   # 语料词条总数
HaveIndex = 0      # 0表示未读入倒排索引，1表示已读入倒排索引

while 1:

    command = raw_input("Please input the command：")
    com = command.split()

    if com[0] == "ConstructIndex" and len(com) >= 3:

        # 因为构建多个文件的索引，所以要在主程序总将内存中的索引清空
        DOCNO = list()      # 清空词项表
        dic = list()        # 清空词典和倒排索引
        countofwords = 0    # 清空词条总数

        for i in range(1, len(com) - 1):
            if not os.path.exists(com[i]):
                print "file " + com[i] + " does not exists"
                break
            else:
                ConstructIndex(com[i])    # 如果文件存在则构建倒排索引并合并
        else:
            SaveIndex(com[len(com)-1])
            HaveIndex = 1                     # 构建索引之后默认读入索引
            print "Construct Index Successfully"

        continue

    if com[0] == "ReadIndex" and len(com) == 2:

        if os.path.exists(com[1]):
            ReadIndex(com[1])    # 如果文件存在则读取索引并解压
            HaveIndex = 1            # 表示当前已经读入了索引
            print "Read Index Successfully"
        else:
            print "file " + com[1] + " does not exists"

        continue

    if com[0] == "Search" and len(com) == 2:

        if HaveIndex == 0:
            print "there is no index in memory"
        else:
            Search(com[1])

        continue

    if com[0] == "Information" and len(com) == 1:

        if HaveIndex == 0:
            print "there is no index in memory"
        else:
           Information()

        continue

    print "Wrong Command"



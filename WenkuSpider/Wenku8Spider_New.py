#encoding = gbk
import sys
import re
import bs4
import os
from multiprocessing.dummy import Pool as ThreadPool
from multiprocessing import Pool
import threading
import time
import random
import requests
import time
import argparse
import shutil

#设置编码
reload(sys)
sys.setdefaultencoding("gbk")
#设置完成

#Wenku8Spider 小说抓取工具 By Lyt99
#以小说目录页面为准抓取信息
#测试环境:Python 2.7 64bit
#多线程有点(各种)小问题，不过线程数量调少点儿或者某些玄学因素就能正常了
#如果还是不行，那就用隔壁的单线程版本(WenkuSpider_Old.py)

time.clock()

#正则表达式
#小说目录页面
matchpattern_title = r'<td class="vcss" colspan="4">(.+)</td>'#标题(用于判断)
matchpattern_chapter = '<td class=\"ccss\"><a href=\"(\d{0,}).htm\">(.+)</a></td>'#章节(用于判断)
matchpattern_pic = '<img src=\"(http://pic.wenku8.com/pictures/.+?)\" border=\"0\" class=\"imagecontent\">'#图片 获取图片地址
matchpattern_bookname = '<a href="http://www.wenku8.com/book/.+\.htm">(.+?)</a>';#书名 获取书名
matchpattern_picture = '<div class="divimage"><a href="http://pic.wenku8.com/pictures/\d+/\d+/\d+/(\d+.jpg)".+?</a></div>'#插图
matchpattern_clear = '<.+>.+</.+>|</div>|<div id="content">|<br/>'#章节多余的html标签
matchpattern_chapterindex = '<a href="(http://www.wenku8.com/novel/\d+/\d+/index.htm)">.+?</a>'#从小说主页面到小说目录页面的链接
matchpattern_url = r'^http://.+?'#这个还要介绍么……
#小说列表页面
matchpattern_articlelist_pagecount = '<em id=\"pagestats\">\d{0,}/(\d{0,})</em>'
matchpattern_articlelist_book = '<a href="http://www\.wenku8\.com/book/(\d{0,})\.htm" title="(.+)"'
#其它正则
matchpattern_without = "[\\/:*?\"<>|]+"
#其它定义
user_agents = ['Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.19 (KHTML, like Gecko) Ubuntu/11.10 Chromium/18.0.1025.168 Chrome/18.0.1025.168 Safari/535.19','Mozilla/5.0 (Windows NT 5.1; rv:5.0.1) Gecko/20100101 Firefox/5.0.1','Mozilla/5.0 (Windows NT 6.1; rv:2.0b7pre) Gecko/20100921 Firefox/4.0b7pre','Opera/9.80 (Windows NT 6.2; Win64; x64) Presto/2.12.388 Version/12.15','Mozilla/5.0 (Linux; U; Android 4.1.2; en-us; SCH-I535 Build/JZO54K) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30','Mozilla/5.0 (Windows NT 5.1; rv:13.0) Gecko/20100101 Firefox/13.0.1','Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; .NET CLR 1.1.4322)','Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; MRA 5.8 (build 4157); .NET CLR 2.0.50727; AskTbPTV/5.11.3.15590)','Mozilla/5.0 (Windows NT 5.1; rv:21.0) Gecko/20100101 Firefox/21.0','Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; .NET CLR 1.1.4322)'] #User-Agnet列表，随机选择使用
articleurl = 'http://www.wenku8.com/modules/article/articlelist.php';#所有小说目录，附加数据:page
searchurl  = 'http://www.wenku8.com/modules/article/search.php' #搜索
mainurl = 'http://www.wenku8.com/'#主站页面

global pics
pics = []

#Utils

def printmessage(prefix, content):
    sys.stdout.flush()
    print u'[%s]%s\n' % (prefix,content),
    sys.stdout.flush()

def makedir(path):
    if os.path.exists(path):
        return
    else:
        os.makedirs(path);

def getcontent(url, params = {}):#传入url和encode好的data，访问并返回内容
    ua = user_agents[random.randint(0,len(user_agents) - 1)]
    
    s = requests.Session()
    header = {'User-Agent' : ua}

    tried = 0
    while(1):
        try:
            r = s.get(url, params = params, headers = header, timeout = 10)
            break
        except requests.RequestException:
            tried += 1
            if tried >= 3:
                printmessage(u'错误', u'访问 %s 失败' % url)
                break
        except:
            return
    if tried >= 3:
        return ''

    if url.find('.jpg'):
        return r.content
    r.encoding = 'gbk'
    return r.text
    
def writetofile(param):#写到文件，支持直接内容或者url
    #url(content) path 0,1
    sys.stdout.flush()#刷新缓冲区
    #print u'开始下载 %s' % param[1]

    basepath = os.path.dirname(param[1])
    makedir(basepath)

    if re.match(matchpattern_url, param[0]):
        content = getcontent(param[0])
        type = 'wb'
    else:
        content = param[0]
        type = 'wt'
    with open(param[1],type) as f:
        f.write(content)

    #print u'[提示 - 写文件]%s 下载完成\n' % param[1],

    sys.stdout.flush()#刷新缓冲区

def removechar(string):
    #占位
    return re.sub(matchpattern_without, '', string)

#抓取相关
def getbookname(content):#获取小说名称
    #占位
    return re.search(matchpattern_bookname,content).group(1)

def getbookindex(content):#获取小说目录，返回['卷名',[('id','章1'), ('id', '章2'), ...], ...]类推
    #因为懒所以直接从旧的抄过来
    bs = bs4.BeautifulSoup(content,'html.parser',from_encoding = 'gbk')
    
    result = bs.find_all('td');

    reg_title = re.compile(matchpattern_title)
    reg_chapter = re.compile(matchpattern_chapter)

    novellist = list()
    curchapter = list()
    chaptername = str()

    #print result

    for k in range(len(result)):
        st = result[k].encode('gbk')
        reg = re.match(reg_title, st)
        if reg:#为卷名
            if chaptername != '':
                novellist.append([chaptername, curchapter])
            chaptername = reg.group(1)
            curchapter = []
        else:
            reg = re.match(reg_chapter,st)
            if reg:
                curchapter.append((reg.group(1),reg.group(2)))

    novellist.append([chaptername, curchapter])

    return novellist

def getchaptercontent(url):#返回处理完成的内容(tuple)，为章节内容和插图列表
    content = getcontent(url)
    if content != None:
        bs = bs4.BeautifulSoup(content,'html.parser')
    else:
        return None
    
    #获取小说内容(其中有一些HTML标签)
    con = bs.find(id='content').encode('gbk')

    #获取插图
    ipic = bs.find_all('img','imagecontent')
    pic = []
    if len(ipic) != 0:
        for p in ipic:
            pic.append(p.get('src'))


    #处理获取到的内容
    con = re.sub('&#160;',' ', con)#替换空格
    con = re.sub('&#8231;','·', con)#特别要命的玩意儿
    con = re.sub(matchpattern_picture, '\n\n   插图[\g<1>]\n\n', con)#替换插图并保留提示
    con = re.sub(matchpattern_clear, '', con)#清除多余的html标签

    return (con,pic)

def getbookurlbyname(name):#通过站内搜索确定小说，返回小说目录页面的url
    data = {'searchtype' : 'articlename', 'searchkey' : name}#访问页面时的数据
    content = getcontent(searchurl, data)
    if content == None:
        return None;

    match = re.findall(matchpattern_chapterindex, content)
    if len(match) == 0:#没有搜索到
        return None
    else:
        return match[0]

def getbookurlbyid(id):#通过小说id来获取url
    base = 'http://www.wenku8.com/novel/%s/%s/index.htm'
    if (id > 0) and (id < 1000): #1-999 dirid为0
        return base % ('0', id)
    if (id >= 1000) and (id <= 1950):#截止到2015.8.20
        return base % ('1', id)
    print 'search'
    for i in range(1,11):#遍历2-10
        r = requests.get(base % (str(i), id))
        if r.status_code == 200:
            return base % (str(i), id)
    return None

def getbookidbyurl(url):#通过小说url获取id
    #日常占位
    return url.split('/')[-2]
  
#包装
def downloadchaptercontent(arg):#path = basepath + bookname + '\'|param(id, chaptername)|url = 小说章节页面所在目录
    

    url = arg[0]
    param = arg[1]
    path = arg[2]
    
    con = getchaptercontent('%s.htm' % (url + param[0]))
    writetofile((con[0], path + '%s - %s.txt' % (param[0], removechar(param[1]))))#先把小说内容下载下来
    for i in con[1]:#插图
        pics.append((i, path + '%s - %s\%s' % (param[0], removechar(param[1]), os.path.basename(i))))


    print u'[提示 - 章节]下载 %s 开始\n' % param[1],

    
def downloadbookcontent(url, path):#下载整本小说 url:小说目录 path:basepath
    #sys.stdout.flush()

    if ENABLE_SORT:
        printmessage(u'提示', u'启用卷名排序')

    printmessage(u'提示', u'使用 %s 线程进行下载' % str(THREADS))
    content = getcontent(url)
    bookname = getbookname(content)
    bookIndex = getbookindex(content)
    baseurl = os.path.dirname(url) + '/'
    id = getbookidbyurl(url)
    sort = 0;

    bookpath = "%s - %s\\" % (path + id, removechar(bookname))
    
    if os.path.exists(bookpath):#如果存在目录先删除
        printmessage(u'提示', u'删除原文件夹 %s' % bookpath)
        shutil.rmtree(bookpath)

    #print u'[提示 - 整书]开始下载 %s\n' % bookname,
    printmessage(u'提示',u'开始下载小说 %s' % bookname)

    downloadlist = list()
    for book in bookIndex:#book[0]:卷名 book[1]:章节list
        sort += 1
        for chapter in book[1]:
            #(baseurl, chapter, r'%s - %s\%s\\' % (path + id, bookname, book[0]))
            if ENABLE_SORT:
                bookp = '%s - %s' % (str(sort),removechar(book[0]))
            else:
                bookp = removechar(book[0])
            ele = (baseurl, chapter, '%s\\' % (bookpath + bookp))
            downloadlist.append(ele)

    td = ThreadPool(THREADS)

    td.map_async(downloadchaptercontent, downloadlist);

    td.close()

    while threading.active_count() - 1:
        time.sleep(1)

    #独立下载插图。采用5线程。减少连接数。
    printmessage('提示 - 插图','下载 插图 中…')
    tp = ThreadPool(5)
    tp.map_async(writetofile, pic)
    tp.close()
    while threading.active_count() - 1:
        time.sleep(1)

    printmessage(u'提示 - 整书',u'下载 %s 结束, 耗时 %s 秒' % (bookname, str(time.clock())))
    #sys.stdout.flush()


def main():
    print u'轻小说文库(wenku8.com)小说爬虫 V1.1 By Lyt99\n\n',

    parser = argparse.ArgumentParser()

    global THREADS
    global ENABLE_SORT

    parser.add_argument('searchpattern', help = u'轻小说ID/名称', type = str)
    parser.add_argument('-bn', '--bookname',help = u'使用小说名称搜索', action='store_true')
    parser.add_argument('-t', '--threads', help = u'线程数，默认为3', type = int)
    #parser.add_argument('--log', help = u'在小说目录下生成下载log', action = 'store_true')
    parser.add_argument('-d', '--dir', help = u'小说下载到的目录，默认使用运行目录下的novel目录', type = str)
    parser.add_argument('-s', '--sort', help = u'卷文件夹名中加入数字进行排序，以保证在资源管理器中的顺序', action = 'store_true')
    args = parser.parse_args()



    if args.bookname:#小说名称搜索
        url = getbookurlbyname(args.searchpattern)
        if url == None:
            printmessage(u'错误', u'未查找到小说 %s，可能不存在或者有多个对应选项' % args.Book)
            sys.exit(0)
    else:#小说id
        if args.searchpattern.isdigit():
            url = getbookurlbyid(int(args.searchpattern))
            if url == None:
                printmessage(u'错误', u'ID为 %s 的小说没有找到' % args.searchpattern)
                sys.exit(0)
        else:
            printmessage(u'错误', u'请输入正确格式的小说ID')
            sys.exit(0)

    ENABLE_SORT = args.sort#排序

    if args.dir:#下载目录
        dir = os.path.abspath(args.dir) + '\\'
    else:
        dir = os.path.abspath('novel') + '\\'

    if args.threads:
        THREADS = args.threads
    else:
        THREADS = 3

    downloadbookcontent(url,dir)





if __name__ == '__main__':
    main()

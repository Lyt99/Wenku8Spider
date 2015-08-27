#encoding = gbk
import sys
import re
import bs4
import os
from multiprocessing.dummy import Pool as ThreadPool
import threading
import time
import random
import requests
import time
import argparse

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

#其它定义
user_agents = [ 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'] #User-Agnet列表，随机选择使用
articleurl = 'http://www.wenku8.com/modules/article/articlelist.php';#所有小说目录，附加数据:page
searchurl  = 'http://www.wenku8.com/modules/article/search.php' #搜索
mainurl = 'http://www.wenku8.com/'#主站页面


#(伪)全局变量
threads = 3 #每个操作的线程数
enable_sort = False



#Utils

def printMessage(prefix, content):
    sys.stdout.flush()
    print u'[%s]%s\n' % (prefix,content),
    sys.stdout.flush()

def makedir(path):
    if os.path.exists(path):
        return
    else:
        os.makedirs(path);

def getContent(url, params = {}):#传入url和encode好的data，访问并返回内容
    ua = user_agents[random.randint(0,len(user_agents) - 1)]
    
    s = requests.Session()
    header = {'User-Agent' : ua}

    r = s.get(url, params = params, headers = header)
    if url.find('.jpg'):
        return r.content
    r.encoding = 'gbk'
    return r.text
    
def writeToFile(param):#写到文件，支持直接内容或者url
    #url(content) path 0,1
    sys.stdout.flush()#刷新缓冲区
    #print u'开始下载 %s' % param[1]

    basepath = os.path.dirname(param[1])
    makedir(basepath)

    if re.match(matchpattern_url, param[0]):
        content = getContent(param[0])
        type = 'wb'
    else:
        content = param[0]
        type = 'wt'
    with open(param[1],type) as f:
        f.write(content)

    #print u'[提示 - 写文件]%s 下载完成\n' % param[1],

    sys.stdout.flush()#刷新缓冲区


#抓取相关
def getBookName(content):#获取小说名称
    #占位
    return re.search(matchpattern_bookname,content).group(1)

def getBookIndex(content):#获取小说目录，返回['卷名',[('id','章1'), ('id', '章2'), ...], ...]类推
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

def getChapterContent(url):#返回处理完成的内容(tuple)，为章节内容和插图列表
    content = getContent(url)
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

def getBookUrlByName(name):#通过站内搜索确定小说，返回小说目录页面的url
    data = {'searchtype' : 'articlename', 'searchkey' : name}#访问页面时的数据
    content = getContent(searchurl, data)
    if content == None:
        return None;

    match = re.findall(matchpattern_chapterindex, content)
    if len(match) == 0:#没有搜索到
        return None
    else:
        return match[0]

def getBookUrlById(id):#通过小说id来获取url
    base = 'http://www.wenku8.com/novel/%s/%s/index.htm'
    if id > 0 & id < 1000: #1-999 dirid为1
        return base % ('0', id)
    if id >= 1000 & id <= 1950:#截止到2015.8.20
        return base % ('1', id)
    for i in range(1,11):#遍历2-10
        r = requests.get(base % (str(i), id))
        if r.status_code == 200:
            return base % (str(i), id)
    return None

def getBookIdByUrl(url):#通过小说url获取id
    #日常占位
    return url.split('/')[-2]
  
#包装
def downloadChapterContent(arg):#path = basepath + bookname + '\'|param(id, chaptername)|url = 小说章节页面所在目录
    

    url = arg[0]
    param = arg[1]
    path = arg[2]
    
    con = getChapterContent('%s.htm' % (url + param[0]))
    download = list()
    writeToFile((con[0], path + '%s - %s.txt' % (param[0], param[1])))
    for i in con[1]:#插图
        download.append((i, path + '%s - %s\%s' % (param[0], param[1], os.path.basename(i))))


    print u'[提示 - 章节]下载 %s 开始\n' % param[1],

    tp = ThreadPool(threads)

    tp.map_async(writeToFile, download)

    tp.close()

    
def downloadBookContent(url, path):#下载整本小说 url:小说目录 path:basepath
    #sys.stdout.flush()

    content = getContent(url)
    bookname = getBookName(content)
    bookIndex = getBookIndex(content)
    baseurl = os.path.dirname(url) + '/'
    id = getBookIdByUrl(url)
    sort = 0;

    #print u'[提示 - 整书]开始下载 %s\n' % bookname,
    printMessage(u'提示',u'开始下载小说 %s' % bookname)

    downloadlist = list()
    for book in bookIndex:#book[0]:卷名 book[1]:章节list
        sort += 1
        for chapter in book[1]:
            #(baseurl, chapter, r'%s - %s\%s\\' % (path + id, bookname, book[0]))
            if enable_sort:
                bookp = '%s - %s' % (str(sort),book[0])
            else:
                bookp = book[0]
            ele = (baseurl, chapter, r'%s - %s\%s\\' % (path + id, bookname,bookp))
            downloadlist.append(ele)

    td = ThreadPool(threads)

    td.map_async(downloadChapterContent, downloadlist);

    td.close()

    while threading.active_count() - 1:
        time.sleep(1)

    print u'[提示 - 整书]下载 %s 结束, 耗时 %s 秒\n' % (bookname, str(time.clock()))
    #sys.stdout.flush()


def main():
    print u'轻小说文库(wenku8.com)小说爬虫 V1.1 By Lyt99\n\n',

    parser = argparse.ArgumentParser()

    parser.add_argument('searchpattern', help = u'轻小说ID/名称', type = str)
    parser.add_argument('-bn', '--bookname',help = u'使用小说名称搜索', action='store_true')
    parser.add_argument('-t', '--threads', help = u'线程数，默认为3', type = int)
    #parser.add_argument('--log', help = u'在小说目录下生成下载log', action = 'store_true')
    parser.add_argument('-d', '--dir', help = u'小说下载到的目录，默认使用运行目录下的novel目录', type = str)
    parser.add_argument('-s', '--sort', help = u'卷文件夹名中加入数字进行排序，以保证在资源管理器中的顺序', action = 'store_true')
    args = parser.parse_args()

    if args.threads:
        threads = args.threads
    else:
        threads = 3

    printMessage(u'提示', u'使用 %s 线程进行下载' % str(threads))

    if args.bookname:#小说名称搜索
        url = getBookUrlByName(args.searchpattern)
        if url == None:
            printMessage(u'错误', u'未查找到小说 %s，可能不存在或者有多个对应选项' % args.Book)
            sys.exit(0)
    else:#小说id
        if args.searchpattern.isdigit():
            url = getBookUrlById(args.searchpattern)
            if url == None:
                printMessage(u'错误', u'ID为 %s 的小说没有找到' % args.searchpattern)
                sys.exit(0)
        else:
            printMessage(u'错误', u'请输入正确格式的小说ID')
            sys.exit(0)

    sort = args.sort#排序

    if args.dir:#下载目录
        dir = os.path.abspath(args.dir) + '\\'
    else:
        dir = os.path.abspath('novel') + '\\'

    downloadBookContent(url,dir)





if __name__ == '__main__':
    main()

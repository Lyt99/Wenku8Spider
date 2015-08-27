# encoding=gbk
import urllib2
import urllib
import re
import sys
import Queue
import bs4
import os

#这是一个单线程的早期版本

#定义们
matchpattern_title = r'<td class="vcss" colspan="4">(.+)</td>'
matchpattern_chapter = '<td class=\"ccss\"><a href=\"(\d{0,}).htm\">(.+)</a></td>'
matchpattern_pic = '<img src=\"(http://pic.wenku8.com/pictures/.+?)\" border=\"0\" class=\"imagecontent\">'
matchpattern_bookname = '<a href="http://www.wenku8.com/book/.+\.htm">(.+?)</a>';
repagenum = '<em id=\"pagestats\">\d{0,}/(\d{0,})</em>'
reg = '<a href="http://www\.wenku8\.com/book/(\d{0,})\.htm" title="(.+)"'
data = {'page' : '1'}
header = { 'User-Agnet' : 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'} #custom user-agent
articleurl = 'http://www.wenku8.com/modules/article/articlelist.php';


print u"Wenku Spider by Lyt99 Wenku8轻小说爬虫 0.1"

def makedir(path):
    if os.path.exists(path) == False:
        os.makedirs(path)

#获取书籍名称
def getBookName(content):
    return re.findall(matchpattern_bookname,content)[0]

#获取章节列表(我觉得我大概用不上BeautifulSoup...)
def ChaptersGet(content):
    u"[-]获取章节列表"
    '''request = urllib2.Request(url,None,header)
    try:
        response = urllib2.urlopen(request)
        content = response.read()
    except urllib2.URLError, e:
        print(u"[错误]打开页面" + url + u"时发生错误: " + e.reason)
        sys.exit()
    '''
    bs = bs4.BeautifulSoup(content,'html.parser')
    
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
                curchapter.append([reg.group(1),reg.group(2)])

    novellist.append([chaptername, curchapter])

    return novellist


#获取章节内容
def GetChapterContent(url, chaptername, path, withpicture):
    request = urllib2.Request(url,None,header)
    try:
        response = urllib2.urlopen(request)
        content = response.read()
    except urllib2.URLError, e:
        print(u"[错误]打开页面" + url + u"时发生错误: " + e.reason)
        sys.exit()
        
    bs = bs4.BeautifulSoup(content,'html.parser')

    obj = bs.find(id="content")

    content = obj.encode('gbk')


    #处理插图
    ipic = bs.find_all('img','imagecontent')

    #print ipic

    if (len(ipic) != 0) & withpicture:#有插图
        makedir(path + chaptername)#创建文件夹存放插图
        for i in ipic:
            while(True):
                tried = 1;
                try:
                    piccontent = urllib2.urlopen(i.get('src'),None,5)
                    break
                except:
                    if tried >= 4:
                        print "[错误]下载失败!"
                    tried += 1
                    continue

            picname = i.get('src').split('/')[-1]
            print u'    正在下载插图%s' % picname
            with open(path + chaptername + '\\' + picname, 'wb') as f:
                 f.write(piccontent.read())
    
    content = content.replace('&#160;',' ') #替换空格
    content = re.sub('<div class="divimage"><a href="http://pic.wenku8.com/pictures/\d+/\d+/\d+/(\d+.jpg)".+?</a></div>', '\n插图[\g<1>]\n', content) #替换掉插图
    content = re.sub(r'<.+>.+</.+>|</div>|<div id="content">|<br/>','', content)#替换首尾和换行符

    return content

#下载内容到硬盘
def DownloadNovel(novelid, path = None, withpicture = True,threads = 0):
    if path == None:
        path = os.path.split(os.path.realpath(sys.argv[0]))[0] + '\\'


    dirid = -1

    print(u'[-]获取小说下载地址')
    #1 - 999在0文件夹，1000 - 1942(截至8.10是最新的)在1文件夹，然并卵还是遍历好了

    for id in range(0,10): #其实是0-9
        try:
            request = urllib2.Request('http://www.wenku8.com/novel/%s/%s/index.htm' % (str(id), novelid), None, header)

            #print 'http://www.wenku8.com/novel/%s/%s/index.htm' % (str(id), novelid)

            response = urllib2.urlopen(request)
            content = response.read()

            dirid = id
            break
        except urllib2.URLError, e:
            if str.find(str(e.reason), 'Not Found') != -1:
                continue;
            print '[错误]网页连接失败!'
            sys.exit(1)

    uurl = 'http://www.wenku8.com/novel/%s/%s/' % (str(dirid), novelid)

    if dirid == -1:
        print "下载地址获取失败！"
        sys.exit(0)

    novelname = getBookName(content)
    print(u'[-]准备下载 ' + novelname.decode('gbk'))

    novelpath  = path + '%s - %s\\' % (novelid, novelname.decode('gbk'))
    makedir(novelpath) #创建目录

    print u'[-]获取章节目录'

    cpt = ChaptersGet(content) #章节

    print u'[-]开始下载章节'
    
    #print cpt


    for c in cpt:
        makedir(novelpath + c[0].decode('gbk'))#创建卷文件夹 c[0]是章节名,c[1]是存在的章节列表
        print u'[%s]正在下载 %s' % (novelid, c[0].decode('gbk'))
        for i in c[1]:#章节下载，i[0]是章节id，i[1]是章节名称
            print u'[%s]正在下载 %s' % (novelid, i[1].decode('gbk'))
            path = novelpath +  c[0].decode('gbk') + '\\' + i[0] + '-' + i[1].decode('gbk') + '.txt'
            if os.path.exists(path):
                print u'[%s]已存在，跳过' % novelid
                continue
            with open(path,'wt') as f:
               con = GetChapterContent(uurl + i[0] + '.htm',i[0] + '-' + i[1].decode('gbk'), novelpath + c[0].decode('gbk') + '\\', withpicture);
               #print con
               f.write(con)

#遍历模式
def DownloadAll():
    data = urllib.urlencode(data)
    request = urllib2.Request(articleurl, data, header)

    try:
        response = urllib2.urlopen(request)
    except urllib2.URLError, e:
       print u"[错误]加载目录网页失败: " + e.reason
       sys.exit(0);

    content = response.read()


    se = re.search(repagenum,content)
    #print content

    if se:
       page = int(se.group(1))
    else:
       print u'[错误]获取页面数量失败'
       sys.exit(0);

    print u"获取小说页面数量:" + str(page) + u"，开始获取小说"

    #获取小说

    novelqueue = Queue.Queue()


    novelreg = re.compile(reg)

    try:
       for cur in range(1,page + 1):
           print u"正在读取第 " + str(cur) + u" 页内容"
           if cur != 1:
               data = {'page' : str(cur) }
               data = urllib.urlencode(data);
               request = urllib2.Request(articleurl, data, header)
               response = urllib2.urlopen(request)
               content = response.read()
           novelresult = re.findall(novelreg,content)
           for novel in novelresult:
               novelqueue.put(novel)
    except urllib2.URLError, e:
        print u'[错误]网页(目录第' + str(k) + u')加载失败：' + e.reason

    print u'已加载' + str(page) + u'页，共 ' + str(novelqueue.qsize()) + u" 本小说"


def main():
    novelid = raw_input("请输入小说ID:")
    if novelid.isdigit():
        DownloadNovel(novelid,r'I:\\novel\\',True)
    else:
        print "参数错误!"

main()
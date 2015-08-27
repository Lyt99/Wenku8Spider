# encoding=gbk
import urllib2
import urllib
import re
import sys
import Queue
import bs4
import os

#����һ�����̵߳����ڰ汾

#������
matchpattern_title = r'<td class="vcss" colspan="4">(.+)</td>'
matchpattern_chapter = '<td class=\"ccss\"><a href=\"(\d{0,}).htm\">(.+)</a></td>'
matchpattern_pic = '<img src=\"(http://pic.wenku8.com/pictures/.+?)\" border=\"0\" class=\"imagecontent\">'
matchpattern_bookname = '<a href="http://www.wenku8.com/book/.+\.htm">(.+?)</a>';
repagenum = '<em id=\"pagestats\">\d{0,}/(\d{0,})</em>'
reg = '<a href="http://www\.wenku8\.com/book/(\d{0,})\.htm" title="(.+)"'
data = {'page' : '1'}
header = { 'User-Agnet' : 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'} #custom user-agent
articleurl = 'http://www.wenku8.com/modules/article/articlelist.php';


print u"Wenku8 Spider by Lyt99 Wenku8��С˵���� 0.1"

def makedir(path):
    if os.path.exists(path) == False:
        os.makedirs(path)

#��ȡ�鼮����
def getBookName(content):
    return re.findall(matchpattern_bookname,content)[0]

#��ȡ�½��б�(�Ҿ����Ҵ���ò���BeautifulSoup...)
def ChaptersGet(content):
    u"[-]��ȡ�½��б�"
    '''request = urllib2.Request(url,None,header)
    try:
        response = urllib2.urlopen(request)
        content = response.read()
    except urllib2.URLError, e:
        print(u"[����]��ҳ��" + url + u"ʱ��������: " + e.reason)
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
        if reg:#Ϊ����
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


#��ȡ�½�����
def GetChapterContent(url, chaptername, path, withpicture):
    request = urllib2.Request(url,None,header)
    try:
        response = urllib2.urlopen(request)
        content = response.read()
    except urllib2.URLError, e:
        print(u"[����]��ҳ��" + url + u"ʱ��������: " + e.reason)
        sys.exit()
        
    bs = bs4.BeautifulSoup(content,'html.parser')

    obj = bs.find(id="content")

    content = obj.encode('gbk')


    #�����ͼ
    ipic = bs.find_all('img','imagecontent')

    #print ipic

    if (len(ipic) != 0) & withpicture:#�в�ͼ
        makedir(path + chaptername)#�����ļ��д�Ų�ͼ
        for i in ipic:
            while(True):
                tried = 1;
                try:
                    piccontent = urllib2.urlopen(i.get('src'),None,5)
                    break
                except:
                    if tried >= 4:
                        print "[����]����ʧ��!"
                    tried += 1
                    continue

            picname = i.get('src').split('/')[-1]
            print u'    �������ز�ͼ%s' % picname
            with open(path + chaptername + '\\' + picname, 'wb') as f:
                 f.write(piccontent.read())
    
    content = content.replace('&#160;',' ') #�滻�ո�
    content = re.sub('<div class="divimage"><a href="http://pic.wenku8.com/pictures/\d+/\d+/\d+/(\d+.jpg)".+?</a></div>', '\n��ͼ[\g<1>]\n', content) #�滻����ͼ
    content = re.sub(r'<.+>.+</.+>|</div>|<div id="content">|<br/>','', content)#�滻��β�ͻ��з�

    return content

#�������ݵ�Ӳ��
def DownloadNovel(novelid, path = None, withpicture = True,threads = 0):
    if path == None:
        path = os.path.split(os.path.realpath(sys.argv[0]))[0] + '\\'


    dirid = -1

    print(u'[-]��ȡС˵���ص�ַ')
    #1 - 999��0�ļ��У�1000 - 1942(����8.10�����µ�)��1�ļ��У�Ȼ���ѻ��Ǳ�������

    for id in range(0,10): #��ʵ��0-9
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
            print '[����]��ҳ����ʧ��!'
            sys.exit(1)

    uurl = 'http://www.wenku8.com/novel/%s/%s/' % (str(dirid), novelid)

    if dirid == -1:
        print "���ص�ַ��ȡʧ�ܣ�"
        sys.exit(0)

    novelname = getBookName(content)
    print(u'[-]׼������ ' + novelname.decode('gbk'))

    novelpath  = path + '%s - %s\\' % (novelid, novelname.decode('gbk'))
    makedir(novelpath) #����Ŀ¼

    print u'[-]��ȡ�½�Ŀ¼'

    cpt = ChaptersGet(content) #�½�

    print u'[-]��ʼ�����½�'
    
    #print cpt


    for c in cpt:
        makedir(novelpath + c[0].decode('gbk'))#�������ļ��� c[0]���½���,c[1]�Ǵ��ڵ��½��б�
        print u'[%s]�������� %s' % (novelid, c[0].decode('gbk'))
        for i in c[1]:#�½����أ�i[0]���½�id��i[1]���½�����
            print u'[%s]�������� %s' % (novelid, i[1].decode('gbk'))
            path = novelpath +  c[0].decode('gbk') + '\\' + i[0] + '-' + i[1].decode('gbk') + '.txt'
            if os.path.exists(path):
                print u'[%s]�Ѵ��ڣ�����' % novelid
                continue
            with open(path,'wt') as f:
               con = GetChapterContent(uurl + i[0] + '.htm',i[0] + '-' + i[1].decode('gbk'), novelpath + c[0].decode('gbk') + '\\', withpicture);
               #print con
               f.write(con)

#����ģʽ
def DownloadAll():
    data = urllib.urlencode(data)
    request = urllib2.Request(articleurl, data, header)

    try:
        response = urllib2.urlopen(request)
    except urllib2.URLError, e:
       print u"[����]����Ŀ¼��ҳʧ��: " + e.reason
       sys.exit(0);

    content = response.read()


    se = re.search(repagenum,content)
    #print content

    if se:
       page = int(se.group(1))
    else:
       print u'[����]��ȡҳ������ʧ��'
       sys.exit(0);

    print u"��ȡС˵ҳ������:" + str(page) + u"����ʼ��ȡС˵"

    #��ȡС˵

    novelqueue = Queue.Queue()


    novelreg = re.compile(reg)

    try:
       for cur in range(1,page + 1):
           print u"���ڶ�ȡ�� " + str(cur) + u" ҳ����"
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
        print u'[����]��ҳ(Ŀ¼��' + str(k) + u')����ʧ�ܣ�' + e.reason

    print u'�Ѽ���' + str(page) + u'ҳ���� ' + str(novelqueue.qsize()) + u" ��С˵"


def main():
    novelid = raw_input("������С˵ID:")
    if novelid.isdigit():
        DownloadNovel(novelid,r'I:\\novel\\',True)
    else:
        print "��������!"

main()
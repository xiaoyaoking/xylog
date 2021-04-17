#encoding=utf8
# pip install Flask gevent requests
# by 职业菜鸟 2021/04/15 QQ:2252432154
# ver：2.0  支持主从，多端同步

# Flask
import sys,os,math,json,re,time,datetime,requests,shutil
import urllib

try:
    from flask import Flask,abort, redirect, url_for ,make_response , request
    from flask import Flask, render_template
    from threading import Thread

    # gevent
    from gevent import monkey
    from gevent.pywsgi import WSGIServer
    monkey.patch_all()
    # gevent end
except Exception,e:
    print 'import flask err:' + str(e)

reload(sys)
sys.setdefaultencoding('utf8')

app = Flask(__name__,template_folder='tpl',static_folder='static')
app.config.update(DEBUG=True)

def log(message=''):
    _print = True
    logpath = 'log'
    nowTime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 现在时间
    logfile = logpath +"/"+ datetime.datetime.now().strftime('%Y-%m-%d')
    txt = '%(asctime)s -: %(message)s\n' % {'asctime': nowTime,'message': message}
    if _print:
        print txt
    if not os.path.exists(logpath):  ###判断文件是否存在，返回布尔值
        os.makedirs(logpath)
    logfile = logfile + '.log'
    with open(logfile, 'a+') as f:
        f.write(txt)
def read_file(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
                file_body = f.read()
        return file_body
    else:
        log('read_file err:'+filepath)
        return None
def setJsonFile(filepath,jsonobj):
    with open(filepath,"w") as f:
        json.dump(jsonobj,f)
def read_file_json(filepath,noNone = False):
    read_txt = read_file(filepath)
    if not read_txt is None:
        return json.loads(read_txt)
    else:
        if noNone:
            return {}
        else:
            return None
xyconfig = read_file_json('xylog.json')
spider_list = xyconfig.get('spiders',[])
apiurl = xyconfig.get('apiurl','')
logpath = xyconfig.get('logpath','')
web_route = xyconfig.get('route','xylog')
run_type = xyconfig.get('type',0)
loglist  = xyconfig.get('loglist',[])
cutlogcmd = xyconfig.get('cutlogcmd','nginx -s reload')

if logpath[-1] != '/':
    logpath = logpath + '/'

def get_log_files():#获取日志列表
    allfile=[]
    for dirpath,dirnames,filenames in os.walk(logpath):
        for name in filenames:
            if name.find('access')<0 and name != 'nginx_error.log' and name.endswith(".log"):
                allfile.append(os.path.join(dirpath, name))
    allfile = list(set(allfile))
    allfile.sort(reverse=True)
    return allfile
@app.route('/'+web_route+'/', methods=['GET','POST'])
def show():
    logdata = ''
    fields = []
    for spider_item in spider_list:
        fields.append("{field:'"+spider_item.get('id','')+"', title: '"+spider_item.get('name','')+"',width:100, sort: true}")
    fieldstr = ','.join(fields)
    jsonlist = os.listdir('json/')
    jsonlist.sort(reverse=True)
    for jsonname in jsonlist:
        myname = jsonname[0:-5]
        logdata += '<option value="'+myname+'">'+myname+'</option>'
    context = {'fieldstr':fieldstr,"logdata":logdata}
    return render_template('show.html',**context)
@app.route('/'+web_route+'/data', methods=['GET','POST'])
def data():
    site = request.args.get("site",'0')
    days = int(request.args.get("day",7))
    logdata = ''
    spiders = []
    newdatalist = []
    for spider_item in spider_list:
        spiders.append(spider_item.get('name',''))
        newdatalist.append({'name': spider_item.get('name',''),'type': 'line','data': [],})
    datas = []
    datas_arr = os.listdir('json/')
    datas_arr.sort(reverse=True)
    datas_i = 0
    for datas_val in datas_arr:
        if datas_i < (days+1):
            jsonarr = read_file_json('json/'+datas_val)
            for json_item in jsonarr:
                if site == json_item['site']:
                    for spider_i,spider_item in enumerate(spider_list):
                        newdatalist[spider_i]['data'].append(json_item[spider_item.get('id','')])
            datas.append(datas_val[0:-5])
        else:
            break
        datas_i += 1
    datas.reverse()
    for spider_i,spider_item in enumerate(spider_list):
        newdatalist[spider_i]['data'].reverse()
    context = {'site':site,'spiders':json.dumps(spiders),'datas':json.dumps(datas),'datalist':json.dumps(newdatalist)}
    return render_template('data.html',**context)
@app.route('/'+web_route+'/ajax', methods=['GET','POST'])
def ajax():
    logdata = request.args.get("logdata",'0')
    if logdata == '0':
        logdata = str(datetime.datetime.now().strftime('%Y-%m-%d'))
    jsonlogpath = 'json/'+logdata+'.json'
    retval = read_file_json(jsonlogpath)
    mtime = os.stat(jsonlogpath).st_mtime
    logtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))

    if type(retval)==str:
        retval = '"'+retval+'"'
    if type(retval)==dict or type(retval)==list:
        retval = json.dumps(retval)
    return '{"code":0,"data":'+retval+',"time":"'+logtime+'"}' 
@app.route('/'+web_route+'/api', methods=['GET','POST'])
def get_api():
    action = request.args.get("action","get")
    if action=='putlog':    #提交log
        new_logs_list = []
        new_logs_str = request.form.get("logs","")
        if new_logs_str != '':
            new_logs_str = urllib.unquote(new_logs_str)
            new_logs_list = json.loads(new_logs_str)
        #准备合并日志
        logdata = str(datetime.datetime.now().strftime('%Y-%m-%d'))
        jsonlogpath = 'json/'+logdata+'.json'
        now_logs_list = read_file_json(jsonlogpath)
        if now_logs_list is None:
            now_logs_list = []
        now_logs_list_dict = {}
        new_logs_list_dict = {}
        for now_logs in now_logs_list: #重组本地日志格式方便替换
            site_name = now_logs.get('site')
            now_logs_list_dict[site_name]=now_logs
        for new_logs in new_logs_list: #合并日志
            site_name = new_logs.get('site')
            now_logs_list_dict[site_name]=new_logs
        #恢复日志原来格式
        new_logs = []
        for k,now_logs in now_logs_list_dict.items():
            new_logs.append(now_logs)
        setJsonFile(jsonlogpath,new_logs)
        return '{"code":1}'
    if action=='getspiders':   #获取蜘蛛
        return json.dumps(spider_list)

def get_log_info(): #获取日志统计信息
    tongji = []
    logfilelist = os.listdir(logpath) 
    for logfile in logfilelist:
        if logfile.find('access')<0 and logfile != 'nginx_error.log' and logfile.endswith(".log"):
            sitename = logfile[:-4]
            if sitename in loglist: #过滤日志
                logstr = read_file(logpath+logfile)
                if not logstr is None:
                    tongji_item = {'site':sitename}
                    spider_c = []
                    for spider_item in spider_list:
                        key_c = 0
                        keys = spider_item.get('key','')
                        if isinstance(keys, list):
                            for key_v in keys:
                                key_c += logstr.count(key_v)
                        else:
                            key_c = logstr.count(spider_item.get('key',''))
                        tongji_item[spider_item.get('id','')]=key_c
                    tongji.append(tongji_item)
    return tongji

def auto_get_spiders():#自动获取主服务器的蜘蛛列表
    global spider_list
    while True:
        try:
            getspiders = requests.get(apiurl+'/api?action=getspiders').json()
            if len(getspiders)>0:
                spider_list = getspiders
        except Exception,e:
            log('auto_get_spiders err:' + str(e))
        time.sleep(60)  

def auto_cut_log():#自动切割日志
    nowdate = str(datetime.datetime.now().strftime('%Y-%m-%d'))
    log( 'auto_cut_log nowdate:'+nowdate)
    while True:
        try:
            newdate = str(datetime.datetime.now().strftime('%Y-%m-%d'))
            #log( 'auto_cut_log newdate:'+newdate)
            if newdate != nowdate:  #当日期改变的时候切割日志
                log( 'auto_cut_log nowdate:'+nowdate+' newdate:'+newdate)
                for logfile in loglist:
                    logpath_bak = logpath + logfile + '_bak.log'
                    logpath_now = logpath + logfile + '.log'
                    if os.path.exists(logpath_bak):
                        os.remove(logpath_bak) #移除前一天的日志备份
                    shutil.move(logpath_now,logpath_bak) #将当前日志移动到备份文件
                    os.system(cutlogcmd)                 #移动文件后执行得命令，因为已经被程序打开得句柄不会关闭还会读写移动后得文件要重载一下
                nowdate = newdate
        except Exception,e:
            log( 'auto_cut_log err:' + str(e))
        time.sleep(60)  #默认一分钟执行一次
def auto_log(): #自动统计日志
    while True:
        try:
            time.sleep(5)
            log( 'auto_log run')
            tongji = get_log_info()
            if len(tongji)>0:
                filename = 'json/' + str(datetime.datetime.now().strftime('%Y-%m-%d')) + '.json'
                setJsonFile(filename,tongji)
                if run_type == 2: #从日志 才更新蜘蛛
                    log( 'auto_log put log:'+str(len(tongji)))
                    payload = {"logs":urllib.quote(json.dumps(tongji))} 
                    log(requests.post(apiurl+'/api?action=putlog',data=payload).text)
            log( 'auto_log end')
        except Exception,e:
            log( 'auto_log err:' + str(e))
        time.sleep(xyconfig.get('uptime',5)*60)
if __name__ == "__main__":
    log( 'xylog run')
    if run_type == 2: #从日志 才更新蜘蛛
        Thread(target=auto_cut_log, args=()).start() #定时切割日志
        Thread(target=auto_get_spiders, args=()).start() #定时更新蜘蛛列表
    if run_type == 3: #单主机模式 
        Thread(target=auto_cut_log, args=()).start() #定时切割日志
    if run_type == 2 or run_type == 3:
        Thread(target=auto_log, args=()).start() #定时更新
    if run_type == 1 or run_type == 3: #为主日志服务器或单主机模式时才开启web服务
        http_server = WSGIServer(('0.0.0.0', xyconfig.get('port',8181)), app)
        http_server.serve_forever()



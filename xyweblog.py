#encoding=utf8
# pip install Flask gevent 
# by 职业菜鸟 2020/03/10 QQ:2252432154

# Flask
import sys,os,math,json,re,time,datetime
from flask import Flask,abort, redirect, url_for ,make_response , request
from flask import Flask, render_template
from threading import Thread

# gevent
from gevent import monkey
from gevent.pywsgi import WSGIServer
monkey.patch_all()
# gevent end

reload(sys)
sys.setdefaultencoding('utf8')

app = Flask(__name__,template_folder='tpl',static_folder='static')
app.config.update(DEBUG=True)

def read_file(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
                file_body = f.read()
        return file_body
    else:
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
def get_log_files():
    allfile=[]
    for dirpath,dirnames,filenames in os.walk(xyconfig.get('logpath','')):
        for name in filenames:
            if name.find('access')<0 and name != 'nginx_error.log' and name.endswith(".log"):
                allfile.append(os.path.join(dirpath, name))
    allfile = list(set(allfile))
    allfile.sort(reverse=True)
    return allfile

xyconfig = read_file_json('logconfig.json')
    
@app.route('/'+xyconfig.get('route','show'), methods=['GET','POST'])
def show():
    spider_arr =  xyconfig.get('spiders',[])
    logdata = ''
    fields = []
    for spider_item in spider_arr:
        fields.append("{field:'"+spider_item.get('id','')+"', title: '"+spider_item.get('name','')+"',width:100}")
    fieldstr = ','.join(fields)
    jsonlist = os.listdir('json/')
    jsonlist.sort(reverse=True)
    for jsonname in jsonlist:
        myname = jsonname[0:-5]
        logdata += '<option value="'+myname+'">'+myname+'</option>'
    context = {'fieldstr':fieldstr,"logdata":logdata}
    return render_template('show.html',**context)
@app.route('/'+xyconfig.get('route','show')+'data', methods=['GET','POST'])
def data():
    site = request.args.get("site",'0')
    days = int(request.args.get("day",7))
    spider_arr =  xyconfig.get('spiders',[])
    logdata = ''
    spiders = []
    newdatalist = []
    for spider_item in spider_arr:
        spiders.append(spider_item.get('name',''))
        newdatalist.append({'name': spider_item.get('name',''),'type': 'line','data': [],})
    datas = []
    datas_arr = os.listdir('json/')
    datas_arr.sort(reverse=True)
    datas_i = 0
    for datas_val in datas_arr:
        if datas_i < (days+1):
            jsonstr = read_file('json/'+datas_val)
            jsonarr = json.loads(jsonstr)
            for json_item in jsonarr:
                if site == json_item['site']:
                    for spider_i,spider_item in enumerate(spider_arr):
                        newdatalist[spider_i]['data'].append(json_item[spider_item.get('id','')])
            datas.append(datas_val[0:-5])
        else:
            break
        datas_i += 1
    datas.reverse()
    for spider_i,spider_item in enumerate(spider_arr):
        newdatalist[spider_i]['data'].reverse()
    context = {'site':site,'spiders':json.dumps(spiders),'datas':json.dumps(datas),'datalist':json.dumps(newdatalist)}
    return render_template('data.html',**context)
@app.route('/'+xyconfig.get('route','show')+'ajax', methods=['GET','POST'])
def ajax():
    logdata = request.args.get("logdata",'0')
    if logdata == '0':
        logdata = str(datetime.datetime.now().strftime('%Y-%m-%d'))
    logpath = 'json/'+logdata+'.json'
    retval = read_file(logpath)
    retval = json.loads(retval)

    mtime = os.stat(logpath).st_mtime
    logtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))

    if type(retval)==str:
        retval = '"'+retval+'"'
    if type(retval)==dict or type(retval)==list:
        retval = json.dumps(retval)

    return '{"code":0,"data":'+retval+',"time":"'+logtime+'"}' 

def get_log_info():
    tongji = []
    logfilelist = os.listdir(xyconfig.get('logpath','')) 
    for logfile in logfilelist:
        if logfile.find('access')<0 and logfile != 'nginx_error.log' and logfile.endswith(".log"):
            sitename = logfile[:-4]
            logstr = read_file(xyconfig.get('logpath','')+logfile)
            if not logstr is None:
                tongji_item = {'site':sitename}
                spider_arr =  xyconfig.get('spiders',[])
                spider_c = []
                for spider_item in spider_arr:
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

def auto_log():
    while True:
        try:
            time.sleep(5)
            tongji = get_log_info()
            if len(tongji)>0:
                filename = 'json/' + str(datetime.datetime.now().strftime('%Y-%m-%d')) + '.json'
                setJsonFile(filename,tongji)
        except Exception, e:
            print('auto_log err:' + str(e))
        time.sleep(xyconfig.get('uptime',5)*60)
if __name__ == "__main__":
    Thread(target=auto_log, args=()).start() #定时更新

    http_server = WSGIServer(('0.0.0.0', xyconfig.get('port',8181)), app)
    http_server.serve_forever()


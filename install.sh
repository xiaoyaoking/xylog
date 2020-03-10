apt-get install -y python python-pip zip unzip
pip install Flask gevent
nohup python xyweblog.py >/dev/null 2>&1 &
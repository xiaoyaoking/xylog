apt-get install -y python python-pip zip unzip
pip install Flask gevent requests
nohup python xylog.py >/dev/null 2>&1 &

import os
os.chdir('/tmp')

import redis
from rq import Worker, Queue, Connection



listen = ['default']

pool = redis.ConnectionPool(db=0, host='localhost', port=6379)
redis_conn = redis.Redis(connection_pool=pool)

if __name__ == '__main__':
    with Connection(redis_conn):
        worker = Worker(map(Queue, listen))
        worker.work()

import os
import redis

from rq import Worker, Queue, Connection
from datamart_isi.utilities import connection

os.chdir('/tmp')

listen = ['default']

# pool = redis.ConnectionPool(db=0, host='localhost', port=6379)
redis_host, redis_server_port = connection.get_redis_host_port()
pool = redis.ConnectionPool(db=0, host=redis_host, port=redis_server_port)
redis_conn = redis.Redis(connection_pool=pool)

if __name__ == '__main__':
    with Connection(redis_conn):
        worker = Worker(map(Queue, listen))
        worker.work()

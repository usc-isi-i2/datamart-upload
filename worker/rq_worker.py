import os
import redis
import time
import logging
from rq import Worker, Queue, Connection
from datamart_isi.utilities import connection

os.chdir('/tmp')
listen = ['default']
_logger = logging.getLogger(__name__)

# pool = redis.ConnectionPool(db=0, host='localhost', port=6379)
redis_host, redis_server_port = connection.get_redis_host_port()
pool = redis.ConnectionPool(db=0, host=redis_host, port=redis_server_port)
redis_conn = redis.Redis(connection_pool=pool)

def is_redis_available(redis_conn):
    try:
        redis_conn.get(None)  # getting None returns None or throws an exception
    except (redis.exceptions.ConnectionError, redis.exceptions.BusyLoadingError):
        _logger.debug("Redis is still loading or not ready yet.")
        return False
    except redis.exceptions.DataError:
        _logger.warn("Redis is ready for connection.")
        return True
    _logger.warn("Redis is ready for connection (2).")
    return True


if __name__ == '__main__':
    # wait until redis is available
    while not is_redis_available(redis_conn):
        _logger.debug("Wait for 10 seconds.")
        time.sleep(10)

    worker_started = False
    while not worker_started:
        try:
            with Connection(redis_conn):
                worker = Worker(map(Queue, listen))
                worker.work()
                worker_started = True
                _logger.warn('rq worker started')
        except redis.exceptions.BusyLoadingError:
            # redis is busy
            _logger.debug('Wait for 10 seconds')
            time.sleep(10)

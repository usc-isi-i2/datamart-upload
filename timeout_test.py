import eventlet
import time

eventlet.monkey_patch() 
time_limit = 3  #set timeout time 3s
with eventlet.Timeout(None,False):
    time.sleep(5)
    print('arrive here!')

print('end--------')

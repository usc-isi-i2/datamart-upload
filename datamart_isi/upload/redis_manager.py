import redis
import json

class RedisManager(object):
    """
    Class for managing the connection to redis and defines several apis to use to perform the required redis lookups.
    """
    def __init__(self, host, port):
        self.redis = redis.StrictRedis(host, int(port), charset="utf-8", decode_responses=True)
        return

    def getKey(self, key):
        """

        :param key:  the key of the set to fetch
        :return: list of members for that set
        """
        # Retreive all the members of the set 'key'
        elements = self.redis.smembers(key)
        return elements

    def get(self, key):
        """

        :param key: the key to fetch
        :return: integer count stored at that key
        """
        ret_val = self.redis.get(key)
        if not ret_val:
            ret_val = 0
        return int(ret_val)


    def setKey(self, key, vals):
        """

        :param key: key to set
        :param vals: list of members to set for that key
        :return: None
        """
        # Adding all the values in the iterable to the set stored at key
        self.sadd(key, *(vals))
        return

    def checkIfExists(self, key, value, keyprefix=""):
        """

        :param key: the key to search in
        :param value: the value to check if it is a member of the set stored at 'key'
        :return: Boolean
        """
        flag = self.redis.sismember(keyprefix+key, value)
        return flag

    def getKeys(self ,keys, prefix=""):
        """
        :param keys: List of keys to fetch
        :return: A dictionary of the keys and their corresponding value sets.
        """
        # Fetch several sets of keys using redis pipeline
        pipe = self.redis.pipeline()
        for key in keys:
            pipe.smembers(prefix+key)
        data = dict(zip(keys,pipe.execute()))
        return data

    def getKeysAsJson(self, keys, prefix=""):
        """
        :param keys: List of keys to fetch from redis
        :param prefix: They keyspace in redis
        :return: Return a dictionary of statements for each key.
        """
        pipe = self.redis.pipeline()
        for key in keys:
            pipe.get(prefix+key)
        data = dict(zip(keys, [json.loads(x) for x in pipe.execute()]))
        return data



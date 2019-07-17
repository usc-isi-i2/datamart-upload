from datamart_isi.materializers.parsers.parser_base import *
import requests
import gzip 
from io import StringIO

class CSVParser(ParserBase):

    def get_all(self, url: str) -> typing.List[pd.DataFrame]:
        try:
            download_res = requests.get(url) 
            decompressed_res = gzip.decompress(download_res.content).decode("utf-8") 
            decompressed_res = StringIO(decompressed_res)
            return [pd.read_csv(decompressed_res, dtype="str")]
        except:
            return [pd.read_csv(url)]
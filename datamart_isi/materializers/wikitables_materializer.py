from datamart_isi.materializers.materializer_base import MaterializerBase
from tablextract import tables
from typing import Optional
from pandas import DataFrame
from collections import OrderedDict


WIKIPEDIA_CSS_FILTER = '#content table:not(.infobox):not(.navbox):not(.navbox-inner):not(.navbox-subgroup):not(.sistersitebox)'

class WikitablesMaterializer(MaterializerBase):
    def __init__(self, **kwargs):
        MaterializerBase.__init__(self, **kwargs)

    def get(self, url:str, constrains: dict = None) -> Optional[DataFrame]:
        """ API for get a dataframe.

            Args:
                metadata: json schema for data_type
                variables:
                constrains: include some constrains like date_range, location and so on
        """
        tabs = tables(url, xpath_filter=None, css_filter=WIKIPEDIA_CSS_FILTER)
        # tabs = tables(metadata['url'], xpath_filter=metadata['xpath'])
        data = OrderedDict()
        results = []
        xpath_filters = []
        if len(tabs) > 0:
            for each in tabs:
                tab = each.record
                data = OrderedDict()
                for col in tab[0].keys():
                    data[col] = [r[col] for r in tab]
                results.append(DataFrame(data))
                xpath_filters.append(each.xpath)
        else:
            print("[WARN] No wikitable found from " + url)
        
        return results, xpath_filters

    def get_one(self, url:str, xpath_filter:str, constrains: dict = None) -> Optional[DataFrame]:
        """ API for get a dataframe.

            Args:
                metadata: json schema for data_type
                variables:
                constrains: include some constrains like date_range, location and so on
        """
        tabs = tables(url, xpath_filter=xpath_filter, css_filter=WIKIPEDIA_CSS_FILTER)
        # tabs = tables(metadata['url'], xpath_filter=metadata['xpath'])
        data = OrderedDict()
        results = []
        if len(tabs) > 0:
            tab = tabs[0].record
            data = OrderedDict()
            for col in tab[0].keys():
                data[col] = [r[col] for r in tab]
            return DataFrame(data)

        else:
            print("[WARN] No wikitable found from " + url)    
            return DataFrame()
        
from common.wordlist import WordList, KeyedWordList, unweighted_to_weighted
from loader.loader import Loader

from configurator import configurator
import yaml
import json
import sys
from augmenter.augmenter import load_word2vec_model

class LinkingScript(object):
    def __init__(self, config):
        self.config = config

    def prepare_datasets(self):
        self.target_data = self.load_target_data()
        
        self.target_data_filtered = self.filter_target_data(self.target_data)

        self.target_data_aug = self.augment_target_data(self.target_data_filtered)

        self.target_data_aug_filtered  = self.filter_augmented_target_data(self.target_data_aug)

    def get_word_map(self, keywords):
        self.source_data = self.load_source_data(keywords)
        self.source_data_filtered = self.filter_source_data(self.source_data)
        self.source_data_aug = self.augment_source_data(self.source_data_filtered)
        self.source_data_aug_filtered = unweighted_to_weighted(self.filter_augmented_source_data(self.source_data_aug))
        return {k: s.word_map for k, s in zip(keywords, self.source_data_aug_filtered)}

    def process(self, keywords):
        sys.stderr.write("process recvd" + json.dumps(keywords))
        self.source_data = self.load_source_data(keywords)
        self.source_data_filtered = self.filter_source_data(self.source_data)
        self.source_data_aug = self.augment_source_data(self.source_data_filtered)
        self.source_data_aug_filtered = unweighted_to_weighted(self.filter_augmented_source_data(self.source_data_aug))

        alignments = self.align_datasets(self.source_data_aug_filtered, 
                                         self.target_data_aug_filtered)
        alignlist = []
        for alignment in alignments.keys():
            alignmap = dict()
            alignmap['keyword']=alignment
            alignmap['augmentation'] = {k: s.word_map for k, s in zip(keywords, self.source_data_aug_filtered)}
            alignmap['alignments'] = []
            for aligned in alignments[alignment]:
                alignedmap = dict()
                if aligned["wl"] is not None:
                    if aligned["wl"].get_key() is not None:
                        alignedmap["name"] = aligned["wl"].get_key()
                        alignedmap["desc"] = aligned["wl"].get_original_string()
                    else:
                        alignedmap["name"] = aligned["wl"].get_original_string()
                alignedmap["score"] = aligned["score"]
                alignmap['alignments'].append(alignedmap)
            alignlist.append(alignmap)
        return alignlist

    def load_source_data(self, keywords):
        loader = self.config.get_component('src_loader')
        return loader.load(keywords)

    def load_target_data(self):
        loader = self.config.get_component('tgt_loader')
        return loader.load()

    def filter_target_data(self, data):
        tfilter = self.config.get_component('tgt_pre_augmentation_filter')
        return tfilter.filter_words(data)

    def filter_source_data(self, data):
        sfilter = self.config.get_component('src_pre_augmentation_filter')
        return sfilter.filter_words(data)

    def augment_source_data(self, data):
        augmenter = self.config.get_component('src_augmenter')
        return augmenter.augment_word_lists(data)

    def augment_target_data(self, data):
        augmenter = self.config.get_component('tgt_augmenter')
        return augmenter.augment_word_lists(data)

    def filter_augmented_source_data(self, data):
        sfilter = self.config.get_component('src_post_augmentation_filter')
        return sfilter.filter_words(data)

    def filter_augmented_target_data(self, data):
        tfilter = self.config.get_component('tgt_post_augmentation_filter')
        return tfilter.filter_words(data)
    
    def align_datasets(self, labels_provider, ontology_provider):
        aligner = self.config.get_component('aligner')
        return aligner.align_word_lists(labels_provider, ontology_provider)
        


def make_YML_config(filename):
    args = yaml.load(open(filename,'r'))
    yml_config = configurator.Configurator(args)
    return yml_config

def make_CMD_config(request):
    args = request.get_json()
    cmd_config = configurator.Configurator(args)
    return cmd_config

if __name__ == '__main__':
    #opts = yaml.load(open('linking_config.yml','r'))
    resources = {}
    resources['GNews_SLIM_model'] = load_word2vec_model('../data/GoogleNews-vectors-negative300-SLIM.bin', binary=True)

    lscript = LinkingScript(make_YML_config('../cfg/linking_config.svo.yml'))
    lscript.config.set_augmenter_preload_resources(resources)
    lscript.prepare_datasets()
    #print(lscript.get_word_map(["oil price", "gold"]))
    #print(lscript.process(["oil price", "gold"]))
    print(lscript.get_word_map(["rainfall", "humidity", "atmospheric pressure", "soil temperature at 3 meters"]))
    print(lscript.process(["rainfall", "humidity", "atmospheric pressure", "soil temperature at 3 meters"]))

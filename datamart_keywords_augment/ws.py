import os
import glob

from flask import Flask, request, jsonify
from flask_restful import Api, Resource, reqparse

from linking_script import *

app = Flask(__name__)
api = Api(app)
configs = {}
resources = {}

CONFIG_DIR_PATH = os.path.abspath(os.path.join('../cfg/', '*.yml'))

def load_resources():
    # preload resources
    print('loading resources...')
    resources['GNews_SLIM_model'] = load_word2vec_model('../data/GoogleNews-vectors-negative300-SLIM.bin', binary=True)
    # resources['ELICIT_Corpus'] = load_elicit_corpus('../data/processed_ELICIT_Corpus_new')

    # configs
    for config_path in glob.glob(CONFIG_DIR_PATH):
        print('loading config:', config_path)
        k = os.path.splitext(os.path.basename(config_path))[0]
        configs[k] = {
            'abspath': config_path,
            'config': make_YML_config(config_path),
            'script': {
                'alignment': None,
                'linking': None
            }
        }
        configs[k]['config'].set_augmenter_preload_resources(resources)

    # load datasets
    for k in configs.keys():
        print('loading datasets...', k)
        # script = alignment_script.AlignmentScript(configs[k]['config'])
        # script.prepare_datasets()
        # configs[k]['script']['alignment'] = script
        script = LinkingScript(configs[k]['config'])
        script.prepare_datasets()
        configs[k]['script']['linking'] = script

    import pickle
    import pdb
    pdb.set_trace()

class ApiRoot(Resource):
    def get(self):
        return 'Data augmentation web service'

class ApiConfig(Resource):
    def get(self):
        return list(configs.keys())

# class ApiAlignment(Resource):

#     def get(self, config_name):
#         if not config_name in configs:
#             return {'error': 'Invalid config name'}, 500

#         config = configs[config_name]['config']
#         script = configs[config_name]['script']['alignment']

#         alignments = script.process()
#         alignmentsConverted = script.convertToLabelAlignmentMap(alignments)

#         truth_dataset = config.get_component('truth_loader').load()
#         performance_evaluator = config.get_component('performance_evaluator')
#         if performance_evaluator is not None:
#             match_score = performance_evaluator.evaluate(truth_dataset, alignmentsConverted) #name to evaluate instead of score
#             data = {"alignments:":alignments, "match_score": match_score}
#         else:
#             data = {"alignments:":alignments}
#         return data

class ApiLinking(Resource):
    def get(self, config_name, keywords):
        if not config_name in configs:
            return {'error': 'Invalid config name'}, 500
        keywords = list(map(lambda x: x.strip(), keywords.split(',')))
        wordmap = request.args.get('wordmap', default=False, type=bool)

        script = configs[config_name]['script']['linking']
        if wordmap:
            return script.get_word_map(keywords)
        else:
            return script.process(keywords)


api.add_resource(ApiRoot, '/')
api.add_resource(ApiConfig, '/config')
# api.add_resource(ApiAlignment, '/alignment/<string:config_name>')
api.add_resource(ApiLinking, '/linking/<string:config_name>/<string:keywords>')

if __name__ == '__main__':
    load_resources()
    app.run(debug=False, host="127.0.0.1", port=5678)

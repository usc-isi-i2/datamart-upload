from augmenter import augmenter
from pydoc import locate


def set_with_default(config, key, default_val):
    if key not in config:
        return default_val
    return config[key]


class Configurator(object):
    def __init__(self, args):
        self.args = args
        self.default_module = {}
        self.default_module['src_loader'] = "loader"
        self.default_module['tgt_loader'] = "loader"
        self.default_module['truth_loader'] = "loader"
        self.default_module['src_pre_augmentation_filter'] = "filters.wordlist_filter"
        self.default_module['tgt_pre_augmentation_filter'] = "filters.wordlist_filter"
        self.default_module['src_post_augmentation_filter'] = "filters.wordlist_filter"
        self.default_module['tgt_post_augmentation_filter'] = "filters.wordlist_filter"
        self.default_module['src_augmenter'] = "augmenter"
        self.default_module['tgt_augmenter'] = "augmenter"
        self.default_module['aligner'] = "aligner"
        self.default_module['performance_evaluator'] = "performance_evaluator"
        self.augmenter_preload_resources = None

    def set_augmenter_preload_resources(self, res):
        self.augmenter_preload_resources = res
 
    def get_class_instance(self, module_path):
        my_class = locate(module_path)
        return my_class

    def get_instance(self, component_key):
        if component_key in self.args and self.args[component_key]['class']:
            argument_value = self.args[component_key]['class']
            default_module = self.default_module[component_key]
            has_package = argument_value.find('.')
            provider = None
            if (has_package <  0):
                provider = self.get_class_instance(default_module+'.'+argument_value)
            else:
                provider = self.get_class_instance(argument_value)
            kwargs = {}
            if self.augmenter_preload_resources and augmenter.Augmenter in provider.__bases__:
                for r in provider.required_resources():
                    kwargs[r] = self.augmenter_preload_resources[r]
            return provider(self.args[component_key], **kwargs)

    def get_component(self, component_key):
        return self.get_instance(component_key)

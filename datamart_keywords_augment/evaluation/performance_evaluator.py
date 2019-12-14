
# import data
from configurator import configurator


class Performance_Evaluator(object):
    def __init__(self, config=None):
        self.config = config
        self.k = configurator.set_with_default(config, 'precision_k', 1)
 
    def evaluate(self, truth_map, alignment_map):
        pass
    

# Each augmentation method is a subclass

class Precision_At_K(Performance_Evaluator):
    def __init__(self, config=None):
        super().__init__(config)
        self.k = 1
    
    
    def evaluate(self, truth_map, alignment_map):
        assert self.k >= 1
        hit_at_k = 0
        for label in truth_map.keys():
            truth = [i[0] for i in truth_map[label]]
            predicted = [i[0] for i in alignment_map[label]]
            if len(predicted) >= self.k:
                for ontology in truth:
                    flag = False
                    for j in range(self.k):
                        if ontology == predicted[j]:
                            hit_at_k += 1
                            flag = True
                            break
                    if flag == True:
                        break
        return hit_at_k / len(truth_map)

class Mean_Reciprocal_Rank(Performance_Evaluator):
    def __init__(self, config=None):
        super().__init__(config)
    
    def evaluate(self, truth_map, alignment_map):
        sum_reciprocal_rank = 0.0
        for label in truth_map.keys():
            truth = [i[0] for i in truth_map[label]]
            predicted = [i[0] for i in alignment_map[label]]
            for ontology in truth:
                flag = False
                for j in range(len(predicted)):
                    if ontology == predicted[j]:
                        sum_reciprocal_rank += 1/(j+1)
                        flag = True
                        break
                if flag == True:
                    break
        return sum_reciprocal_rank / len(truth_map)

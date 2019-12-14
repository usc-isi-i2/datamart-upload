from configurator import configurator
from collections import Counter
from pyjarowinkler import distance
import edit_distance

class Aligner(object):
    def __init__(self, config):
        self.aligned_data = {}
        self.config = config
        self.top_k_alignments = configurator.set_with_default(config, 'top_k_ontologies', 5)
    
    def align_word_lists(self, label_objects, ontology_objects):
        for lwl in label_objects:
            #print("Original string in wl:",lwl.get_original_string())
            label_matches = dict()
            onto_map = dict()
            for owl in ontology_objects:
                label_matches[owl.get_original_string()] = self.score(lwl, owl)
                onto_map[owl.get_original_string()] = owl
                scores = []
                for term in self.filter_scored_terms(label_matches):
                    scores.append({"score":label_matches[term[0]], "wl":onto_map[term[0]]})
            self.aligned_data[lwl.get_original_string()] = scores
        return self.aligned_data

    def score(self, wordlist1, wordlist2):
        return 0

    def filter_scored_terms(self, terms):
        #print ("terms: " + str(terms))
        return Counter(terms).most_common(self.top_k_alignments)

    def evaluate(self):
        pass

# Each augmentation method is a subclass

class JS_Matching(Aligner):
    def __init__(self, config):
        super().__init__(config)
        #self.ontology = set(ontology_objects)
        
    def score(self, list1, list2):
        return self.JS_on_word(list1.words,list2.words)
    
    def JS_on_word(self, list1, list2):
        intersection = len(list(set(list1).intersection(list2)))
        union = (len(list1) + len(list2)) - intersection
        if union == 0:
            return 0
        else:
            return float(intersection / union)
        
        
class Levenshtein_Distance(Aligner):
    def __init__(self, config):
        super().__init__(config)
    
    def align_word_lists(self, label_objects, ontology_objects):
        query_clean = []
        for lwl in label_objects:
            lwl_string = lwl.string
            lwl_string = lwl_string.replace('(',' ').replace(')',' ').replace('of',' ')
            lwl.string = lwl_string
            query_clean.append(lwl)
        gsn_clean = []
        for owl in ontology_objects:
            owl_string = owl.string
            owl_string = owl_string.replace('(',' ').replace(')',' ').replace('of',' ')
            owl.string = owl_string
            query_clean.append(owl)
        return super().align_word_lists(query_clean, gsn_clean)
    
    def score(self, list1, list2):
        return edit_distance(list1.string, list2.string)
    

class JW_Distance(Aligner):
    
    def __init__(self, config):
        super().__init__(config)
    
    def align_word_lists(self, label_objects, ontology_objects):
        query_clean = []
        for lwl in label_objects:
            lwl_string = lwl.string
            lwl_string = lwl_string.replace('(',' ').replace(')',' ').replace('of',' ')
            lwl.string = lwl_string
            query_clean.append(lwl)
        gsn_clean = []
        for owl in ontology_objects:
            owl_string = owl.string
            owl_string = owl_string.replace('(',' ').replace(')',' ').replace('of',' ')
            owl.string = owl_string
            query_clean.append(owl)
        return super().align_word_lists(query_clean, gsn_clean)
    
    def score(self, list1, list2):
        return distance.get_jaro_distance(list1.string, list2.string, winkler=True, scaling=0.1)
    
class JS_on_char_Distance(Aligner):  
    
    def __init__(self, config):
        super().__init__(config)
    
    def JS_on_char(self, str1, str2):
        str1 = set(str1)
        str2 = set(str2)
        return float(len(str1 & str2)) / len(str1 | str2)

    def score(self, list1, list2):
        return self.JS_on_char(list1.string, list2.string)

class Weighted_JS_Matching(Aligner):
    def __init__(self, config):
        super().__init__(config)
    
    def score(self, wl1, wl2):
        intersection = list(set(wl1.words).intersection(wl2.words))
        union = list(set(wl1.words).union(wl2.words))
        
        weighted_label = wl1.word_map
        weighted_onto = wl2.word_map

        intersection_score = 0.0
        for intersection_word in intersection:
            intersection_score += wl1.word_map[intersection_word]*wl2.word_map[intersection_word]
            
        union_score = 0.0
        for union_word in union:
            if union_word in wl1.word_map and union_word in wl2.word_map:
                union_score += wl1.word_map[union_word]*wl2.word_map[union_word]
            elif union_word in wl1.word_map:
                union_score += wl1.word_map[union_word]
            else:
                union_score += wl2.word_map[union_word]
                
        match = float(intersection_score / union_score)
        return match    

class Exact_Matching(Aligner):
    def __init__(self, config):
        super().__init__(config)
    
    def score(self, wl1, wl2):
        intersection = list(set(wl1.words).intersection(wl2.words))
        if intersection is not None and len(intersection) != 0:
            return 1
        else:
            return 0

    
class Weighted_Exact_Matching(Aligner):
    def __init__(self, config):
        super().__init__(config)
    
    def score(self, wl1, wl2):
        intersection = list(set(wl1.words).intersection(wl2.words))
        union = list(set(wl1.words).union(wl2.words))
        
        weighted_label = wl1.word_map
        weighted_onto = wl2.word_map

        intersection_score = 0.0
        for intersection_word in intersection:
            intersection_score += wl1.word_map[intersection_word]*wl2.word_map[intersection_word]
                
        match = float(intersection_score)
        return match
        
            
class Intersection(Aligner):
    def __init__(self, config):
        pass

class Jaccard_Similarity(Aligner):
    def __init__(self, config):
        pass

class Edit_Distance(Aligner):
    def __init__(self, config):
        pass

class W2V_Matching(Aligner):
    def __init__(self, config):
        pass

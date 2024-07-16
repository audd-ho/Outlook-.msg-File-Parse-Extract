import os
import sys
import subprocess
import importlib

used_modules = ["torch", "math", "numpy", "itertools", "matplotlib", "scipy", "functools", "transformers", "sentence_transformers", "json", "getopt"]
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
def setup_modules(used_modules):
    missing_modules = []

    for mod in used_modules:
        try:
            importlib.import_module(mod)
        except ModuleNotFoundError:
            missing_modules.append(mod)
    for mod in missing_modules:
        if mod == "win32com.client":
            install("pywin32")
        elif mod == "torch":
            package_list = ["torch", "torchvision", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cu118"]
            subprocess.check_call(([sys.executable, "-m", "pip3", "install"] + package_list))
        else:
            install(mod)
    #print(f"Please re-run the program, some packages were installed")
    #sys.exit(1)
    if len(missing_modules) != 0:
        os.execv(sys.executable, ['python'] + sys.argv)
setup_modules(used_modules)

## Pre-cursor Codes, no zero classifier yet

## Overall Useful Functions

import torch
import math
import numpy as np
def get_length(embedding_1d):
    sum = 0
    for i in embedding_1d:
        sum+=(i**2)
    return math.sqrt(sum)
def normalise_embedding(embedding_1d):
    length = get_length(embedding_1d)
    for i in range(len(embedding_1d)):
        embedding_1d[i] /= length
def get_normalise_embedding(embedding_1d):
    if type(embedding_1d) is torch.Tensor:
        temp_embedding_1d = (embedding_1d.detach().numpy()).copy()
    else:
        temp_embedding_1d = embedding_1d.copy()
    length = get_length(temp_embedding_1d)
    for i in range(len(temp_embedding_1d)):
        temp_embedding_1d[i] /= length
    return temp_embedding_1d


def cosine_sim(embedding_1, embedding_2):
    embedding_1 = get_normalise_embedding(embedding_1)
    embedding_2 = get_normalise_embedding(embedding_2)
    sim_sum = 0
    for e_1, e_2 in zip(embedding_1, embedding_2):
        sim_sum += (e_1*e_2)
    return sim_sum
def norm_ed_cosine_sim(embedding_1, embedding_2):
    sim_sum = 0
    for e_1, e_2 in zip(embedding_1, embedding_2):
        sim_sum += (e_1*e_2)
    return sim_sum

## Cosine Similarity -- Embedding Model

def generic_sent_cos_sim(model_emb_func, t1, t2, additional_nesting = False):
    if additional_nesting:
        return cosine_sim(model_emb_func(t1)[0], model_emb_func(t2)[0])    
    return cosine_sim(model_emb_func(t1), model_emb_func(t2))

#Mean Pooling - Take attention mask into account for correct averaging
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0] #First element of model_output contains all token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

## Semantic Segmentation Function PREPARATION FUNCTIONS

from itertools import islice

def window(seq, n=3):
    it = iter(seq)
    result = tuple(islice(it, n))
    if len(result) == n:
        yield result
    for elem in it:
        result = result[1:] + (elem,)
        yield result
        
        
        
        
def climb(co_score_list, list_index, mode = "l"):
    res_score = 0
    if mode == "l":
        while (list_index >= 0):
            if co_score_list[list_index] > res_score:
                res_score = co_score_list[list_index]
                list_index -= 1
            else:
                break
        return res_score
    else:
        list_len = len(co_score_list)
        while (list_index < list_len):
            if co_score_list[list_index] > res_score:
                res_score = co_score_list[list_index]
                list_index += 1
            else:
                break
        return res_score
    
def get_depth_score_list(co_score_list):
    res_depth_score_list = []
    co_score_len = len(co_score_list)
    for i in range(co_score_len):
        i_co_score = co_score_list[i]
        l_peak = climb(co_score_list, i, "l")
        r_peak = climb(co_score_list, i, "r")
        i_depth_score = 0.5 * (l_peak + r_peak - (2*i_co_score))
        res_depth_score_list.append(i_depth_score)
    return np.array(res_depth_score_list)




import matplotlib.pyplot as plt

from scipy.signal import argrelmax

def get_local_maxima(depth_scores, order=1):
    maxima_ids = argrelmax(depth_scores, order=order)[0]
    filtered_scores = np.zeros(len(depth_scores))
    filtered_scores[maxima_ids] = depth_scores[maxima_ids]
    return filtered_scores

def compute_threshold(scores): ## maybe can make this more picky, by making threshold higher, like (np.std(s) / 3) or /4 or more instead?
    s = scores[np.nonzero(scores)]
    threshold = np.mean(s) - (np.std(s) / 2)
    # threshold = np.mean(s) - (np.std(s))
    return threshold

def get_threshold_segments(scores, threshold=0.1):
    segment_ids = np.where(scores >= threshold)[0]
    return segment_ids




def primitively_naive_tokeniser(text):
    toks_list = text.split(" ")
    return toks_list

## Semantic Segmentation Function Portions

WINDOW_SIZE = 3

def sentence_to_sliding_window(sentence_s):
    sentence_words_toks = primitively_naive_tokeniser(sentence_s)
    window_size_split = list(window(sentence_words_toks, WINDOW_SIZE))
    window_splited_texts = [' '.join([window_toks for window_toks in each_window]) for each_window in window_size_split]
    return window_splited_texts

def coherence_score_list_from_embedding_list(window_splited_embedding_list):
    coherence_scores_list = [cosine_sim(pair[0], pair[1]) for pair in zip(window_splited_embedding_list[:-1], window_splited_embedding_list[1:])]
    return coherence_scores_list

def plot_data_points(vary_data, thres = -1):
    plt.plot(vary_data)
    if (thres == -1):
        plt.show()
    else:
        plt.plot([thres for i in range(len(vary_data))])
        plt.show()

def filtered_indexes_list_to_splitted_segments_by_semantics(original_sent, filtered_indexes_list):
    sentence_words_toks = primitively_naive_tokeniser(original_sent)
    segment_key_breaks = get_threshold_segments(filtered_indexes_list, compute_threshold(filtered_indexes_list))
    segment_demark = [0] + [(ids + (WINDOW_SIZE-1)) for ids in segment_key_breaks] + [len(sentence_words_toks)]
    segment_demark_intervals = list(zip(segment_demark[:-1], segment_demark[1:]))
    resultant_segments_after_split_by_interval = [" ".join(sentence_words_toks[interval_points[0]:interval_points[1]]) for interval_points in segment_demark_intervals]
    return resultant_segments_after_split_by_interval

## Semantic Segmentation Function

def semantic_segmentation_function(embedding_model_function, sentence_text, intermediate_status = False, graph_status = False):
    windowed_parts = sentence_to_sliding_window(sentence_text)
    if intermediate_status:
        print(f"windowed_parts: {windowed_parts}")
    
    # if ensure "embedding_model_function" accept only 1 string and return 1d array/tensor then can use the below code, current should still work!!, as long as return 1d array for single string!!
    # embedding_list = [embedding_model_function(windowed_part) for windowed_part in windowed_parts]
    
    ## if list of input strings can produce 2d array/tensor automatically, then can just use below one!!, only 1 time embed bunch at once!!
    embedding_list = embedding_model_function(windowed_parts)
    if intermediate_status:
        print(f"embedding_list: {embedding_list}")
    """
    if graph_status:
        print("Embedding List Plot") # bad! like no use
        plot_data_points(embedding_list) # bad! like no use
    """
    
    windowed_parts_coherence_score_list = coherence_score_list_from_embedding_list(embedding_list)
    if intermediate_status:
        print(f"windowed_parts_coherence_score_list: {windowed_parts_coherence_score_list}")
    if graph_status:
        print("Coherence Score Plot:")
        plot_data_points(windowed_parts_coherence_score_list)
    
    windowed_parts_depth_score_list = get_depth_score_list(windowed_parts_coherence_score_list)
    if intermediate_status:
        print(f"windowed_parts_depth_score_list: {windowed_parts_depth_score_list}")
    if graph_status:
        print("Depth Score Plot:")
        plot_data_points(windowed_parts_depth_score_list)
    
    windowed_parts_filtered_depth_score_list = get_local_maxima(windowed_parts_depth_score_list)
    if intermediate_status:
        print(f"windowed_parts_filtered_depth_score_list: {windowed_parts_filtered_depth_score_list}")
    if graph_status:
        print("Filtered Depth Score Plot:")
        plot_data_points(windowed_parts_filtered_depth_score_list)
    
    filtered_threshold = compute_threshold(windowed_parts_filtered_depth_score_list)
    if intermediate_status:
        print(f"filtered_threshold: {filtered_threshold}")
    if graph_status:
        print("Filtered Depth Score With Threshold Line Plot:")
        plot_data_points(windowed_parts_filtered_depth_score_list, filtered_threshold)

    #sentences_tokenised = primitively_naive_tokeniser(sentences)
    #sentences_topics_splitted = filtered_indexes_list_to_splitted_sent(sentences_tokenised, windowed_sentences_filtered_depth_score_v1_list)
    sentences_topics_splitted = filtered_indexes_list_to_splitted_segments_by_semantics(sentence_text, windowed_parts_filtered_depth_score_list)
    return sentences_topics_splitted

# Lock Model
def lock_semantic_segmentation_function(embedding_model_function):
    def lockED_semantic_segmentation_function(sentence_text, intermediate_status = False, graph_status = False): # all these default params need to have because the locked function can have the option to leave the args blank for them to let it be default!
        return semantic_segmentation_function(embedding_model_function=embedding_model_function, sentence_text=sentence_text, intermediate_status=intermediate_status, graph_status=graph_status)
    return lockED_semantic_segmentation_function

# Generic Similarity Comparison Function (comparison tuples in a list for comparison!)

def generic_similarity_comparison_function(embedding_model_function, comparison_tuple_in_list, sort_output = 0):
    res_dict = {}
    for comp_items in comparison_tuple_in_list:
        # possible alternative is below, so that if embedding model only accept one string and return 1d array/tensor then works!!
        # comp_emb = [embedding_model_function(comp_items[0]), embedding_model_function(comp_items[1])]
        comp_emb = embedding_model_function([comp_items[0], comp_items[1]]) # or just list(comp_items)
        cos_sim = cosine_sim(comp_emb[0], comp_emb[1])
        res_dict[comp_items] = cos_sim
        
    # sort by -1 is descending, 0 is no sort, 1 is ascending!
    # default is no sort, 0
    if sort_output == -1:
        res_dict = {comp:comp_score for comp, comp_score in sorted(res_dict.items(), key = lambda dict_item: dict_item[1], reverse=True)}
    if sort_output == 1:
        res_dict = dict(sorted(res_dict.items(), key = lambda dict_item: dict_item[1], reverse=False))
    return res_dict
        

# partial does not allow arguments to be filled with keywords, need strictly positional so prefer not

## Error is like:
# generic_similarity_comparison_locked_model_MiniLM_L6_v2 = lock_generic_similarity_comparison_function(get_sentence_embedding_MiniLM_L6_v2)
# generic_similarity_comparison_locked_model_MiniLM_L6_v2([("hi there", "the world is bad"), ("i like people", "people love me"), ("the world is green", "the ocean is blue")], sort_output=1)

## Fix is need to specific keyword or change embedding callbaack function position and all, by keyword is like:
# generic_similarity_comparison_locked_model_MiniLM_L6_v2 = lock_generic_similarity_comparison_function(get_sentence_embedding_MiniLM_L6_v2)
# generic_similarity_comparison_locked_model_MiniLM_L6_v2(comparison_tuple_in_list=[("hi there", "the world is bad"), ("i like people", "people love me"), ("the world is green", "the ocean is blue")], sort_output=1)
## see the "comparison_tuple_in_list=" specified, for example! ^

"""
from functools import partial

def lock_generic_similarity_comparison_function(embedding_model_function):
    return partial(generic_similarity_comparison_function, embedding_model_function=embedding_model_function)
"""

## instead of def new function, lambda approach!

def lock_generic_similarity_comparison_function(embedding_model_function):
    return lambda comparison_tuple_in_list, sort_output = 0: generic_similarity_comparison_function(embedding_model_function=embedding_model_function, comparison_tuple_in_list=comparison_tuple_in_list, sort_output=sort_output)

# ONE Category Similarity Comparison Function (compare to each string in a list!)
def single_category_similarity_comparison_function(embedding_model_function, category_single, texts, sort_output = 0):
    if type(texts) != list:
        texts = [texts]
    compiled_tuple_comparison_list = [(text, category) for text, category in zip(texts, [category_single for i in range(len(texts))])]
    comparison_result_dict = generic_similarity_comparison_function(embedding_model_function=embedding_model_function, comparison_tuple_in_list=compiled_tuple_comparison_list, sort_output=sort_output)
    return comparison_result_dict

def lock_single_category_similarity_comparison_function(embedding_model_function):
    def lockED_single_category_similarity_comparison_function(category_single, texts, sort_output=0): ## sort_output=0 is needed since it can be left blank when called from locked model!
        return single_category_similarity_comparison_function(embedding_model_function=embedding_model_function, category_single=category_single, texts=texts, sort_output=sort_output)
    return lockED_single_category_similarity_comparison_function

# Categories Similarity Comparison Function (compare to each string in a list!)

# sort by -1 is descending, 0 is no sort, 1 is ascending!
# default is no sort, 0
    
def categories_similarity_comparison_function(embedding_model_function, categories, texts, sort_output = 0):
    if type(categories) != list:
        categories = [categories]
    categories_comparison_result_dict = {}
    for category in categories:
        categories_comparison_result_dict[category] = single_category_similarity_comparison_function(embedding_model_function=embedding_model_function, category_single=category, texts=texts, sort_output=sort_output)
    return categories_comparison_result_dict

"""
from functools import partial

def lock_categories_similarity_comparison_function(embedding_model_function):
    return partial(categories_similarity_comparison_function, embedding_model_function=embedding_model_function)
"""

# lambda approach somewhat!, no keyword in the lambda now, just based off positional cos it can! but the sort_output=0 is a must, so that when call the locked function, if leave blank for it, wont error!
def lock_categories_similarity_comparison_function(embedding_model_function):
    return lambda categories, texts, sort_output=0: categories_similarity_comparison_function(embedding_model_function, categories, texts, sort_output)

# Categories Similarity Result Display

# Very specific use case only for "single_category_similarity_comparison_function" which returns a dict of compare_key and result_value
# Not usable on "categories_similarity_comparison_function" since this returns will return dict of dict!

def category_similarity_result_display(category_result_dict, sort_display = 0):
    print(f"Category: {list(category_result_dict.keys())[0][1]}") ## trashy clusterfuck
    print("Similarity Level:")
    if sort_display == -1:
        for comparison_items_tuple, comparison_result in (sorted(category_result_dict.items(), key= lambda dict_item: dict_item[1], reverse=True)):
            print(f"{comparison_items_tuple[0]:30.30} /-/ {comparison_items_tuple[1]:30.30} : {comparison_result:.5}")
    elif sort_display == 1:
        for comparison_items_tuple, comparison_result in (sorted(category_result_dict.items(), key= lambda dict_item: dict_item[1], reverse=True)):
            print(f"{comparison_items_tuple[0]:30.30} /-/ {comparison_items_tuple[1]:30.30} : {comparison_result:.5}")
    else:
        for comparison_items_tuple, comparison_result in category_result_dict.items():
            print(f"{comparison_items_tuple[0]:30.30} /-/ {comparison_items_tuple[1]:30.30} : {comparison_result:.5}")

# Categories Similarity Result Display
def categories_similarity_result_display(categories_result_dict, sort_display = 0):
    for category, category_similarity_results_dict in categories_result_dict.items():
        print(f"Category: {category}")
        print("Similarity Level:")
        if sort_display == -1:
            for comparison_items_tuple, comparison_result in (sorted(category_similarity_results_dict.items(), key= lambda dict_item: dict_item[1], reverse=True)):
                print(f"{comparison_items_tuple[0]:30.30} /-/ {comparison_items_tuple[1]:30.30} : {comparison_result:.5}")
        elif sort_display == 1:
            for comparison_items_tuple, comparison_result in (sorted(category_similarity_results_dict.items(), key= lambda dict_item: dict_item[1], reverse=True)):
                print(f"{comparison_items_tuple[0]:30.30} /-/ {comparison_items_tuple[1]:30.30} : {comparison_result:.5}")
        else:
            for comparison_items_tuple, comparison_result in category_similarity_results_dict.items():
                print(f"{comparison_items_tuple[0]:30.30} /-/ {comparison_items_tuple[1]:30.30} : {comparison_result:.5}")

## Categories with sub-categories is in format of dictionary where general_category-key:sub-"categories"_in_list(actually more like "synonyms" of the general categories)-value
## returns a dictionary of general_category-key:{sub-"category"(general category "synonyms")-key:{(xyz_comparison, sub-"category"/"synonym"):cosine_similarity}}

def categories_wsub_similarity_comparison_function(embedding_model_function, categories_wsub_dict, texts, sort_output=0):
    categories_wsub_result_dict = {}
    for big_general_category, sub_categories in categories_wsub_dict.items():
        categories_wsub_result_dict[big_general_category] = categories_similarity_comparison_function(embedding_model_function=embedding_model_function, categories=([big_general_category]+sub_categories), texts=texts, sort_output=sort_output)
    return categories_wsub_result_dict

def lock_categories_wsub_similarity_comparison_function(embedding_model_function):
    return lambda categories_wsub_dict, texts, sort_output=0: categories_wsub_similarity_comparison_function(embedding_model_function=embedding_model_function, categories_wsub_dict=categories_wsub_dict, texts=texts, sort_output=sort_output)

def categories_wsub_similarity_result_display(categories_wsub_result_dict, sort_display = 0):
    for big_general_category, big_wsub_categories_result in categories_wsub_result_dict.items():
        print(f"General Category: {big_general_category}")
        categories_similarity_result_display(big_wsub_categories_result, sort_display=sort_display)
        print()

## Top xxx and Limit yyy, display function different mainly

# Prep
def categories_similarity_result_display_top_limit(categories_result_dict, top_many = 5, limit_value = 0.5):
    for category, category_similarity_results_dict in categories_result_dict.items():
        print(f"Sub-Categories: {category}")
        print(f"Similarity Level Of Top {top_many} (Limit={limit_value}):")
        num_count = 0
        #if sort_display == -1:
        for comparison_items_tuple, comparison_result in (sorted(category_similarity_results_dict.items(), key= lambda dict_item: dict_item[1], reverse=True)):
            if num_count == top_many or comparison_result < limit_value:
                break
            print(f"{comparison_items_tuple[0]:30.30} /-/ {comparison_items_tuple[1]:30.30} : {comparison_result:.5}")
            num_count += 1
        """
        elif sort_display == 1:
            for comparison_items_tuple, comparison_result in (sorted(category_similarity_results_dict.items(), key= lambda dict_item: dict_item[1], reverse=True)):
                if num_count == top_many or comparison_result < limit_value:
                    break
                print(f"{comparison_items_tuple[0]:30.30} /-/ {comparison_items_tuple[1]:30.30} : {comparison_result:.5}")
        else:
            for comparison_items_tuple, comparison_result in category_similarity_results_dict.items():
                if num_count == top_many or comparison_result < limit_value:
                    break
                print(f"{comparison_items_tuple[0]:30.30} /-/ {comparison_items_tuple[1]:30.30} : {comparison_result:.5}")
        """
# Actual using function
def categories_wsub_similarity_result_display_top_limit(categories_wsub_result_dict, top_many = 5, limit_value = 0.5):
    for big_general_category, big_wsub_categories_result in categories_wsub_result_dict.items():
        print(f"General Category: {big_general_category}")
        general_category_subcats = tuple(big_wsub_categories_result.keys())
        subcat_combined_dicts = {}
        for subcat_dicts in big_wsub_categories_result.values():
            subcat_combined_dicts = subcat_combined_dicts | subcat_dicts
        #sorted_subcat_combined_dicts = {comp_tuple:comp_res for comp_tuple, comp_res in sorted(subcat_combined_dicts.items(), key = lambda dict_item: dict_item[1], reverse=True)}
        categories_similarity_result_display_top_limit({general_category_subcats: subcat_combined_dicts}, top_many=top_many, limit_value=limit_value)
        print()

def categories_wsub_similarity_comparison_resort_function(categories_wsub_similarity_comparison_result_dict, get_inner_list = False, sort_within_cat=0, top_many_wsub = 3, limit_value = 0.5):
    resorted_categories_wsub_similarity_comparison_dict = {}
    if limit_value < 0:
        if sort_within_cat == -1:
            limit_value = 0
        if sort_within_cat == 0:
            limit_value = None
        if sort_within_cat == 1:
            limit_value = 1
    
    if get_inner_list:
        for category, sub_syn_cat_dict in categories_wsub_similarity_comparison_result_dict.items():
            resorted_categories_wsub_similarity_comparison_dict[category] = []
            for sub_syn_cat_text_tuple_pred_dict in sub_syn_cat_dict.values():
                for sub_syn_cat_text_tuple, pred in sub_syn_cat_text_tuple_pred_dict.items():
                    if sort_within_cat == 0 or (sort_within_cat == -1 and pred >= limit_value) or (sort_within_cat == 1 and pred <= limit_value):    
                        resorted_categories_wsub_similarity_comparison_dict[category].append((sub_syn_cat_text_tuple, pred))
        # sorting below is within a category itself
        for category, comparison_tuple_pred_tuple in resorted_categories_wsub_similarity_comparison_dict.items():
            if sort_within_cat == -1:
                resorted_categories_wsub_similarity_comparison_dict[category] = list(sorted(comparison_tuple_pred_tuple, key= lambda tuple_item: tuple_item[1], reverse=True))[:top_many_wsub]
            if sort_within_cat == 0:
                resorted_categories_wsub_similarity_comparison_dict[category] = list(comparison_tuple_pred_tuple)[:top_many_wsub]
            if sort_within_cat == 1:
                resorted_categories_wsub_similarity_comparison_dict[category] = list(sorted(comparison_tuple_pred_tuple, key= lambda tuple_item: tuple_item[1], reverse=False))[:top_many_wsub]
        return resorted_categories_wsub_similarity_comparison_dict
            
    else:    
        for category, sub_syn_cat_dict in categories_wsub_similarity_comparison_result_dict.items():
            resorted_categories_wsub_similarity_comparison_dict[category] = {}
            for sub_syn_cat_text_tuple_pred_dict in sub_syn_cat_dict.values():
                for sub_syn_cat_text_tuple, pred in sub_syn_cat_text_tuple_pred_dict.items():
                    if sort_within_cat == 0 or (sort_within_cat == -1 and pred >= limit_value) or (sort_within_cat == 1 and pred <= limit_value):    
                        resorted_categories_wsub_similarity_comparison_dict[category][sub_syn_cat_text_tuple] = pred
        # sorting below is within a category itself
        for category, comparison_tuple_pred_dict in resorted_categories_wsub_similarity_comparison_dict.items():
            if sort_within_cat == -1:
                resorted_categories_wsub_similarity_comparison_dict[category] = dict(list(sorted(comparison_tuple_pred_dict.items(), key= lambda dict_item: dict_item[1], reverse=True))[:top_many_wsub])
            if sort_within_cat == 0:
                resorted_categories_wsub_similarity_comparison_dict[category] = dict(list(comparison_tuple_pred_dict.items())[:top_many_wsub])
            if sort_within_cat == 1:
                resorted_categories_wsub_similarity_comparison_dict[category] = dict(list(sorted(comparison_tuple_pred_dict.items(), key= lambda dict_item: dict_item[1], reverse=False))[:top_many_wsub])
    return resorted_categories_wsub_similarity_comparison_dict

## No Sorting Order, all made for the cleaning function, but the code is there but the argument is removed and relevant code portion is commented out, after all, for no sort, how to determine top xxx category, the top or bottom!!

def categories_wsub_similarity_comparison_resort_cleaning_function(resorted_categories_wsub_similarity_comparison_dict, get_inner_list = False, get_list = False, top_many_cat = 3):
    resultant_cleaned_list = []
    if get_inner_list:
        for category, comparison_tuple_pred_pair_tuple_list in resorted_categories_wsub_similarity_comparison_dict.items():
            for comparison_tuple, pred in comparison_tuple_pred_pair_tuple_list:
                resultant_cleaned_list.append((category, (comparison_tuple, pred)))
    else:
        for category, comparison_tuple_pred_pair_dict in resorted_categories_wsub_similarity_comparison_dict.items():
            for comparison_tuple, pred in comparison_tuple_pred_pair_dict.items():
                resultant_cleaned_list.append((category, (comparison_tuple, pred)))
    """
    # sort_cats args gone!! since cleaning is for top many, so no point giving option here, just restrict to just most to least!!
    if sort_cats == -1:
        sorted_resultant_cleaned_list = list(sorted(resultant_cleaned_list, key=lambda list_element: list_element[1][1], reverse=True))
    if sort_cats == 0:
        sorted_resultant_cleaned_list = resultant_cleaned_list
    if sort_cats == 1:
        sorted_resultant_cleaned_list = list(sorted(resultant_cleaned_list, key=lambda list_element: list_element[1][1], reverse=False))
    """
    sorted_resultant_cleaned_list = list(sorted(resultant_cleaned_list, key=lambda list_element: list_element[1][1], reverse=True))[:top_many_cat]
    if get_list:
        return sorted_resultant_cleaned_list
    """
    # for this to work with getting back a dict, which is sorted correctly, the "top_many_wsub" argument in previous function need to be 1
    ## if not, very wonky, since category as key means "top_many_cat" has to be <= number of category, else weird, and if "top_many_wsub" is not 1, the method below not so direct, need to ensure only add to dict once, and if category added then no more replacement!
    ### a possible alternative but unpreferred, so just keep "top_many_wsub" at 1 if following into this function!!
    
    sorted_resultant_cleaned_list_dict = {}
    for cat, tuple_pair in sorted_resultant_cleaned_list:
        if cat not in sorted_resultant_cleaned_list_dict:
            sorted_resultant_cleaned_list_dict[cat] = tuple_pair
    return sorted_resultant_cleaned_list_dict
    """
    return dict(sorted_resultant_cleaned_list)

def cleaned_categories_wsub_similarity_comparison_resorted_result_display(cleaned_resorted_compare_result, get_list):
    if get_list:
        for label, comparison_tuple_pred_pair_tuple in cleaned_resorted_compare_result:
            print(f"Category: {label}")
            print(f"{comparison_tuple_pred_pair_tuple[0][0]:30.30} /-/ {comparison_tuple_pred_pair_tuple[0][1]:30.30}: {comparison_tuple_pred_pair_tuple[1]:.5}")
            print()
    else:
        for label, comparison_tuple_pred_pair_tuple in cleaned_resorted_compare_result.items():
            print(f"Category: {label}")
            print(f"{comparison_tuple_pred_pair_tuple[0][0]:30.30} /-/ {comparison_tuple_pred_pair_tuple[0][1]:30.30}: {comparison_tuple_pred_pair_tuple[1]:.5}")
            print()

def classify_sentence(classifier, candidate_labels, sequence_to_classify, multi_label = True):
    result_dict = {}
    classifier_results = classifier(sequence_to_classify, candidate_labels, multi_label=multi_label)
    if type(classifier_results) != list:
        classifier_results = [classifier_results]
    for classifier_result in classifier_results:
        result_dict[classifier_result["sequence"]] = {label:label_prob for label,label_prob in zip(classifier_result["labels"], classifier_result["scores"])}
    return result_dict

def lock_classify_sentence(classifier):
    return lambda candidate_labels, sequence_to_classify, multi_label = True: classify_sentence(classifier=classifier, candidate_labels=candidate_labels, sequence_to_classify=sequence_to_classify, multi_label=multi_label)

def categories_classification_function(classification_model_function, categories_candidate_labels, texts, multi_label = True, sort_output = 0):
    classification_results = classify_sentence(classifier=classification_model_function, candidate_labels=categories_candidate_labels, sequence_to_classify=texts, multi_label=multi_label)
    final_classified_dict = {}
    if sort_output == -1:
        final_classified_dict = classification_results
        return final_classified_dict
    if sort_output == 0:
        for seq in texts:
            final_classified_dict[seq] = {label:classification_results[seq][label] for label in categories_candidate_labels}
        return final_classified_dict
    if sort_output == 1:
        for seq in texts:
            pre_sort = {label:classification_results[seq][label] for label in categories_candidate_labels}
            final_classified_dict[seq] = {label:label_pred for label, label_pred in sorted(pre_sort.items(), key = lambda dict_item: dict_item[1])}
        return final_classified_dict

## Resort Format Function
def categories_classification_additional_resort_function(seq_classified_dictionary, categories_candidate_labels, sort_output = 0, top_many = 5, limit_value = 0.5):
    if limit_value < 0:
        if sort_output == -1:
            limit_value = 0
        if sort_output == 0:
            limit_value = None
        if sort_output == 1:
            limit_value = 1
    resorted_classification_dict = {label:{} for label in categories_candidate_labels}
    for seq, label_to_label_pred_dict in seq_classified_dictionary.items():
        for label in categories_candidate_labels:
            if sort_output == -1:
                if label_to_label_pred_dict[label] >= limit_value:
                    resorted_classification_dict[label][seq] = label_to_label_pred_dict[label]
            if sort_output == 0:
                # limit_value no meaning here since no sorting so no >= or <= to base off
                resorted_classification_dict[label][seq] = label_to_label_pred_dict[label]
            if sort_output == 1:
                if label_to_label_pred_dict[label] <= limit_value:
                    resorted_classification_dict[label][seq] = label_to_label_pred_dict[label]
    if sort_output == -1:
        for label in categories_candidate_labels:
            resorted_classification_dict[label] = dict(sorted(resorted_classification_dict[label].items(), key = lambda dict_item: dict_item[1], reverse=True))
    if sort_output == 0:
        resorted_classification_dict = resorted_classification_dict
    if sort_output == 1:
        for label in categories_candidate_labels:
            resorted_classification_dict[label] = dict(sorted(resorted_classification_dict[label].items(), key = lambda dict_item: dict_item[1], reverse=False))
    
    if top_many >= 0:
        for label in categories_candidate_labels:
            resorted_classification_dict[label] = dict(list(resorted_classification_dict[label].items())[:top_many])
    return resorted_classification_dict

def lock_categories_classification_function(classification_model_function):
    return lambda categories_candidate_labels, texts, multi_label = True, sort_output = 0 : categories_classification_function(classification_model_function=classification_model_function, categories_candidate_labels=categories_candidate_labels, texts=texts, multi_label = multi_label, sort_output = sort_output)


def categories_classification_resorted_result_display(classification_resorted_dictionary_result, sort_display = 0, top_many = 5, limit_value = 0.5):
    if limit_value < 0:
        if sort_display == -1:
            limit_value = 0
        if sort_display == 0:
            limit_value = None
        if sort_display == 1:
            limit_value = 1
    if top_many > 0:
        for label, seq_pred_dict in classification_resorted_dictionary_result.items():
            print(f"Category: {label}")
            if sort_display == -1:
                for seq, pred in dict(sorted(list(seq_pred_dict.items()), key=lambda list_dict_tuple: list_dict_tuple[1], reverse=True)[:top_many]).items():
                    if pred >= limit_value:
                        print(f"{seq:65.65}: {pred:.5}")
            if sort_display == 0:
                ## if no sorting, then top xxx and limit yyy does not make sense so not applicable here
                for seq, pred in seq_pred_dict.items():
                    print(f"{seq:65.65}: {pred:.5}")
            if sort_display == 1:
                for seq, pred in dict(sorted(list(seq_pred_dict.items()), key=lambda list_dict_tuple: list_dict_tuple[1], reverse=False)[:top_many]).items():
                    if pred <= limit_value:
                        print(f"{seq:65.65}: {pred:.5}")
            print()
    else:
        for label, seq_pred_dict in classification_resorted_dictionary_result.items():
            print(f"Category: {label}")
            if sort_display == -1:
                for seq, pred in dict(sorted(seq_pred_dict.items(), key=lambda list_dict_tuple: list_dict_tuple[1], reverse=True)).items():
                    if pred >= limit_value:
                        print(f"{seq:65.65}: {pred:.5}")
            if sort_display == 0:
                ## if no sorting, then top xxx and limit yyy does not make sense so not applicable here
                for seq, pred in seq_pred_dict.items():
                    print(f"{seq:65.65}: {pred:.5}")
            if sort_display == 1:
                for seq, pred in dict(sorted(seq_pred_dict.items(), key=lambda list_dict_tuple: list_dict_tuple[1], reverse=False)).items():
                    if pred <= limit_value:
                        print(f"{seq:65.65}: {pred:.5}")
            print()

def categories_classification_additional_resort_cleaning_function(classification_resorted_dictionary_result, get_list = False, top_many_cat = 3, limit_value = 0.5):
    #return dict(list(dict(sorted(list(classification_resorted_dictionary_result.items()), key=lambda tuple_value_dict: list(tuple_value_dict[1].values())[0], reverse=True)).items())[:top_many_cat])
    cleaned_classification_resorted_dictionary_result = {}
    for label, seq_pred_dict in classification_resorted_dictionary_result.items():
        ## the "if" part and the "for" part is done so that if seq_pred_dict.items() is empty, then next(iter()) wont crash if solely use it!!
        """
        if len(seq_pred_dict) > 0:
            cleaned_classification_resorted_dictionary_result[label] = next(iter(seq_pred_dict.items()))
        """
        for seq, pred in seq_pred_dict.items():
            cleaned_classification_resorted_dictionary_result[label] = (seq, pred)
        ### if label dont have any that fits limit_value restriction, then the label wont appear in the dict at the end!!, not in this version at least!!!
    cleaned_classification_resorted_dictionary_result = dict(sorted(cleaned_classification_resorted_dictionary_result.items(), key=lambda dict_item: dict_item[1][1], reverse=True))
    if get_list:
        return list(cleaned_classification_resorted_dictionary_result.items())[:top_many_cat]
    return dict(list(cleaned_classification_resorted_dictionary_result.items())[:top_many_cat])


def cleaned_categories_classification_resorted_result_display(cleaned_classification_resorted_result, get_list):
    if get_list:
        for label, seq_pred_tuple in cleaned_classification_resorted_result:
            print(f"Category: {label}")
            print(f"{seq_pred_tuple[0]:65.65}: {seq_pred_tuple[1]:.5}")
            print()
    else:
        for label, seq_pred_tuple in cleaned_classification_resorted_result.items():
            print(f"Category: {label}")
            print(f"{seq_pred_tuple[0]:65.65}: {seq_pred_tuple[1]:.5}")
            print()

# Overall Combined Function (Similarity Comparison)

def split_and_compare(split_embed_function, compare_embed_function, categories, sentence_text, intermediate = False, graph = False, sort_compare = 0, display_split = True , display_end = True, sort_display = 0):
    splitted_sentence_text = semantic_segmentation_function(embedding_model_function=split_embed_function, sentence_text=sentence_text, intermediate_status=intermediate, graph_status=graph)
    if display_split:
        print(f"Splitted texts: {splitted_sentence_text}")
    compare_result = categories_similarity_comparison_function(embedding_model_function=compare_embed_function, categories=categories, texts=splitted_sentence_text, sort_output=sort_compare)
    if display_end:
        categories_similarity_result_display(compare_result, sort_display=sort_display)
    return splitted_sentence_text, compare_result
    

## Lock split and compare overall combined function
def lock_split_and_compare(split_embed_function, compare_embed_function):
    return lambda categories, sentence_text, intermediate = False, graph = False, sort_compare = 0, display_split = True, display_end = True, sort_display = 0: split_and_compare(split_embed_function=split_embed_function, compare_embed_function=compare_embed_function, categories=categories, sentence_text=sentence_text, intermediate=intermediate, graph=graph, sort_compare=sort_compare, display_split=display_split, display_end=display_end, sort_display=sort_display)
    # SyntaxError: positional argument follows keyword argument
    # return lambda categories, sentence_text, intermediate = False, graph = False, sort_compare = 0, display_end = True, sort_display = 0: split_and_compare(split_embed_function=split_embed_function, compare_embed_function=compare_embed_function, categories, sentence_text, intermediate = False, graph = False, sort_compare = 0, display_end = True, sort_display = 0)

### OR !!

def lock_split_and_compare(split_embed_function, compare_embed_function):
    def lockED_split_and_compare(categories, sentence_text, intermediate = False, graph = False, sort_compare = 0, display_split = True , display_end = True, sort_display = 0):
        return split_and_compare(split_embed_function, compare_embed_function, categories, sentence_text, intermediate = intermediate, graph = graph, sort_compare = sort_compare, display_split = display_split , display_end = display_end, sort_display = sort_display)
    return lockED_split_and_compare


def split_and_compare_wsub(split_embed_function, compare_embed_function, categories_wsub, sentence_text, intermediate = False, graph = False, sort_compare = 0, display_split = True , display_end = True, sort_display = 0):
    splitted_sentence_text = semantic_segmentation_function(embedding_model_function=split_embed_function, sentence_text=sentence_text, intermediate_status=intermediate, graph_status=graph)
    if display_split:
        print(f"Splitted texts: {splitted_sentence_text}")
    compare_result = categories_wsub_similarity_comparison_function(embedding_model_function=compare_embed_function, categories_wsub_dict=categories_wsub, texts=splitted_sentence_text, sort_output=sort_compare)
    if display_end:
        categories_wsub_similarity_result_display(compare_result, sort_display=sort_display)
    return splitted_sentence_text, compare_result

def lock_split_and_compare_wsub(split_embed_function, compare_embed_function):
    def lockED_split_and_compare_wsub(categories_wsub, sentence_text, intermediate = False, graph = False, sort_compare = 0, display_split = True , display_end = True, sort_display = 0):
        return split_and_compare_wsub(split_embed_function, compare_embed_function, categories_wsub=categories_wsub, sentence_text=sentence_text, intermediate = intermediate, graph = graph, sort_compare = sort_compare, display_split = display_split , display_end = display_end, sort_display = sort_display)
    return lockED_split_and_compare_wsub

def split_and_compare_wsub_top_limit(split_embed_function, compare_embed_function, categories_wsub, sentence_text, intermediate = False, graph = False, sort_compare = 0, display_split = True , display_end = True, top_many = 5, limit_value = 0.5):
    splitted_sentence_text = semantic_segmentation_function(embedding_model_function=split_embed_function, sentence_text=sentence_text, intermediate_status=intermediate, graph_status=graph)
    if display_split:
        print(f"Splitted texts: {splitted_sentence_text}")
    compare_result = categories_wsub_similarity_comparison_function(embedding_model_function=compare_embed_function, categories_wsub_dict=categories_wsub, texts=splitted_sentence_text, sort_output=sort_compare)
    if display_end:
        categories_wsub_similarity_result_display_top_limit(compare_result, top_many=top_many, limit_value=limit_value)
    return splitted_sentence_text, compare_result

def lock_split_and_compare_wsub_top_limit(split_embed_function, compare_embed_function):
    return lambda categories_wsub, sentence_text, intermediate = False, graph = False, sort_compare = 0, display_split = True , display_end = True, top_many = 5, limit_value = 0.5:split_and_compare_wsub_top_limit(split_embed_function=split_embed_function, compare_embed_function=compare_embed_function, categories_wsub=categories_wsub, sentence_text=sentence_text, intermediate = intermediate, graph = graph, sort_compare = sort_compare, display_split = display_split , display_end = display_end, top_many = top_many, limit_value = limit_value)

def split_and_compare_wsub_top_limit_cleaned(split_embed_function, compare_embed_function, categories_wsub, sentence_text, intermediate = False, graph = False, sort_compare = 0, get_inner_list = False, get_list = False, display_split = True , display_end = True, top_many_cat = 3, limit_value = 0.5, extra_clean_output=False):
    splitted_sentence_text = semantic_segmentation_function(embedding_model_function=split_embed_function, sentence_text=sentence_text, intermediate_status=intermediate, graph_status=graph)
    if display_split:
        print(f"Splitted texts: {splitted_sentence_text}")
    compare_result = categories_wsub_similarity_comparison_function(embedding_model_function=compare_embed_function, categories_wsub_dict=categories_wsub, texts=splitted_sentence_text, sort_output=sort_compare)
    resorted_compare_result = categories_wsub_similarity_comparison_resort_function(categories_wsub_similarity_comparison_result_dict=compare_result, get_inner_list=get_inner_list, sort_within_cat=-1, top_many_wsub=1, limit_value=limit_value) ## sort_within_cat=-1, top_many_wsub=1 are both need!! for the purpose of this cleaning up function part!!
    cleaned_resorted_compare_result = categories_wsub_similarity_comparison_resort_cleaning_function(resorted_categories_wsub_similarity_comparison_dict=resorted_compare_result, get_inner_list=get_inner_list, get_list=get_list, top_many_cat=top_many_cat)
    if display_end:
        cleaned_categories_wsub_similarity_comparison_resorted_result_display(cleaned_resorted_compare_result, get_list=get_list)
    if extra_clean_output:
        if get_list:
            return splitted_sentence_text, [(category, compare_sim_tuple[1]) for category, compare_sim_tuple in cleaned_resorted_compare_result]
        else:
            return splitted_sentence_text, {category:compare_sim_tuple[1] for category, compare_sim_tuple in cleaned_resorted_compare_result.items()}
    return splitted_sentence_text, cleaned_resorted_compare_result

def lock_split_and_compare_wsub_top_limit_cleaned(split_embed_function, compare_embed_function):
    return lambda categories_wsub, sentence_text, intermediate = False, graph = False, sort_compare = 0, get_inner_list = False, get_list = False, display_split = True , display_end = True, top_many_cat = 3, limit_value = 0.5, extra_clean_output=False: split_and_compare_wsub_top_limit_cleaned(split_embed_function=split_embed_function, compare_embed_function=compare_embed_function, categories_wsub=categories_wsub, sentence_text=sentence_text, intermediate = intermediate, graph = graph, sort_compare = sort_compare, get_inner_list = get_inner_list, get_list = get_list, display_split = display_split , display_end = display_end, top_many_cat = top_many_cat, limit_value = limit_value, extra_clean_output=extra_clean_output)

## Split and Classify, using Zero Shot Classification
def split_and_classify(split_embed_function, classify_function, candidate_possible_labels, sentence_text, intermediate = False, graph = False, multi_label=True, sort_classify = 0, additional_resort = True, display_split = True , display_end = True, sort_display = 0):
    splitted_sentence_text = semantic_segmentation_function(embedding_model_function=split_embed_function, sentence_text=sentence_text, intermediate_status=intermediate, graph_status=graph)
    if display_split:
        print(f"Splitted texts: {splitted_sentence_text}")
    classification_result = categories_classification_function(classification_model_function=classify_function, categories_candidate_labels=candidate_possible_labels, texts=splitted_sentence_text, multi_label=multi_label, sort_output=sort_classify)
    if additional_resort:
        resorted_classification_result = categories_classification_additional_resort_function(seq_classified_dictionary=classification_result, categories_candidate_labels=candidate_possible_labels, sort_output=sort_classify, top_many=-1, limit_value=0)
    if display_end:
        display_usage_resorted_classification_result = categories_classification_additional_resort_function(seq_classified_dictionary=classification_result, categories_candidate_labels=candidate_possible_labels, sort_output=0, top_many=-1, limit_value=-1)
        categories_classification_resorted_result_display(classification_resorted_dictionary_result=display_usage_resorted_classification_result, sort_display=sort_display, top_many=-1, limit_value=-1)
    if additional_resort:
        return splitted_sentence_text, resorted_classification_result
    return splitted_sentence_text, classification_result

def lock_split_and_classify(split_embed_function, classify_function):
    return lambda candidate_possible_labels, sentence_text, intermediate = False, graph = False, multi_label=True, sort_classify = 0, additional_resort = True, display_split = True , display_end = True, sort_display = 0: split_and_classify(split_embed_function=split_embed_function, classify_function=classify_function, candidate_possible_labels=candidate_possible_labels, sentence_text=sentence_text, intermediate = intermediate, graph = graph, multi_label=multi_label, sort_classify = sort_classify, additional_resort = additional_resort, display_split = display_split , display_end = display_end, sort_display = sort_display)

def split_and_classify_top_limit(split_embed_function, classify_function, candidate_possible_labels, sentence_text, intermediate = False, graph = False, multi_label=True, sort_classify = 0, additional_resort = True, display_split = True , display_end = True, sort_display = 0, top_many=5, limit_value=0.5):
    splitted_sentence_text = semantic_segmentation_function(embedding_model_function=split_embed_function, sentence_text=sentence_text, intermediate_status=intermediate, graph_status=graph)
    if display_split:
        print(f"Splitted texts: {splitted_sentence_text}")
    classification_result = categories_classification_function(classification_model_function=classify_function, categories_candidate_labels=candidate_possible_labels, texts=splitted_sentence_text, multi_label=multi_label, sort_output=sort_classify)
    if additional_resort:
        resorted_classification_result = categories_classification_additional_resort_function(seq_classified_dictionary=classification_result, categories_candidate_labels=candidate_possible_labels, sort_output=sort_classify, top_many=top_many, limit_value=limit_value)
    if display_end:
        display_usage_resorted_classification_result = categories_classification_additional_resort_function(seq_classified_dictionary=classification_result, categories_candidate_labels=candidate_possible_labels, sort_output=0, top_many=-1, limit_value=-1)
        categories_classification_resorted_result_display(classification_resorted_dictionary_result=display_usage_resorted_classification_result, sort_display=sort_display, top_many=top_many, limit_value=limit_value)
    if additional_resort:
        return splitted_sentence_text, resorted_classification_result
    return splitted_sentence_text, classification_result

def lock_split_and_classify_top_limit(split_embed_function, classify_function):
    return lambda candidate_possible_labels, sentence_text, intermediate = False, graph = False, multi_label=True, sort_classify = 0, additional_resort = True, display_split = True , display_end = True, sort_display = 0, top_many=5, limit_value=0.5: split_and_classify_top_limit(split_embed_function=split_embed_function, classify_function=classify_function, candidate_possible_labels=candidate_possible_labels, sentence_text=sentence_text, intermediate = intermediate, graph = graph, multi_label=multi_label, sort_classify = sort_classify, additional_resort = additional_resort, display_split = display_split , display_end = display_end, sort_display = sort_display, top_many=top_many, limit_value=limit_value)

def split_and_classify_top_limit_cleaned(split_embed_function, classify_function, candidate_possible_labels, sentence_text, intermediate = False, graph = False, multi_label=True, get_list = False, display_split = True , display_end = True, top_many_cat=3, limit_value=0.5, extra_clean_output=False):
    splitted_sentence_text = semantic_segmentation_function(embedding_model_function=split_embed_function, sentence_text=sentence_text, intermediate_status=intermediate, graph_status=graph)
    if display_split:
        print(f"Splitted texts: {splitted_sentence_text}")
    classification_result = categories_classification_function(classification_model_function=classify_function, categories_candidate_labels=candidate_possible_labels, texts=splitted_sentence_text, multi_label=multi_label)
    resorted_classification_result = categories_classification_additional_resort_function(seq_classified_dictionary=classification_result, categories_candidate_labels=candidate_possible_labels, sort_output=-1, top_many=1, limit_value=limit_value) # the sort_output = -1 and top_many = 1 is both impt!!!
    cleaned_classification_resorted_result = categories_classification_additional_resort_cleaning_function(classification_resorted_dictionary_result=resorted_classification_result, get_list=get_list, top_many_cat=top_many_cat, limit_value=limit_value)

    if display_end:
        cleaned_categories_classification_resorted_result_display(cleaned_classification_resorted_result=cleaned_classification_resorted_result, get_list=get_list)
    
    if extra_clean_output:
        if get_list:
            return splitted_sentence_text, [(category_label, seq_pred_tuple[1]) for category_label, seq_pred_tuple in cleaned_classification_resorted_result]
        else:
            return splitted_sentence_text, {category_label:seq_pred_tuple[1] for category_label, seq_pred_tuple in cleaned_classification_resorted_result.items()}
    return splitted_sentence_text, cleaned_classification_resorted_result

def lock_split_and_classify_top_limit_cleaned(split_embed_function, classify_function):
    return lambda candidate_possible_labels, sentence_text, intermediate = False, graph = False, multi_label=True, get_list=False, display_split = True , display_end = True, top_many_cat=3, limit_value=0.5, extra_clean_output=False: split_and_classify_top_limit_cleaned(split_embed_function=split_embed_function, classify_function=classify_function, candidate_possible_labels=candidate_possible_labels, sentence_text=sentence_text, intermediate = intermediate, graph = graph, multi_label=multi_label, get_list=get_list, display_split = display_split , display_end = display_end, top_many_cat=top_many_cat, limit_value=limit_value, extra_clean_output=extra_clean_output)

# NOT YET WITH ZERO SHOT CLASSIFIER FUNCTION!

### maybe also rename the functions to be like xxx_emb, or smth easier then later on use

## Embedding Functions (xxx_embedding)

### sentence-transformers/all-MiniLM-L6-v2

from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F

#Mean Pooling - Take attention mask into account for correct averaging
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0] #First element of model_output contains all token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    """
    print(attention_mask.shape, attention_mask)
    print(attention_mask.unsqueeze(-1).shape, attention_mask.unsqueeze(-1))
    print(input_mask_expanded)
    print(len(input_mask_expanded), token_embeddings.size(), input_mask_expanded.size())
    """
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

"""
# Sentences we want sentence embeddings for
sentences = ['This is an example sentence', 'Each sentence is converted']
"""

# Load model from HuggingFace Hub
pt_transformers_L6_v2_tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
pt_transformers_L6_v2_model = AutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')

def all_MiniLM_L6_v2_embedding(sentences):
    
    # Tokenize sentences
    encoded_input = pt_transformers_L6_v2_tokenizer(sentences, padding=True, truncation=True, return_tensors='pt')

    # Compute token embeddings
    with torch.no_grad():
        model_output = pt_transformers_L6_v2_model(**encoded_input)

    # Perform pooling
    sentence_embeddings = mean_pooling(model_output, encoded_input['attention_mask'])

    # Normalize embeddings
    sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)

    #print("Sentence embeddings:")
    #print(sentence_embeddings)
    '''
    if len(sentence_embeddings) == 1:
        return sentence_embeddings[0]
    return sentence_embeddings
    '''
    return sentence_embeddings
"""
### sentence-transformers/all-MiniLM-L12-v2

from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F

#Mean Pooling - Take attention mask into account for correct averaging
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0] #First element of model_output contains all token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    '''
    print(attention_mask.shape, attention_mask)
    print(attention_mask.unsqueeze(-1).shape, attention_mask.unsqueeze(-1))
    print(input_mask_expanded)
    print(len(input_mask_expanded), token_embeddings.size(), input_mask_expanded.size())
    '''
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)


# Load model from HuggingFace Hub
pt_transformers_L12_v2_tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L12-v2')
pt_transformers_L12_v2_model = AutoModel.from_pretrained('sentence-transformers/all-MiniLM-L12-v2')

def all_MiniLM_L12_v2_embedding(sentences):
    
    # Tokenize sentences
    encoded_input = pt_transformers_L12_v2_tokenizer(sentences, padding=True, truncation=True, return_tensors='pt')

    # Compute token embeddings
    with torch.no_grad():
        model_output = pt_transformers_L12_v2_model(**encoded_input)

    # Perform pooling
    sentence_embeddings = mean_pooling(model_output, encoded_input['attention_mask'])

    # Normalize embeddings
    sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)

    #print("Sentence embeddings:")
    #print(sentence_embeddings)
    '''
    if len(sentence_embeddings) == 1:
        return sentence_embeddings[0]
    return sentence_embeddings
    '''
    return sentence_embeddings

### BAAI/bge-large-en-v1.5

from transformers import AutoTokenizer, AutoModel
import torch

# Load model from HuggingFace Hub
#tokenizer = AutoTokenizer.from_pretrained('BAAI/bge-large-zh-v1.5')
#model = AutoModel.from_pretrained('BAAI/bge-large-zh-v1.5')
tokenizer_bge = AutoTokenizer.from_pretrained("BAAI/bge-large-en-v1.5")
model_bge = AutoModel.from_pretrained("BAAI/bge-large-en-v1.5")

model_bge.eval()

def bge_large_v1_5_embedding(sentenceS): ## already normalised due to "torch.nn.functional.normalize" function
    # Tokenize sentences
    encoded_input = tokenizer_bge(sentenceS, padding=True, truncation=True, return_tensors='pt')
    # for s2p(short query to long passage) retrieval task, add an instruction to query (not add instruction for passages)
    # encoded_input = tokenizer([instruction + q for q in queries], padding=True, truncation=True, return_tensors='pt')

    # Compute token embeddings
    with torch.no_grad():
        model_output = model_bge(**encoded_input)
        # Perform pooling. In this case, cls pooling.
        sentenceS_embeddings = model_output[0][:, 0]
    # normalize embeddings
    sentenceS_embeddings = torch.nn.functional.normalize(sentenceS_embeddings, p=2, dim=1)
    #print("SentenceS embeddings:", sentenceS_embeddings)
    '''
    if len(sentenceS_embeddings) == 1:
        return sentenceS_embeddings[0]
    return sentenceS_embeddings ## if not input a list of sentences, then just one
    '''
    return sentenceS_embeddings

### facebook/bart-large

from transformers import BartTokenizer, BartModel
import torch

bart_large_tokenizer = BartTokenizer.from_pretrained('facebook/bart-large')
bart_large_model = BartModel.from_pretrained('facebook/bart-large')
def bart_cls_emb(sentences):
    inputs = bart_large_tokenizer(sentences, return_tensors="pt")
    outputs = bart_large_model(**inputs)

    last_hidden_states = outputs.last_hidden_state
    return last_hidden_states[:, 0]

def bart_mean_emb(sentences):
    inputs = bart_large_tokenizer(sentences, return_tensors="pt")
    outputs = bart_large_model(**inputs)

    last_hidden_states = outputs.last_hidden_state
    input_mask_expanded = inputs["attention_mask"].unsqueeze(-1).expand(last_hidden_states.size()).float()

    return torch.sum(last_hidden_states * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
def bart_pad_cls_emb(sentences):
    inputs = bart_large_tokenizer(sentences, return_tensors="pt", padding=True)
    outputs = bart_large_model(**inputs)

    last_hidden_states = outputs.last_hidden_state
    return last_hidden_states[:, 0]

def bart_pad_mean_emb(sentences):
    inputs = bart_large_tokenizer(sentences, return_tensors="pt", padding=True)
    outputs = bart_large_model(**inputs)

    last_hidden_states = outputs.last_hidden_state
    input_mask_expanded = inputs["attention_mask"].unsqueeze(-1).expand(last_hidden_states.size()).float()

    return torch.sum(last_hidden_states * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)


def bart_large_cls_embedding(sentences):
    inputs = bart_large_tokenizer(sentences, return_tensors="pt", padding=True)
    outputs = bart_large_model(**inputs)

    last_hidden_states = outputs.last_hidden_state
    return last_hidden_states[:, 0]

def bart_large_mean_embedding(sentences):
    inputs = bart_large_tokenizer(sentences, return_tensors="pt", padding=True)
    outputs = bart_large_model(**inputs)

    last_hidden_states = outputs.last_hidden_state
    input_mask_expanded = inputs["attention_mask"].unsqueeze(-1).expand(last_hidden_states.size()).float()

    return torch.sum(last_hidden_states * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

### google/canine-c

from transformers import CanineTokenizer, CanineModel

Canine_model = CanineModel.from_pretrained('google/canine-c')
Canine_tokenizer = CanineTokenizer.from_pretrained('google/canine-c')

def g_canine_embedding(sentences_input):
    #sentences_input = ["Life is like a box of chocolates.", "You never know what you gonna get."]
    encoding = Canine_tokenizer(sentences_input, padding="longest", truncation=True, return_tensors="pt")

    outputs = Canine_model(**encoding) # forward pass
    pooled_output = outputs.pooler_output
    #print(pooled_output)
    sequence_output = outputs.last_hidden_state
    
    '''
    sentence_cls_emb = mean_pooling(outputs, encoding["attention_mask"])
    sentence_cls_emb = F.normalize(sentence_cls_emb, p=2, dim=1)

    if len(sentence_cls_emb) == 1:
        return sentence_cls_emb[0]
    return sentence_cls_emb
    '''
    
    '''
    if len(sequence_output) == 1:
        return sequence_output[0][0]
    return sequence_output[:, 0]
    '''
    return sequence_output[:, 0]

### mixedbread-ai/mxbai-embed-large-v1

from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim
from sentence_transformers.quantization import quantize_embeddings

# 1. Specify preffered dimensions
mxbai_v1_dimensions = 512

# 2. load model
mxbai_v1_model = SentenceTransformer("mixedbread-ai/mxbai-embed-large-v1", truncate_dim=mxbai_v1_dimensions)

def mxbai_large_v1_embedding(sentences):
    # For retrieval you need to pass this prompt.
    query = 'Represent this sentence for searching relevant passages: A man is eating a piece of bread'

    docs = sentences

    # 2. Encode
    embeddings = mxbai_v1_model.encode(docs)

    # Optional: Quantize the embeddings
    #binary_embeddings = quantize_embeddings(embeddings, precision="ubinary")

    #similarities = cos_sim(embeddings[0], embeddings[1:])
    #print('similarities:', similarities)
    return embeddings

### sentence-transformers/all-mpnet-base-v2

from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F

#Mean Pooling - Take attention mask into account for correct averaging
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0] #First element of model_output contains all token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

'''
# Sentences we want sentence embeddings for
sentences = ['This is an example sentence', 'Each sentence is converted']
'''

# Load model from HuggingFace Hub
all_mpnet_base_v2_tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-mpnet-base-v2')
all_mpnet_base_v2_model = AutoModel.from_pretrained('sentence-transformers/all-mpnet-base-v2')

def all_mpnet_base_v2_embedding(sentences):
    # Tokenize sentences
    encoded_input = all_mpnet_base_v2_tokenizer(sentences, padding=True, truncation=True, return_tensors='pt')

    # Compute token embeddings
    with torch.no_grad():
        model_output = all_mpnet_base_v2_model(**encoded_input)

    # Perform pooling
    sentence_embeddings = mean_pooling(model_output, encoded_input['attention_mask'])

    # Normalize embeddings
    sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)

    return sentence_embeddings

### sentence-transformers/paraphrase-MiniLM-L6-v2

from sentence_transformers import SentenceTransformer

paraphrase_MiniLM_L6_v2_model = SentenceTransformer('sentence-transformers/paraphrase-MiniLM-L6-v2')

def paraphrase_MiniLM_L6_v2_embedding(sentences):
    embeddings = paraphrase_MiniLM_L6_v2_model.encode(sentences)
    return embeddings

### sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

from sentence_transformers import SentenceTransformer

paraphrase_multilingual_MiniLM_L12_v2_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
def paraphrase_multilingual_MiniLM_L12_v2_embedding(sentences):
    embeddings = paraphrase_multilingual_MiniLM_L12_v2_model.encode(sentences)
    return embeddings

### Alibaba-NLP/gte-large-en-v1.5

# Requires sentence_transformers>=2.7.0

from sentence_transformers import SentenceTransformer

gte_large_en_v1_5_model = SentenceTransformer('Alibaba-NLP/gte-large-en-v1.5', trust_remote_code=True)

def gte_large_en_v1_5_embedding(sentences):
    embeddings = gte_large_en_v1_5_model.encode(sentences)
    return embeddings

### nomic-ai/nomic-embed-text-v1.5

import torch.nn.functional as F
from sentence_transformers import SentenceTransformer
!pip install einops

nomic_embed_text_v1_5_model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)

def nomic_embed_text_v1_5_embedding(sentences):
    matryoshka_dim = 512
    if type(sentences) != list:
        sentences = [sentences]
    sentences = [("search_document: " + sentence) for sentence in sentences]
    embeddings = nomic_embed_text_v1_5_model.encode(sentences, convert_to_tensor=True)
    embeddings = F.layer_norm(embeddings, normalized_shape=(embeddings.shape[1],))
    embeddings = embeddings[:, :matryoshka_dim]
    embeddings = F.normalize(embeddings, p=2, dim=1)
    return embeddings
"""
## Zero-Shot Classification Functions (xxx_classifier)

### facebook/bart-large-mnli

from transformers import pipeline
"""
bart_mnli_classifier = pipeline("zero-shot-classification",
                      model="facebook/bart-large-mnli")
"""

bart_mnli_classifier_pipeline = pipeline("zero-shot-classification",
                    model="facebook/bart-large-mnli")

"""
def bart_mnli_classifier(*classifier_input, **keyword_args):
    if "multi_label" in keyword_args:
        return bart_mnli_classifier_pipeline(*classifier_input, multi_label=keyword_args["multi_label"])
    else:
        return bart_mnli_classifier_pipeline(*classifier_input)
"""

## above works but this is just cleaner since i know only got multi_label argument being used here!!
def bart_mnli_classifier(*classifier_input, multi_label = False):
    return bart_mnli_classifier_pipeline(*classifier_input, multi_label=multi_label)
"""

### cross-encoder/nli-roberta-base

from transformers import pipeline

nli_roberta_base_classifier_pipeline = pipeline("zero-shot-classification", model='cross-encoder/nli-roberta-base')


def nli_roberta_base_classifier(*classifier_input, multi_label = False):
    return nli_roberta_base_classifier_pipeline(*classifier_input, multi_label=multi_label)

### MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli

#!pip install transformers[sentencepiece]
from transformers import pipeline
deberta_v3_base_mnli_fever_anli_classifier_pipeline = pipeline("zero-shot-classification", model="MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli")

def deberta_v3_base_mnli_fever_anli_classifier(*classifier_input, multi_label=False):
    return deberta_v3_base_mnli_fever_anli_classifier_pipeline(*classifier_input, multi_label=multi_label)
"""
# Setup Data and Variables 
"""
embedding_functions_list = [
    all_MiniLM_L6_v2_embedding,
    all_MiniLM_L12_v2_embedding,
    bge_large_v1_5_embedding,
    bart_large_cls_embedding,
    bart_large_mean_embedding,
    g_canine_embedding,
    mxbai_large_v1_embedding,
    all_mpnet_base_v2_embedding,
    paraphrase_MiniLM_L6_v2_embedding,
    paraphrase_multilingual_MiniLM_L12_v2_embedding,
    gte_large_en_v1_5_embedding,
    nomic_embed_text_v1_5_embedding
]

classification_functions_list = [
    bart_mnli_classifier,
    nli_roberta_base_classifier,
    deberta_v3_base_mnli_fever_anli_classifier
]
"""
categories_for_embedding = {
"Tax principle": [""],
"List of benefits-in-kind granted administrative concession or exempt from income tax": [""],
"Flexible benefits scheme": [""],
"Accommodation provided to an employee/director": [""],
"Furniture and fittings and related benefits": [""],
"Serviced apartment": [""],
"Hotel": [""],
"Housing allowance": [""],
"Home leave passage": [""],
"Cash payment in-lieu of home leave passage": [""],
"Passage provided for business purpose": [""],
"Passage provided when taking up employment and upon termination": [""],
"Award for passing exams": [""],
"Bursary": [""],
"Innovation/ Improvement": [""],
"Long service/ retirement": [""],
"Recognition of good service": [""],
"Recognition of work performance": [""],
"Referral": [""],
"Zero/ low MC": [""],
"Food, door gifts and lucky draw prizes": [""],
"Dinner and dance held overseas": [""],
"Interest benefits arising from interest-free or subsidised interest loan": [""],
"Interest benefits on loans to company directors": [""],
"Waiver of principal sum": [""],
"Car provided": [""],
"Commercial vehicle provided": [""],
"Car park charges": [""],
"ERP charges": [""],
"Mileage for business usage": [""],
"Taxes, repairs and maintenance expenses of employee's own vehicle": [""],
"Subsidy for a child in childcare center": [""],
"Subsidy for a child in student care": [""],
"Employer's contributions relating to employment in Singapore": [""],
"Contributions made from 1 Jan 2004 relating to employment outside Singapore": [""],
"Contributions relating to director's fees": [""],
"Festive occasions": [""],
"Special occasions": [""],
"Bereavement": [""],
"Insurance premium": [""],
"Group medical insurance": [""],
"Group insurance policy": [""],
"Travel insurance covering the period of business travel": [""],
"Work injury compensation": [""],
"Death gratuities/ Injuries or disability payments/ Workmen compensation": [""],
"Gratuity for completing number of years of service": [""],
"Payment to induce a person to join the company": [""],
"Retrenchment payment to compensate loss of employment": [""],
"Retirement benefits": [""],
"Payment made to employee for entering into covenant": [""],
"Salary in lieu of notice/notice pay": [""],
"Fixed monthly meal allowance": [""],
"Working overtime - allowance paid or reimbursement made": [""],
"Free or subsidised food and drinks": [""],
"Reimbursement for employees and dependants": [""],
"Medical benefit based on gender or age": [""],
"Medical insurance": [""],
"Transport expenses to see doctor": [""],
"Absentee payroll under Skills Redevelopment programme": [""],
"Conditional payments made in advance": [""],
"Encashment of unutilised leave": [""],
"Inflation bonus": [""],
"Laundry allowance": [""],
"Maternity leave benefit": [""],
"NSman pay": [""],
"Skills Development Levy (SDL)": [""],
"Contributions made by employer to employee's Supplementary Retirement Scheme (SRS) account": [""],
"Relocation allowance": [""],
"Contributions made by employer to any pension/provident fund outside Singapore": [""],
"Employment Assistance Payment (EAP)": [""],
"Overseas holiday trips": [""],
"Holiday reimbursement": [""],
"Overtime allowance": [""],
"Overtime claims": [""],
"Per diem allowance": [""],
"Per diem reimbursement": [""],
"Combination of allowance and reimbursement": [""],
"Parking fees at the airport": [""],
"Travel insurance premium": [""],
"Travel between home and airport": [""],
"Payment for warm clothing": [""],
"Payment for luggage": [""],
"Facilities owned by employer": [""],
"Reimbursement for renting chalet": [""],
"Corporate passes to places of interest": [""],
"Staff discount offered by employer or its related entities": [""],
"Staff discount extended to employee's family members, relatives and friends": [""],
"Employee Share Option (ESOP)": [""],
"Other forms of Employee Share Ownership (ESOW) Plan": [""],
"Club": [""],
"Personal membership to gym/ fitness centre/ sports club/ union": [""],
"Handphone/ Internet reimbursement": [""],
"Handphone allowance": [""],
"Cable for TV": [""],
"Professional bodies": [""],
"Income tax borne fully or partially by employer": [""],
"Fixed sum of tax allowance": [""],
"Subsidies for course fees and training fees for staff development": [""],
"Scholarship payments": [""],
"Subsidy of course fees or scholarship given as reward for service rendered": [""],
"Overseas training": [""],
"Fixed monthly allowance": [""],
"Expenses for discharging official duties": [""],
"Mileage on private cars": [""],
"Working overtime": [""],
"Shuttle bus": [""],
"Taxi trip between home and office": [""],
"Travel between home and business venue": [""],
"Trips made by employee between home and external business venues": [""]
}


categories_for_classification = [
"Tax principle",
"List of benefits-in-kind granted administrative concession or exempt from income tax",
"Flexible benefits scheme",
"Accommodation provided to an employee/director",
"Furniture and fittings and related benefits",
"Serviced apartment",
"Hotel",
"Housing allowance",
"Home leave passage",
"Cash payment in-lieu of home leave passage",
"Passage provided for business purpose",
"Passage provided when taking up employment and upon termination",
"Award for passing exams",
"Bursary",
"Innovation/ Improvement",
"Long service/ retirement",
"Recognition of good service",
"Recognition of work performance",
"Referral",
"Zero/ low MC",
"Food, door gifts and lucky draw prizes",
"Dinner and dance held overseas",
"Interest benefits arising from interest-free or subsidised interest loan",
"Interest benefits on loans to company directors",
"Waiver of principal sum",
"Car provided",
"Commercial vehicle provided",
"Car park charges",
"ERP charges",
"Mileage for business usage",
"Taxes, repairs and maintenance expenses of employee's own vehicle",
"Subsidy for a child in childcare center",
"Subsidy for a child in student care",
"Employer's contributions relating to employment in Singapore",
"Contributions made from 1 Jan 2004 relating to employment outside Singapore",
"Contributions relating to director's fees",
"Festive occasions",
"Special occasions",
"Bereavement",
"Insurance premium",
"Group medical insurance",
"Group insurance policy",
"Travel insurance covering the period of business travel",
"Work injury compensation",
"Death gratuities/ Injuries or disability payments/ Workmen compensation",
"Gratuity for completing number of years of service",
"Payment to induce a person to join the company",
"Retrenchment payment to compensate loss of employment",
"Retirement benefits",
"Payment made to employee for entering into covenant",
"Salary in lieu of notice/notice pay",
"Fixed monthly meal allowance",
"Working overtime - allowance paid or reimbursement made",
"Free or subsidised food and drinks",
"Reimbursement for employees and dependants",
"Medical benefit based on gender or age",
"Medical insurance",
"Transport expenses to see doctor",
"Absentee payroll under Skills Redevelopment programme",
"Conditional payments made in advance",
"Encashment of unutilised leave",
"Inflation bonus",
"Laundry allowance",
"Maternity leave benefit",
"NSman pay",
"Skills Development Levy (SDL)",
"Contributions made by employer to employee's Supplementary Retirement Scheme (SRS) account",
"Relocation allowance",
"Contributions made by employer to any pension/provident fund outside Singapore",
"Employment Assistance Payment (EAP)",
"Overseas holiday trips",
"Holiday reimbursement",
"Overtime allowance",
"Overtime claims",
"Per diem allowance",
"Per diem reimbursement",
"Combination of allowance and reimbursement",
"Parking fees at the airport",
"Travel insurance premium",
"Travel between home and airport",
"Payment for warm clothing",
"Payment for luggage",
"Facilities owned by employer",
"Reimbursement for renting chalet",
"Corporate passes to places of interest",
"Staff discount offered by employer or its related entities",
"Staff discount extended to employee's family members, relatives and friends",
"Employee Share Option (ESOP)",
"Other forms of Employee Share Ownership (ESOW) Plan",
"Club",
"Personal membership to gym/ fitness centre/ sports club/ union",
"Handphone/ Internet reimbursement",
"Handphone allowance",
"Cable for TV",
"Professional bodies",
"Income tax borne fully or partially by employer",
"Fixed sum of tax allowance",
"Subsidies for course fees and training fees for staff development",
"Scholarship payments",
"Subsidy of course fees or scholarship given as reward for service rendered",
"Overseas training",
"Fixed monthly allowance",
"Expenses for discharging official duties",
"Mileage on private cars",
"Working overtime",
"Shuttle bus",
"Taxi trip between home and office",
"Travel between home and airport",
"Travel between home and business venue",
"Trips made by employee between home and external business venues"
]



broad_categories_for_embedding = {
'General Information': [""],
'Accommodation and Related Benefits': [""],
'Air Passage': [""],
'Awards': [""],
'Benefits relating to Corporate Events': [""],
'Benefits relating to Loans': [""],
'Car and Car-related Benefits': [""],
'Childcare Subsidy': [""],
'Central Provident Fund (CPF) Contributions': [""],
'Gifts': [""],
'Insurance Premium': [""],
'Lump Sum Payment': [""],
'Meal Payments and Food Provided': [""],
'Medical and Dental Care': [""],
'Other Payments': [""],
'Overseas Holiday Trips': [""],
'Overtime Payments': [""],
'Per Diem': [""],
'Social and Recreational Facilities': [""],
'Staff Discount': [""],
'Stock Options': [""],
'Subscriptions': [""],
'Tax Borne by Employer': [""],
'Training': [""],
'Transport': [""]
}

broad_categories_for_classification = [
'General Information',
'Accommodation and Related Benefits',
'Air Passage',
'Awards',
'Benefits relating to Corporate Events',
'Benefits relating to Loans',
'Car and Car-related Benefits',
'Childcare Subsidy',
'Central Provident Fund (CPF) Contributions',
'Gifts',
'Insurance Premium',
'Lump Sum Payment',
'Meal Payments and Food Provided',
'Medical and Dental Care',
'Other Payments',
'Overseas Holiday Trips',
'Overtime Payments',
'Per Diem',
'Social and Recreational Facilities',
'Staff Discount',
'Stock Options',
'Subscriptions',
'Tax Borne by Employer',
'Training',
'Transport'
]

# Start here for running

## run from here!

# Original

## Original before made all ' become " yeaaaa

{'Tax principle': [''],
 'List of benefits-in-kind granted administrative concession or exempt from income tax': [''],
 'Flexible benefits scheme': [''],
 'Accommodation provided to an employee/director': [''],
 'Furniture and fittings and related benefits': [''],
 'Serviced apartment': [''],
 'Hotel': [''],
 'Housing allowance': [''],
 'Home leave passage': [''],
 'Cash payment in-lieu of home leave passage': [''],
 'Passage provided for business purpose': [''],
 'Passage provided when taking up employment and upon termination': [''],
 'Award for passing exams': [''],
 'Bursary': [''],
 'Innovation/ Improvement': [''],
 'Long service/ retirement': [''],
 'Recognition of good service': [''],
 'Recognition of work performance': [''],
 'Referral': [''],
 'Zero/ low MC': [''],
 'Food, door gifts and lucky draw prizes': [''],
 'Dinner and dance held overseas': [''],
 'Interest benefits arising from interest-free or subsidised interest loan': [''],
 'Interest benefits on loans to company directors': [''],
 'Waiver of principal sum': [''],
 'Car provided': [''],
 'Commercial vehicle provided': [''],
 'Car park charges': [''],
 'ERP charges': [''],
 'Mileage for business usage': [''],
 "Taxes, repairs and maintenance expenses of employee's own vehicle": [''],
 'Subsidy for a child in childcare center': [''],
 'Subsidy for a child in student care': [''],
 "Employer's contributions relating to employment in Singapore": [''],
 'Contributions made from 1 Jan 2004 relating to employment outside Singapore': [''],
 "Contributions relating to director's fees": [''],
 'Festive occasions': [''],
 'Special occasions': [''],
 'Bereavement': [''],
 'Insurance premium': [''],
 'Group medical insurance': [''],
 'Group insurance policy': [''],
 'Travel insurance covering the period of business travel': [''],
 'Work injury compensation': [''],
 'Death gratuities/ Injuries or disability payments/ Workmen compensation': [''],
 'Gratuity for completing number of years of service': [''],
 'Payment to induce a person to join the company': [''],
 'Retrenchment payment to compensate loss of employment': [''],
 'Retirement benefits': [''],
 'Payment made to employee for entering into covenant': [''],
 'Salary in lieu of notice/notice pay': [''],
 'Fixed monthly meal allowance': [''],
 'Working overtime - allowance paid or reimbursement made': [''],
 'Free or subsidised food and drinks': [''],
 'Reimbursement for employees and dependants': [''],
 'Medical benefit based on gender or age': [''],
 'Medical insurance': [''],
 'Transport expenses to see doctor': [''],
 'Absentee payroll under Skills Redevelopment programme': [''],
 'Conditional payments made in advance': [''],
 'Encashment of unutilised leave': [''],
 'Inflation bonus': [''],
 'Laundry allowance': [''],
 'Maternity leave benefit': [''],
 'NSman pay': [''],
 'Skills Development Levy (SDL)': [''],
 "Contributions made by employer to employee's Supplementary Retirement Scheme (SRS) account": [''],
 'Relocation allowance': [''],
 'Contributions made by employer to any pension/provident fund outside Singapore': [''],
 'Employment Assistance Payment (EAP)': [''],
 'Overseas holiday trips': [''],
 'Holiday reimbursement': [''],
 'Overtime allowance': [''],
 'Overtime claims': [''],
 'Per diem allowance': [''],
 'Per diem reimbursement': [''],
 'Combination of allowance and reimbursement': [''],
 'Parking fees at the airport': [''],
 'Travel insurance premium': [''],
 'Travel between home and airport': [''],
 'Payment for warm clothing': [''],
 'Payment for luggage': [''],
 'Facilities owned by employer': [''],
 'Reimbursement for renting chalet': [''],
 'Corporate passes to places of interest': [''],
 'Staff discount offered by employer or its related entities': [''],
 "Staff discount extended to employee's family members, relatives and friends": [''],
 'Employee Share Option (ESOP)': [''],
 'Other forms of Employee Share Ownership (ESOW) Plan': [''],
 'Club': [''],
 'Personal membership to gym/ fitness centre/ sports club/ union': [''],
 'Handphone/ Internet reimbursement': [''],
 'Handphone allowance': [''],
 'Cable for TV': [''],
 'Professional bodies': [''],
 'Income tax borne fully or partially by employer\xa0': [''],
 'Fixed sum of tax allowance': [''],
 'Subsidies for course fees and training fees for staff development': [''],
 'Scholarship payments': [''],
 'Subsidy of course fees or scholarship given as reward for service rendered': [''],
 'Overseas training': [''],
 'Fixed monthly allowance': [''],
 'Expenses for discharging official duties': [''],
 'Mileage on private cars': [''],
 'Working overtime': [''],
 'Shuttle bus': [''],
 'Taxi trip between home and office': [''],
 'Travel between home and business venue': [''],
 'Trips made by employee between home and external business venues': ['']}


['Tax principle',
 'List of benefits-in-kind granted administrative concession or exempt from income tax',
 'Flexible benefits scheme',
 'Accommodation provided to an employee/director',
 'Furniture and fittings and related benefits',
 'Serviced apartment',
 'Hotel',
 'Housing allowance',
 'Home leave passage',
 'Cash payment in-lieu of home leave passage',
 'Passage provided for business purpose',
 'Passage provided when taking up employment and upon termination',
 'Award for passing exams',
 'Bursary',
 'Innovation/ Improvement',
 'Long service/ retirement',
 'Recognition of good service',
 'Recognition of work performance',
 'Referral',
 'Zero/ low MC',
 'Food, door gifts and lucky draw prizes',
 'Dinner and dance held overseas',
 'Interest benefits arising from interest-free or subsidised interest loan',
 'Interest benefits on loans to company directors',
 'Waiver of principal sum',
 'Car provided',
 'Commercial vehicle provided',
 'Car park charges',
 'ERP charges',
 'Mileage for business usage',
 "Taxes, repairs and maintenance expenses of employee's own vehicle",
 'Subsidy for a child in childcare center',
 'Subsidy for a child in student care',
 "Employer's contributions relating to employment in Singapore",
 'Contributions made from 1 Jan 2004 relating to employment outside Singapore',
 "Contributions relating to director's fees",
 'Festive occasions',
 'Special occasions',
 'Bereavement',
 'Insurance premium',
 'Group medical insurance',
 'Group insurance policy',
 'Travel insurance covering the period of business travel',
 'Work injury compensation',
 'Death gratuities/ Injuries or disability payments/ Workmen compensation',
 'Gratuity for completing number of years of service',
 'Payment to induce a person to join the company',
 'Retrenchment payment to compensate loss of employment',
 'Retirement benefits',
 'Payment made to employee for entering into covenant',
 'Salary in lieu of notice/notice pay',
 'Fixed monthly meal allowance',
 'Working overtime - allowance paid or reimbursement made',
 'Free or subsidised food and drinks',
 'Reimbursement for employees and dependants',
 'Medical benefit based on gender or age',
 'Medical insurance',
 'Transport expenses to see doctor',
 'Absentee payroll under Skills Redevelopment programme',
 'Conditional payments made in advance',
 'Encashment of unutilised leave',
 'Inflation bonus',
 'Laundry allowance',
 'Maternity leave benefit',
 'NSman pay',
 'Skills Development Levy (SDL)',
 "Contributions made by employer to employee's Supplementary Retirement Scheme (SRS) account",
 'Relocation allowance',
 'Contributions made by employer to any pension/provident fund outside Singapore',
 'Employment Assistance Payment (EAP)',
 'Overseas holiday trips',
 'Holiday reimbursement',
 'Overtime allowance',
 'Overtime claims',
 'Per diem allowance',
 'Per diem reimbursement',
 'Combination of allowance and reimbursement',
 'Parking fees at the airport',
 'Travel insurance premium',
 'Travel between home and airport',
 'Payment for warm clothing',
 'Payment for luggage',
 'Facilities owned by employer',
 'Reimbursement for renting chalet',
 'Corporate passes to places of interest',
 'Staff discount offered by employer or its related entities',
 "Staff discount extended to employee's family members, relatives and friends",
 'Employee Share Option (ESOP)',
 'Other forms of Employee Share Ownership (ESOW) Plan',
 'Club',
 'Personal membership to gym/ fitness centre/ sports club/ union',
 'Handphone/ Internet reimbursement',
 'Handphone allowance',
 'Cable for TV',
 'Professional bodies',
 'Income tax borne fully or partially by employer\xa0',
 'Fixed sum of tax allowance',
 'Subsidies for course fees and training fees for staff development',
 'Scholarship payments',
 'Subsidy of course fees or scholarship given as reward for service rendered',
 'Overseas training',
 'Fixed monthly allowance',
 'Expenses for discharging official duties',
 'Mileage on private cars',
 'Working overtime',
 'Shuttle bus',
 'Taxi trip between home and office',
 'Travel between home and airport',
 'Travel between home and business venue',
 'Trips made by employee between home and external business venues']


# Test Sentences

sentences = ["",
             "",
             ""
]

import os
import sys
import json
def process_extracted_folder_freetext(extracted_raw_files_folder = "Extracted Raw Data"):
    form_extracted_data_name = "form_extracted_data.json"
    
    ## not dictionary since no unique key to give/use
    free_text_res = {}
    
    cur_dir = os.path.realpath(".")
    
    ##extracted_raw_files_folder = ("Extracted "+ raw_files_folder) ## argument fitted
    
    extracted_data_folder = os.path.join(cur_dir, extracted_raw_files_folder)
    if not os.path.exists(extracted_data_folder):
        print(f"No extract folder to process from!!")
        sys.exit(1)
    
    
    companies_folders = next(os.walk(("./"+extracted_raw_files_folder)))[1]
    #list_of_raw_companies_folders_abs_path = [os.path.join(cur_dir, raw_files_folder, companies_folder) for companies_folder in companies_folders]
    for company_folder in companies_folders:
        extracted_company_folder_abs_path = os.path.join(cur_dir, extracted_raw_files_folder, company_folder)
        extracted_company_data_file_abs_path = os.path.join(extracted_company_folder_abs_path, form_extracted_data_name)
        print(extracted_company_data_file_abs_path)
        free_text_res[extracted_company_data_file_abs_path] = []
        if not os.path.exists(extracted_company_data_file_abs_path):
            continue
        with open(extracted_company_data_file_abs_path, "r") as extracted_company_data_file:
            loaded_in_extracted_data = json.load(extracted_company_data_file)
        free_text_content_list = loaded_in_extracted_data["Free Text"]
        print(free_text_content_list)
        
        free_text_cats = []
        for free_text_content in free_text_content_list:
            splitted_text, classify_res = split_and_classify_top_limit_cleaned(all_MiniLM_L6_v2_embedding, bart_mnli_classifier, candidate_possible_labels=categories_for_classification, sentence_text=free_text_content, top_many_cat=5, get_list=True, extra_clean_output=True)
            for_output_cat_list = [cat_to_comp_pred_dict[0] for cat_to_comp_pred_dict in classify_res]
            for_output_cat_list_trim = for_output_cat_list[:5]
            free_text_res[extracted_company_data_file_abs_path].append(for_output_cat_list_trim)
            
            free_text_cats += for_output_cat_list_trim
        
        post_process_extracted_company_data_file_abs_path = os.path.join(extracted_company_folder_abs_path, ("Classified " + form_extracted_data_name))

        with open(post_process_extracted_company_data_file_abs_path, "w") as proccesed_extracted_data_file:
            loaded_in_extracted_data["Classified Free Text Categories"] = free_text_cats
            json.dump(loaded_in_extracted_data, proccesed_extracted_data_file)
        
        """
        #print(msg_files_abs_path_list)
        count = 0
        form_extracted_data_name = "form_extracted_data.json"
        for msg_file_abs_path in msg_files_abs_path_list:
            
            count += 1
            if count > 1:
                form_extracted_data_name = f"form_extracted_data_{count}.json"
                print("Multiple Copies of Msg?!?!")
            extracted_data = extract_data_from_msg_file(msg_file_abs_path)
            if extracted_data == None:
                continue
            processed_extracted_data = process_extracted_data(extracted_data)
            #print(processed_extracted_data)
            #print()
            ## not dictionary since no unique key to give/use
            extracted_data_list.append(processed_extracted_data)
            output_extracted_file(extracted_raw_company_folder_abs_path, form_extracted_data_name, processed_extracted_data)
        """
    return free_text_res

#process_extracted_folder_freetext()

## maybe top x(up to, since not every point got value) for EACH POINT, better? not overall?
## join together with other one maybe too

## but need pick model, else too time consuming unless can do on server?

import getopt
def OverallProgram():
    extracted_raw_files_folder = "Extracted Raw Data"
    opts, argss = getopt.getopt(sys.argv[1:], "e:") ## split by pair of 2s
    for opt, val in opts:
        if opt == "-e":
            extracted_raw_files_folder = val.strip(".\\").strip('"')
    if not os.path.exists(os.path.join(os.path.realpath("./"), extracted_raw_files_folder)):
        print(f"The path '{os.path.join(os.path.realpath("./"), extracted_raw_files_folder)}' does not exists?!?!")
        print("Have a extracted-companies-files-overall-folder named 'Extracted Raw Data'")
        print("OR")
        print("Usage: " + sys.argv[0] + " -e extracted-companies-files-overall-folder")
        sys.exit(1)
    return process_extracted_folder_freetext(extracted_raw_files_folder=extracted_raw_files_folder)

OverallProgram()
#process_extracted_folder_freetext(extracted_raw_files_folder = "Extracted (Raw/Companies) Data")
# -*- coding: utf-8 -*-
__author__ = 'Administrator'

# -*- coding: utf-8 -*-
import os
curr_dir = os.path.dirname(os.path.abspath(__file__))
filtered_words_txt_path = os.path.join(curr_dir,'filtered_words.txt')
import chardet

def filter_replace(string):
    string = string.decode("utf-8")
    filtered_words = []
    with open(filtered_words_txt_path) as filtered_words_txt:
        lines = filtered_words_txt.readlines()
        for line in lines:
            filtered_words.append(line.strip().decode("utf-8"))
    return replace(filtered_words, string)

def replace(filtered_words,string):
    new_string = string
    for words in filtered_words:
        if words in string:
            new_string = string.replace(words,"*"*len(words))
    if new_string == string:
        return new_string
    else:
        return replace(filtered_words,new_string)

if __name__ == '__main__':
    print filter_replace(raw_input("Type:"))
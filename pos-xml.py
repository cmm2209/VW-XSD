"""
This function opens an RNNTagger-ed plain text file and converts it to a customized xml file.
"""
import pandas as pd
import lxml

def converter(file):
    new_file_name = file.replace('.txt', '.xml') 
    with open (file, 'r', encoding='utf-8') as file:
        reader = pd.read_table(file, sep=' +', engine='python')
        df = pd.DataFrame(reader)
    df.to_xml(new_file_name, index=False, root_name='body', row_name='w', attr_cols=['pos', 'norm', 'lemma'], elem_cols=['token'], na_rep='', stylesheet='https://raw.githubusercontent.com/cmm2209/VW-XSD/refs/heads/main/pos-to-xml-cleaner.xsl')
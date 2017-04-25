#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 24 10:58:07 2017

@author: srikant
"""
import json
import sys
import os

import pandas as pd

import get_github_details as ghd
import get_stackoverflow_details as sod


MASTER_DIR = "master_data"
MASTER_FILE = "Applicant Master Data 2017.xlsx"
OUTPUT_FILE = MASTER_FILE.replace('Master', 'Github and Stackoverflow')

def read_master_data(filepath):
    '''Read Applicant Master Data,
    drop rows where either emailid or name is missing,
    return dataframe of master data.
    '''
    # read master appliant information
    try:
        master_df_raw = pd.read_excel(filepath, sheetname='Sheet1')
    except FileNotFoundError as err:
        print("\nCouldnt find '{}' \n".format(filepath))
        sys.exit(0)
    # offset for consistency in row numbers
    offset = 2
    master_df_raw.index = master_df_raw.index + offset
    # drop rows where both names or emails are available
    name_and_email_available = master_df_raw['NAME'].notnull() & master_df_raw['EMAIL'].notnull()
    master_df = master_df_raw[name_and_email_available]
    return master_df


def write_df_to_excel(df, filepath):
    '''write df to excelfile in a proper order
    '''
    # order of columns for excel output
    cols_1 = ['master_details',
              'github_id_details',
              'stackoverflow_id_details',
              'github_overall_rating',
              'stackoverflow_overall_rating']
    cols_2 = ['github_expertise_ratings']
    cols_3 = ['stackoverflow_expertise_ratings']
    # check if columns names are in df, keep columns that are in df.columns.level[0]
    for cols_list in [cols_1, cols_2, cols_3]:
        cols_list = [col for col in cols_list if col in df.columns.levels[0]]
    ordered_df_list = [
            df[cols_1],
            df[cols_2].sortlevel(axis=1),
            df[cols_3].sortlevel(axis=1)
    ]
    df = pd.concat(ordered_df_list, axis=1)
    # write dataframe to excel file
    df.to_excel(filepath, index_label='index')


def get_github_stackorf_details(g, so, master_data_df):
    '''get github and stackoverflow details for each of the applicant in the master_data_df
    '''
    all_details_dict = {}
    master_details_dict = {}
    github_ratings_dict = {}
    stackovf_ratings_dict = {}
    ratings_dict = {}
    for i,row in master_data_df.iterrows():
        user_name = row['NAME']
        user_email = row['EMAIL'].split('|')[0]
        print('\nSl.No {:3d}: [{}], [{}]'.format(i, user_name, user_email))
        # applicant master details - as part of output
        master_details_dict[i] = {
                ('master_details','name'): user_name,
                ('master_details','email'): user_email
        }
        
        
        # GITHUB
        # search in Github for user matching the email_id
        search_string = user_email
        github_matches = ghd.find_matching_users(g, search_string)
        try:
            # get github data for the matching user
            github_details = ghd.get_github_profiles(github_matches, search_string)
        except SystemExit:
            github_details = {}
        # get the github ratings df
        github_ratings_df = github_details.get(user_email,{}).get('overall_rating', pd.DataFrame())
        # convert df to dict
        github_ratings_dict[i] = github_ratings_df.to_dict().get('value',{})
        
        
        # STACKOVERFLOW
        search_string = user_name
        search_kw = {'inname':search_string}
        stackovf_matches = sod.find_matching_users(so, search_kw)[0:1]
        try:
            stackovf_details = sod.get_stackoverflow_profiles(stackovf_matches, search_kw)
        except SystemExit:
            stackovf_details = {}
        stackovf_ratings_df = stackovf_details.get(search_string,{}).get('ratings_df', pd.DataFrame())
        stackovf_ratings_dict[i] = stackovf_ratings_df.to_dict().get('value',{})
        
        
        # append all ratings df to applicant master details
        ratings_dict[i] = {
                **master_details_dict[i],
                **github_ratings_dict[i],
                **stackovf_ratings_dict[i]
        }
    # all dicts
    all_details_dict = {
            'ratings_dict': ratings_dict,
            'master_details_dict': master_details_dict,
            'github_ratings_dict': github_ratings_dict,
            'stackovf_ratings_dict': stackovf_ratings_dict
    }
    return all_details_dict


if __name__ == '__main__':
    # read master data from excel file
    master_data_df = read_master_data(filepath = os.path.join(MASTER_DIR, MASTER_FILE))
    # initialize github object
    g = ghd.init_github_object()
    # initialize stackoverflow object
    so = sod.init_stackoverflow_object()
    # get applicant github stackoverflow data
    data_df = master_data_df
    all_details_dict = get_github_stackorf_details(g, so, data_df)
    ratings_details = all_details_dict['ratings_dict']
    # convert dict of all applicant details to a dataframe
    applicants_df = pd.DataFrame.from_dict(ratings_details, orient='index')
    # write to excel file
    output_file = os.path.join(MASTER_DIR, OUTPUT_FILE)
    write_df_to_excel(applicants_df, output_file)

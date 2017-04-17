#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 14 16:08:54 2017

@author: srikant
"""

import json
import sys
import os
import argparse

import stackexchange
import nltk
import pandas as pd

# add nltk_data folder to the list of NLTK library paths
nltk.data.path.insert(0,'nltk_data')
# set of stopwords
STOPWORDS = set(nltk.corpus.stopwords.words('english'))


def init_stackoverflow_object(auth_key=None):
    '''Get authentication header using authentication key provided 
    either as part of command line or stored in stackoverflow_auth.py.
    '''
    # if auth token is not provided as an argv
    if auth_key == None:
        # check if auth token file exists, get token if it does
        try:
            import stackoverflow_auth
            print("\nReading auth_token from stackoverflow_auth.py")
            auth_key = stackoverflow_auth.AUTH_KEY
        # proceed without auth if there is no auth token file
        except ImportError:
            print("\nAuthentication token not provided; Can't find stackoverflow_auth.py; Trying without authentication.")
            print("Rate limit without authentication is 300 requests/day")
            print("Store stackoverflow AUTH_KEY in stackoverflow_auth.py to avoid rate limitation")
            auth_key == None
        # initialize stackoverflow object
    so = stackexchange.Site(stackexchange.StackOverflow, auth_key)
    return so


def convert_datetime_cols(df_all, date_cols):
    ''' Convert datetime string to datetime objects
    '''
    for col in date_cols:
        df_all[col] = pd.to_datetime(df_all[col], unit='s', infer_datetime_format=True)
    return df_all


def get_top_answers_tags(user):
    '''Get top answer tags and tag details
    '''
    print('\tGetting tags details ...')
    tags_dfs = []
    cols = ['tag_name', 'answer_count', 'answer_score', 'question_count', 'question_score']
    # top answer tags
    top_tags = user.top_answer_tags.fetch()
    for tag in top_tags:
        df = pd.io.json.json_normalize(tag.json)
        tags_dfs.append(df)
    try:
        df_all = pd.concat(tags_dfs, axis=0).sort_values(by = 'answer_count', ascending=False)
    except ValueError:
        df_all = pd.DataFrame(columns=cols)
    return df_all[cols]
    

def parse_user_details(user):
    '''For given user get all the user's details and parse the information to a dataframe.
    '''
    print('\tGetting user details ...')
    # get all the user details and parse info to dataframe
    user_json = user.json
    user_df = pd.io.json.json_normalize(user_json)
    drop_cols = [col for col in user_df.columns if '_params_' in col]
    user_df.drop(drop_cols, axis=1, inplace=True)
    # get tag details
    tags_df = get_top_answers_tags(user)
    # convert datetime columns to datetime objects
    date_cols=['creation_date', 'last_access_date', 'last_modified_date']
    for col in date_cols:
        user_df[col] = pd.to_datetime(user_df[col], unit='s', infer_datetime_format=True)
    # transpose user_df
    user_df = user_df.T
    # cleanup tags_df
    tags_df = tags_df.set_index('tag_name', drop=True)
    return user_df, tags_df


def get_stackoverflow_profiles(matching_users, search_string):
    '''Get all details for matching users and save as excel file
    '''
    n_matches = len(matching_users)
    # exit if there are no matches
    if n_matches == 0:
        print("Found 0 users matching '{}'; exiting\n".format(search_string))
        sys.exit(0)
    # get details of all the matching users, parse the details to dataframe, write it to excel file
    else:
        print("Found {} user(s) matching '{}'.\nFetching details ...".format(n_matches, search_string))
        for i,user in enumerate(matching_users):
            # get all repos for the user and output to a dataframe
            print("\tGetting user_df and tags_df for '{}' ...".format(user.display_name))
            user_df, tags_df = parse_user_details(user)
            # write dataframe to excel file
            file_name = '{}_{}_stackoverflow.xlsx'.format(search_string.replace(' ','_'), str(i+1))
            file_path = os.path.join('stackoverflow_output', file_name)
            excel_writer = pd.ExcelWriter(file_path)
            user_df.to_excel(excel_writer, sheet_name='overall_details', header=False)
            tags_df.to_excel(excel_writer, sheet_name='top_answers_tags')
            excel_writer.save()
            print('\tDetails saved to {}'.format(file_name),'\n')
    return user_df, tags_df


if __name__ == '__main__':
    # get search_string, user_id and auth_key from command line arguments
    description = "Script to get job candidate's stackoverflow profile"
    epilog = '''Provide either USER_ID or SEARCH_STRING.
                USER_ID will be used if both are provided'''
    parser = argparse.ArgumentParser(description=description, epilog=epilog)
    parser.add_argument("-i", dest="user_id", type=int,
                        help="candidate's stackoverflow user id (number)")
    parser.add_argument("-s", dest="search_string", type=str,
                        help="string to search for in users' display-name fields")
    parser.add_argument("-a", dest="auth_key", type=str, nargs="?",
                        help="stackoverflow authentication key (to avoid rate limits)")
    args = parser.parse_args()
    user_id = args.user_id
    search_string = args.search_string
    auth_key = args.auth_key
    # initialize SO object
    so = init_stackoverflow_object(auth_key = auth_key)
    # build search criterial kw
    if user_id is not None:
        search_kw = {'ids':user_id}
    elif search_string is not None:
        search_kw = {'inname':search_string}
    else:
        parser.error('Requires either USER_ID or SEARCH_STRING')
    # find all users matching the search criteria
    matching_users = so.users(**search_kw)
    # get all details for matching users and save as tabular form to excel sheet
    user_df, tags_df = get_stackoverflow_profiles(matching_users, str(user_id or search_string))
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
import numpy as np

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
            print("\n", '''Authentication token not provided; Can't find stackoverflow_auth.py;
                  Trying without authentication.''')
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
        df_all = pd.concat(tags_dfs, axis=0)[cols]
    except ValueError:
        df_all = pd.DataFrame(columns=cols)
    # row totals
    df_all['value'] = df_all.sum(axis=1)
    # column totals
    sum_row = df_all.sum(axis=0)
    sum_row.ix['tag_name'] = 'OVERALL'
    df_tags = df_all.append(sum_row, ignore_index=True)
    # return df sorted by row totals
    return df_tags.sort_values(by = 'value', ascending=False)


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
    user_df.index.name = 'field'
    user_df.rename(columns={0:'value'}, inplace=True)
    # cleanup tags_df
    tags_df = tags_df.set_index('tag_name', drop=True)
    return user_df, tags_df


def apply_func_wgt_bias(x, ops):
    ''' Returns a_f * func( x * a_x + b_x) + b_f
    '''
    func = ops.get('func',float)
    a_x = ops.get('a_x',1)
    a_f = ops.get('a_f',1)
    b_x = ops.get('b_x',0)
    b_f = ops.get('b_f',0)
    result = a_f * func( x * a_x + b_x) + b_f
    return result


def overall_rating(user_df, tags_df):
    '''Get a tabulated form for user details, general ratings, overall rating, top tag ratings
    '''
    user_id_fields = ['display_name', 'user_id', 'age', 'location']
    general_rating_fields = ['accept_rate', 'reputation', 'badge_counts.bronze',
                             'badge_counts.silver', 'badge_counts.gold']
    ratings_df = user_df.loc[user_id_fields + general_rating_fields].copy()
    # append user details
    ratings_df.loc[user_id_fields,'field_type'] = 'user_details'
    # append geneal ratings
    ratings_df.loc[general_rating_fields, 'field_type'] = 'general_ratings'
    ratings_df['value'] = ratings_df['value'].fillna(0)
    # calculate overall rating as SUM( a_f*func(a_x*x + b_x) + b_f)
    ops = {
        'accept_rate': {'func':np.exp, 'a_x':0.05, 'a_f':1, 'b_x':0, 'b_f':-1},
        'badge_counts.bronze': {'func':np.abs, 'a_x':1, 'a_f':1, 'b_x':0, 'b_f':0},
        'badge_counts.silver': {'func':np.abs, 'a_x':1, 'a_f':1, 'b_x':0, 'b_f':0},
        'badge_counts.gold': {'func':np.abs, 'a_x':1, 'a_f':1, 'b_x':0, 'b_f':0},
        'reputation': {'func':np.log, 'a_x':1, 'a_f':100, 'b_x':0, 'b_f':1}
    }
    ratings = [apply_func_wgt_bias(ratings_df.loc[key,'value'], opr) for key,opr in ops.items()]
    overall_rating = int(sum(ratings))
    # append overall rating
    ratings_df.loc['overall_rating', 'value'] = overall_rating
    ratings_df.loc['overall_rating', 'field_type'] = 'overall_rating'
    # append tags
    top_tags_df = tags_df['value'].head(20).to_frame()
    top_tags_df['field_type'] = 'expertise_ratings'
    ratings_df = ratings_df.append(top_tags_df)
    ratings_df.index.name = 'field'
    ratings_df = ratings_df.set_index(['field_type',ratings_df.index])
    return ratings_df


def get_stackoverflow_profiles(matching_users, search_kw):
    '''Get all details for matching users and save as excel file
    '''
    n_matches = len(matching_users)
    search_term = list(search_kw.values())[0]
    users_dict = {}
    # exit if there are no matches
    if n_matches == 0:
        print("Found 0 users matching '{}'; exiting\n".format(search_term))
        sys.exit(0)
    # get details of all the matching users, parse the details to dataframe, write it to excel file
    else:
        print("Found {} user(s) matching '{}'.\nFetching details ...".format(n_matches,search_term))
        for i,user in enumerate(matching_users):
            # get all repos for the user and output to a dataframe
            print("\tGetting user_df and tags_df for '{}' ...".format(user.display_name))
            user_df, tags_df = parse_user_details(user)
            # get overall score
            ratings_df = overall_rating(user_df, tags_df)
            # write dataframes to excel file
            file_name = '{}_{}_stackoverflow.xlsx'.format(search_term.replace(' ','_'), str(i+1))
            file_path = os.path.join('stackoverflow_output', file_name)
            excel_writer = pd.ExcelWriter(file_path)
            ratings_df.to_excel(excel_writer, sheet_name='overall_ratings')
            user_df.to_excel(excel_writer, sheet_name='user_details', header=False)
            tags_df.to_excel(excel_writer, sheet_name='top_answers_tags')
            excel_writer.save()
            print('\tDetails saved to {}'.format(file_name),'\n')
            users_dict[user.display_name] = {
                'user_df': user_df,
                'tags_df': tags_df,
                'ratings_df': ratings_df
            }
    return users_dict


def find_matching_users(search_kw, auth_key):
    # initialize SO object
    so = init_stackoverflow_object(auth_key = auth_key)
    # find all users matching the search criteria
    matching_users = so.users(**search_kw)
    return matching_users

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
    # build search criterial kw
    if user_id is not None:
        search_kw = {'ids':user_id}
    elif search_string is not None:
        search_kw = {'inname':search_string}
    else:
        parser.error('Requires either USER_ID or SEARCH_STRING')
    # get matching users
    matching_users = find_matching_users(search_kw, auth_key)
    # get all details for matching users and save as tabular form to excel sheet
    users_dict = get_stackoverflow_profiles(matching_users, search_kw)

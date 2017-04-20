#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 13 11:14:34 2017

@author: srikant
"""

import json
import sys
import os
import argparse

import nltk
import pandas as pd
import numpy as np
from github import Github
from pandas.io.json import json_normalize

# add nltk_data folder to the list of NLTK library paths
nltk.data.path.insert(0,'nltk_data')
# set of stopwords
STOPWORDS = set(nltk.corpus.stopwords.words('english'))


def get_keywords(readme):
    tokens_all = nltk.word_tokenize(readme)
    tokens_set = set(tokens_all)
    tokens_alpha = [s.lower() for s in tokens_set if s.isalpha()]
    tokens_nostop = set(tokens_alpha) - STOPWORDS
    return list(tokens_nostop)


def parse_contributions(df_repo, user, repo):
    '''Extract user's contribution for the specified repo
    '''
    # get list of all contributions
    contribs_list = repo.get_contributors()
    # dict of {user:contributions} for the repo
    contribs_dict = {contrib.login : contrib.contributions for contrib in contribs_list}
    # get user's contribution %
    sum_contribs = sum(contrib for contrib in contribs_dict.values())
    try:
        user_contrib = 100*contribs_dict[user.login]/sum_contribs
    except (ZeroDivisionError, KeyError):
        user_contrib = 0
    # add contribution and owner details to the repo dataframe
    df_repo['user_contrib_pct'] = user_contrib
    df_repo['contributions'] = sum_contribs
    df_repo['owner'] = repo.owner.login
    print("\t\t{:3.0f}% contribution in '{}' ({})".format(user_contrib, repo.full_name,
                                                          repo.language))
    return df_repo


def parse_readme(df_repo, user, repo):
    '''Extract keywords from readme
    '''
    try:
        readme_data = repo.get_readme()
        readme_binstr = readme_data.decoded_content
        readme = readme_binstr.decode('utf-8')
        keywords_list = get_keywords(readme)
    except:
        keywords_list = []
    df_repo['readme_keywords'] = ','.join(keywords_list)
    return df_repo


def add_user_details(df_repo, user, fields):
    '''Add specified user details to tabular data
    '''
    for field in fields:
        try:
            df_repo['user_' + field] = getattr(user, field)
        except AttributeError:
            continue
    return df_repo


def convert_datetime_cols(df_all, date_cols):
    ''' Convert datetime string to datetime objects
    '''
    for col in date_cols:
        df_all[col] = pd.to_datetime(df_all[col],infer_datetime_format=True)
    return df_all


def parse_user_details(user):
    '''For each of the users matching the search string,
    get all the user repos and parse the information to a dataframe.
    '''
    repos_dfs = []
    # get all repos for user
    repos = list(user.get_repos(type='all'))
    n_repos = len(repos)
    print('\t{}, {}, {}, {:2d} repos'.format(user.name, user.login, user.email, n_repos))
    if n_repos == 0:
        return pd.DataFrame()
    # for each repo, get contirbution details for the user and parse the info to dataframe
    for repo in repos:
        # json to dataframe using builtin pandas method
        df_repo = json_normalize(repo.raw_data) # 30 sec
        # parse contribution
        df_repo = parse_contributions(df_repo, user, repo) # 1 min
        # parse readme readme
        df_repo = parse_readme(df_repo, user, repo) # 30 sec
        # append user id details to the repo dataframe
        df_repo = add_user_details(df_repo, user, fields = ['login','name','email','score'])
        # add it to the list of repo dataframes
        repos_dfs.append(df_repo)
    # combine all the repo dataframes for each of the matching users
    df_all = pd.concat(repos_dfs, axis=0, ignore_index=True)
    # convert datetime columns to datetime objects
    df_all = convert_datetime_cols(df_all, date_cols=['updated_at','created_at', 'pushed_at'])
    # return combined dataframe
    return df_all


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


def apply_row_ops(row, row_ops):
    list_vals = [apply_func_wgt_bias(row[col], ops) for col,ops in row_ops.items()]
    result = sum(list_vals)
    return result


def get_overall_rating(repo_details, user):
    '''Get overall rating based on all details
    '''
    isowner = repo_details['owner'] == repo_details['user_login']
    repo_details['isowner'] = isowner.astype(int)
    # assign a rating for each repo
    # calculate repo's overall rating as SUM( a_f*func(a_x*x + b_x) + b_f)
    repo_ops = {
            'forks_count': {'func':np.abs, 'a_x':2, 'a_f':1, 'b_x':0, 'b_f':0},
            'stargazers_count': {'func':np.abs, 'a_x':1, 'a_f':1, 'b_x':0, 'b_f':0},
            'contributions': {'func':np.log, 'a_x':1, 'a_f':1, 'b_x':1, 'b_f':0}
    }
    repo_details['repo_rating'] = repo_details.apply(lambda x: apply_row_ops(x,repo_ops), axis=1)
    owner_frac = 0
    user_contrib = 0.01*repo_details['user_contrib_pct'] * (1 - owner_frac*repo_details['isowner'])
    repo_details['user_rating'] = repo_details['repo_rating'] * user_contrib
    # derive overall rating
    overall_rating = pd.pivot_table(repo_details, index='language', values='user_rating',
                                    aggfunc=sum, margins=True, margins_name='OVERALL').to_frame()
    overall_rating.index.name = 'field'
    overall_rating = overall_rating.rename(columns={'user_rating':'value'})
    overall_rating['field_type'] = 'rating_by_language'
    # add user details
    details = ['name','login','email']
    user_details= {idx:getattr(user,idx) for idx in details}
    user_df = pd.Series(user_details, name='value').to_frame()
    user_df.index.name = 'field'
    user_df['field_type'] = 'user_details'
    overall_rating = user_df.append(overall_rating.sort_values(by='value', ascending=False))
    overall_rating = overall_rating.set_index(['field_type', overall_rating.index])
    # all details
    all_details = repo_details
    return overall_rating, all_details


def get_github_profiles(matching_users, search_string, fields):
    '''Get all details for matching users and save as excel file
    '''
    n_matches = len(matching_users)
    search_term = search_string.replace('@','[at]').replace(' ','_')
    users_dict = {}
    # exit if there are no matches
    if n_matches == 0:
        print("Found 0 users matching '{}'; exiting\n".format(search_string))
        sys.exit(0)
    # get details of all the matching users, parse the details to dataframe, write it to excel file
    else:
        print("Found {} users matching '{}'.\nFetching details ...".format(n_matches,search_string))
        # for each user get all the user repos and parse info to dataframe
        for i,user in enumerate(matching_users):
            print("\tGetting details for '{}' ...".format(user.name))
            repo_details = parse_user_details(user)
            # check if there are no repos
            if repo_details.shape[0] == 0:
                print('\tNo repos for {}, nothing to save.'.format(user.login))
                continue
            else:
                # get overall ratings
                overall_rating, all_details = get_overall_rating(repo_details, user)
                 # write dataframe to excel file
                file_name = '{}_{}_github.xlsx'.format(search_term, str(i+1))
                file_path = os.path.join('github_output', file_name)
                excel_writer = pd.ExcelWriter(file_path)
                overall_rating.to_excel(excel_writer, sheet_name='overall_rating')
                all_details[fields].to_excel(excel_writer, sheet_name='main_details')
                all_details.to_excel(excel_writer, sheet_name='all_details')
                excel_writer.save()
                print('\tDetails saved to {}'.format(file_name),'\n')
                users_dict[user.login] = {'all_details':all_details,
                                          'overall_rating':overall_rating}
    return users_dict


def init_github_object(auth_token=None):
    '''Get authentication header using auth token in auth_file.
    Returns auth_header for GET requests
    '''
    # if auth token is not provided as an argv
    if auth_token == None:
        # check if auth token file exists, get token if it does
        try:
            import github_auth
            print("\nReading auth_token from github_auth.py")
            auth_token = github_auth.AUTH_TOKEN
        # proceed without auth if there is no auth token file
        except ImportError:
            print("\n", '''Authentication token not provided; Can't find github_auth.py;
                  Trying without authentication.''')
            print("Rate limit without authentication is 60 requests/hour")
            print("Store github AUTH_TOKEN in github_auth.py to avoid rate limitation")
            auth_token == None
        # initialize github object
    g = Github(login_or_token=auth_token, timeout=60)
    return g


if __name__ == '__main__':
    # get search_string and auth_token from command line arguments
    usage = "\npython3 get_github_details.py"
    description = "Script to get job candidate's github profile"
    parser = argparse.ArgumentParser(usage=usage, description=description)
    parser.add_argument("-s", dest="search_string", type=str,
                        help="substring to search for in users' name/email/login fields")
    parser.add_argument("-a", dest="auth_token", type=str, nargs="?",
                        help="github authentication token (to avoid rate limitation)")
    args = parser.parse_args()
    search_string = args.search_string
    auth_token = args.auth_token
    # initialize github object
    g = init_github_object(auth_token=auth_token)
    # find all users matchin the search string
    search_result = g.search_users(search_string, sort='repositories' ,order='desc')
    matching_users = list(search_result)
    # fields to output to excel file
    fields = ['user_name', 'user_login', 'user_email', 'full_name', 'owner',
              'html_url', 'language', 'updated_at', 'fork', 'forks_count', 'stargazers_count',
              'contributions', 'user_contrib_pct','readme_keywords','repo_rating','user_rating']
    # get all details for mathing users and save specified fields to excel sheet
    users_dict = get_github_profiles(matching_users, search_string, fields)

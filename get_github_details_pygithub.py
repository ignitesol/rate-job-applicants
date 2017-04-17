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
    df_repo['contribution %'] = user_contrib
    df_repo['contributions'] = contribs_dict.get(user.login,0)
    df_repo['owner'] = repo.owner.login
    print("\t\t{:3.0f}% contribution in '{}' ({})".format(user_contrib, repo.full_name, repo.language))
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


def parse_user_details(matching_usersr):
    '''For each of the users matching the search string,
    get all the user repos and parse the information to a dataframe.
    '''
    repos_dfs = []
    # for each user get all the user repos and parse info to dataframe
    for user in matching_users:
        # get all repos for user
        repos = list(user.get_repos(type='all'))
        n_repos = len(repos)
        print('\t{}, {}, {}, {:2d} repos'.format(user.name, user.login, user.email, n_repos))
        if n_repos == 0:
            continue
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
    try:
        df_all = pd.concat(repos_dfs, axis=0, ignore_index=True)
    except ValueError:
        print('No repos found for any of the matching users.\n')
        sys.exit(0)
    # convert datetime columns to datetime objects
    df_all = convert_datetime_cols(df_all, date_cols=['updated_at','created_at', 'pushed_at'])
    # return combined dataframe
    return df_all


def get_github_profiles(matching_users, search_string, fields):
    '''Get all details for matching users and save as excel file
    '''
    n_matches = len(matching_users)
    # exit if there are no matches
    if n_matches == 0:
        print("Found 0 users matching '{}'; exiting\n".format(search_string))
        sys.exit(0)
    # get details of all the matching users, parse the details to dataframe, write it to excel file
    else:
        print("Found {} users matching '{}'.\nFetching details ...".format(n_matches,search_string))
        # get all repos for the user and output to a dataframe
        tabulated_details = parse_user_details(matching_users)[fields]
        # write dataframe to excel file
        file_name = os.path.join('github_output',search_string.replace(' ','_') + '_github.xlsx')
        tabulated_details.to_excel(file_name)
        print('Details saved to {}'.format(file_name),'\n')
    return tabulated_details


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
            print("\nAuthentication token not provided; Can't find github_auth.py; Trying without authentication.")
            print("Rate limit without authentication is 60 requests/hour")
            print("Store github AUTH_TOKEN in github_auth.py to avoid rate limitation")
            auth_token == None
        # initialize github object
    g = Github(login_or_token=auth_token, timeout=60)
    return g


if __name__ == '__main__':
    # get search_string and auth_token from command line arguments
    usage = "\npython3 get_github_details_pygithub.py"
    description = "Script to get job candidate's github profile"
    parser = argparse.ArgumentParser(usage=usage, description=description)
    parser.add_argument("search_string", type=str, nargs=1,
                        help="substring to search for in users' name/email/login fields")
    parser.add_argument("auth_token", type=str, nargs="?",
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
              'html_url', 'language', 'updated_at', 'forks_count', 'stargazers_count',
              'contribution %', 'contributions','readme_keywords']
    # get all details for mathing users and save specified fields to excel sheet
    tabulated_details = get_github_profiles(matching_users, search_string, fields)

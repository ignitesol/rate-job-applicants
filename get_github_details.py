#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  5 13:17:58 2017

@author: srikant
"""

import requests
import json
import sys
import os
import base64
import argparse

import nltk
import pandas as pd
from pandas.io.json import json_normalize

# initialize requests sessions
requests_session = requests.Session()
# add nltk_data folder to the list of NLTK library paths
nltk.data.path.insert(0,'nltk_data')
# set of stopwords
STOPWORDS = set(nltk.corpus.stopwords.words('english'))
#with open('nltk_data/corpora/stopwords/english','r') as f_stop:
#    STOPWORDS = set(f_stop.read().splitlines())

   
def get_keywords(readme):
    tokens_all = nltk.word_tokenize(readme)
    tokens_set = set(tokens_all)
    tokens_alpha = [s.lower() for s in tokens_set if s.isalpha()]
    tokens_nostop = set(tokens_alpha) - STOPWORDS
    return list(tokens_nostop)


def github_get_request(url, auth_header, params={}):
    '''Function to send requests to github and return the json part of the response
    '''
    # get request
    resp = requests_session.get(url, params=params, headers=auth_header)
    # error handling - print error message and exit
    if resp.status_code in [403,400,422]:
        error_msg = resp.json().get('message','')
        print("\nError: '{}'.\n\nExiting.\n".format(error_msg))
        sys.exit(0)
    else:
        return resp.json()


def get_matching_users(search_string, auth_header):
    '''Find all the users matching the search string.
    '''
    print("\nFinding users matching '{}' ...".format(search_string))
    url = 'https://api.github.com/search/users'
    # search for the  search_string matches in fullnames, logins, emails
    params = {'q':search_string,
              'in':['fullname','login','email'],
              'sort':'score',
              'order':'desc'}
    # get resonse with list of matching users
    resp_json = github_get_request(url=url, params=params, auth_header=auth_header)
    # list of user id details (user_login, user_name, user_email)
    users_list = []
    # get user profile for each of the matching users - necessary for getting email ids
    for i,user_details in enumerate(resp_json.get('items',[])):
        profile_url = 'https://api.github.com/users/' + user_details['login']
        profile = github_get_request(profile_url, auth_header=auth_header)
        # combine user details and user profile
        resp_json['items'][i] = {**user_details, **profile}
        users_list.append((profile['login'], profile['name'], profile['email']))
    # return list of user profiles and list of user id details
    return resp_json, users_list


def parse_contributions(df_repo, user, repo, auth_header):
    '''Extract user's contributions for the specified repo
    '''
    login = user.get('login','')
    # contributions url
    contribs_url = repo['contributors_url']
    # get list of all contributions to the rep
    try:
        contribs_list = github_get_request(url=contribs_url, auth_header=auth_header)
    except json.JSONDecodeError:
        contribs_list = []
    # dict of {user:contributions} for the rep
    contribs_dict = {contrib['login']:contrib.get('contributions',0) \
                     for contrib in contribs_list}
    # get users contribution %
    sum_contribs = sum(contrib for contrib in contribs_dict.values())
    try:
        user_contrib = 100*contribs_dict[login]/sum_contribs
    except (ZeroDivisionError, KeyError):
        user_contrib = 0
    # add contribution and owner details to the repo dataframe
    df_repo['contribution %'] = user_contrib
    df_repo['contributions'] = contribs_dict.get(login,0)
    df_repo['owner'] = repo.get('owner',{}).get('login','')
    print("\t\t{:3.0f}% contribution in '{}' ({})".format(user_contrib, repo.get('full_name',''),
          repo.get('language','')))
    return df_repo


def parse_readme(df_repo, user, repo, auth_header):
    '''Extract keywords from readme
    '''
    readme_url = repo['url'] + '/readme'
    readme_data = github_get_request(url=readme_url, auth_header=auth_header)
    readme_content = readme_data.get('content','')
    readme_binstr = base64.b64decode(readme_content)
    readme = readme_binstr.decode('utf-8')
    keywords_list = get_keywords(readme)
    df_repo['readme_keywords'] = ','.join(keywords_list)
    return df_repo


def add_user_details(df_repo, user, user_fields):
    '''Add specified user details to tabular data
    '''
    for item in user_fields:
        df_repo['user_' + item] = user.get(item,'')
    return df_repo


def convert_datetime_cols(df_all, date_cols):
    ''' Convert datetime string to datetime objects
    '''
    for col in date_cols:
        df_all[col] = pd.to_datetime(df_all[col],infer_datetime_format=True)
    return df_all

def parse_user_details(matching_users, auth_header):
    '''For each of the users matching the search string,
    get all the user repos and parse the information to a dataframe.
    '''
    repos_dfs = []
    # for each user get all the user repos and parse info to dataframe
    for user in matching_users.get('items',[]):
        login = user.get('login','')
        repos_url = 'https://api.github.com/users/' + login + '/repos'
        repos_params = {'type':'all'}
        # get all repos for user
        repos = github_get_request(url=repos_url, params=repos_params, auth_header=auth_header)
        print('\t{}, {}, {}, {:2d} repos'.format(user['name'],user['login'],user['email'],len(repos)))
        # for each repo, get contirbution details for the user and parse the info to dataframe
        for repo in repos:
            # json to dataframe using builtin pandas method
            df_repo = json_normalize(repo)
            # parse contributions
            df_repo = parse_contributions(df_repo, user, repo, auth_header)
            # parse readme readme
            df_repo = parse_readme(df_repo, user, repo, auth_header)
            # append user id details to the repo dataframe
            df_repo = add_user_details(df_repo, user, user_fields = ['login','name','email','score'])
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


def get_github_auth(auth_token=None):
    '''Get authentication header using auth token in auth_file.
    Returns auth_header for GET requests
    '''
    if auth_token is not None:
        auth_header = {'Authorization':'token ' + auth_token}
    # if auth token is not provided as an argv
    else:
        # check if auth token file exists, get token if it does
        try:
            import github_auth
            print("\nReading auth_token from github_auth.py")
            auth_token = github_auth.AUTH_TOKEN
            auth_header = {'Authorization':'token ' + auth_token}
        # proceed without auth if there is no auth token file
        except ImportError:
            print("\nAuthentication token not privided; Can't find github_auth.py; Trying without authentication.")
            print("Rate limit without authentication is 60 requests/hour")
            print("Store github AUTH_TOKEN in github_auth.py to avoid rate limitation issue")
            auth_header = {}
    return auth_header


def get_github_profiles(matching_users, users_list, fields, auth_header):
    '''Get all details for matching users and save as excel file
    '''
    n_matches = len(users_list)
    # exit if there are no matches
    if n_matches == 0:
        print("Found 0 users matching '{}'; exiting\n".format(search_string))
        sys.exit(0)
    # get details of all the matching users, parse the details to dataframe, write it to excel file
    else:
        print("Found {} users matching '{}'.\nFetching details ...".format(n_matches,search_string))
        # get all repos for the user and output to a dataframe
        tabulated_details = parse_user_details(matching_users, auth_header=auth_header)[fields]
        # write dataframe to excel file
        file_name = os.path.join('github_output',search_string.replace(' ','_') + '_github.xlsx')
        tabulated_details.to_excel(file_name)
        print('Details saved to {}'.format(file_name),'\n')
    return tabulated_details


if __name__ == '__main__':
    # get search_string from argv
    parser = argparse.ArgumentParser("Get github data for users matching given string")
    parser.add_argument("search_string", type=str, nargs="?",
                        help="name to search in user's name/email/login fields")
    parser.add_argument("auth_token", type=str, nargs="?",
                        help="github authentication token (for avoiding request rate limitation)")
    args = parser.parse_args()
    search_string = args.search_string
    auth_token = args.auth_token
    # get github authentication - as header for GET request
    auth_header = get_github_auth(auth_token=None)
    # find all users matchin the search string
    matching_users, users_list = get_matching_users(search_string, auth_header=auth_header)
    # get all details for mathing users and save specific fields to excel sheet
    # fields to output to excel file
    fields = ['user_name', 'user_login', 'user_email', 'full_name', 'owner',
              'html_url', 'language', 'updated_at', 'forks_count', 'stargazers_count',
              'contribution %', 'contributions','readme_keywords']
    tabulated_details = get_github_profiles(matching_users, users_list, fields, auth_header)
    

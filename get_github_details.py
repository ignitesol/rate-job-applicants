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

# initialize 
requests_session = requests.Session()

# add nltk_data path
nltk.data.path.append('nltk_data')
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


def github_get_request(url, params={}):
    '''Function to send requests to github and return the json part of the response
    '''
    # get request
    resp = requests_session.get(url, params=params, headers=AUTH_HEADER)
    # error handling - print error message and exit
    if resp.status_code in [403,400,422]:
        error_msg = resp.json().get('message','')
        print("\nError: '{}'.\n\nExiting.\n".format(error_msg))
        sys.exit(0)
    else:
        return resp.json()


def get_matching_users(search_string):
    '''Find all the users matching the search string.
    '''
    url = 'https://api.github.com/search/users'
    # search for the  search_string matches in fullnames, logins, emails
    params = {'q':search_string,
              'in':['fullname','login','email'],
              'sort':'score',
              'order':'desc'}
    # get resonse with list of matching users
    resp_json = github_get_request(url=url, params=params)
    # list of user id details (user_login, user_name, user_email)
    users_list = []
    # get user profile for each of the matching users - necessary for getting email ids
    for i,user_details in enumerate(resp_json.get('items',[])):
        profile_url = 'https://api.github.com/users/' + user_details['login']
        profile = github_get_request(profile_url)
        # combine user details and user profile
        resp_json['items'][i] = {**user_details, **profile}
        users_list.append((profile['login'], profile['name'], profile['email']))
    # return list of user profiles and list of user id details
    return resp_json, users_list


def parse_user_details(matching_users):
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
        repos = github_get_request(url=repos_url, params=repos_params)
        print('\t{}, {}, {}, {:2d} repos'.format(user['name'],user['login'],user['email'],len(repos)))
        # for each repo, get contirbution details for the user and parse the info to dataframe
        for repo in repos:
            # json to dataframe using builtin pandas method
            df_repo = json_normalize(repo)
            # contributions url
            contribs_url = repo['contributors_url']
            # get list of all contributions to the rep
            try:
                contribs_list = github_get_request(url=contribs_url)
            except json.JSONDecodeError:
                continue
            # dict of {user:contributions} for the rep
            contribs_dict = {contrib['login']:contrib.get('contributions',0) \
                             for contrib in contribs_list}
            # get users contribution %
            sum_contribs = sum(contrib for contrib in contribs_dict.values())
            try:
                user_contrib = 100*contribs_dict[login]/sum_contribs
            except ZeroDivisionError:
                user_contrib = 0
            # add contribution and owner details to the repo dataframe
            df_repo['contribution %'] = user_contrib
            df_repo['contributions'] = contribs_dict.get(login,0)
            df_repo['owner'] = repo.get('owner',{}).get('login','')
            # get readme
            readme_url = repo['url'] + '/readme'
            readme_data = github_get_request(url=readme_url)
            readme_content = readme_data.get('content','')
            readme_binstr = base64.b64decode(readme_content)
            readme = readme_binstr.decode('utf-8')
            keywords_list = get_keywords(readme)
            df_repo['readme_keywords'] = ','.join(keywords_list)
            # append user id details to the repo dataframe
            user_details = ['login','name','email','score']
            for item in user_details:
                df_repo['user_' + item] = user.get(item,'')
            # add it to the list of repo dataframes
            repos_dfs.append(df_repo)
    # combine all the repo dataframes for each of the matching users
    df_all = pd.concat(repos_dfs, axis=0, ignore_index=True)
    # convert datetime columns to datetime objects
    date_cols = ['updated_at','created_at', 'pushed_at']
    for col in date_cols:
        df_all[col] = pd.to_datetime(df_all[col],infer_datetime_format=True)
    # return combined dataframe
    return df_all


if __name__ == '__main__':

    parser = argparse.ArgumentParser("Github job rater")
    parser.add_argument("search", type=str, nargs="+")
    args = parser.parse_args()
    search_string = " ".join(args.search)

    # check if auth token file exists, get token if it does
    try:
        import github_auth
        AUTH_TOKEN = github_auth.AUTH_TOKEN
        AUTH_HEADER = {'Authorization':'token ' + AUTH_TOKEN}
    # proceed without auth if there is no auth token file
    except ImportError:
        print("Trying without authentication.(rate limited; email-ids may not be available)")
        print("Rate limit without authentication is 60 requests/hour")
        print("Store github AUTH_TOKEN in github_auth.py to avoid rate limitation issue")
        AUTH_HEADER = {}
    
    # fields to output to excel file
    fields = ['user_name', 'user_login', 'user_email', 'user_score', 'full_name', 'owner',
              'html_url', 'language', 'updated_at', 'forks_count', 'stargazers_count',
              'contribution %', 'contributions','readme_keywords']
    print("\nFinding users matching '{}' ...".format(search_string))
    # find all users matchin the search string
    matching_users, users_list = get_matching_users(search_string)
    n_matches = len(users_list)
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

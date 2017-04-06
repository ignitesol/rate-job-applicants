#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  5 13:17:58 2017

@author: srikant
"""

import requests
import json
import pandas as pd
import sys
from pandas.io.json import json_normalize

AUTH_TOKEN = '1b2f1a9bdcea074239731623c09ddbf9310a959b'
AUTH_HEADER = {'Authorization':'token ' + AUTH_TOKEN}

requests_session = requests.Session()

def get_matching_users(search_string):
    url = 'https://api.github.com/search/users'
    params = {'q':search_string,
              'in':['fullname','login','email'],
              'sort':'score',
              'order':'desc'}
    resp = requests_session.get(url, params=params, headers=AUTH_HEADER)
    resp_json = resp.json()
    users_list = []
    for i,user_details in enumerate(resp_json.get('items',[])):
        profile_url = 'https://api.github.com/users/' + user_details['login']
        profile = requests_session.get(profile_url, headers=AUTH_HEADER).json()
        resp_json['items'][i] = {**user_details, **profile}
        users_list.append((profile['login'], profile['name'], profile['email']))
    return resp_json, users_list

def get_user_repos(login):
    url = 'https://api.github.com/users/' + login + '/repos'
    params = {'type':'all'}
    resp = requests_session.get(url, params=params, headers=AUTH_HEADER)
    resp_json = resp.json()
    return resp_json

def parse_user_details(matching_users):
    repos_dfs = []
    for user in matching_users.get('items',[]):
        login = user.get('login','')
        repos = get_user_repos(login)
        print('\t{}, {}, {}, {:2d} repos'.format(user['name'],user['login'],user['email'],len(repos)))
        for repo in repos:
            df_repo = json_normalize(repo)
            contribs_url = repo['contributors_url']
            try:
                contribs_list = requests_session.get(contribs_url, headers=AUTH_HEADER).json()
            except json.JSONDecodeError:
                continue
            contribs_dict = {contrib['login']:contrib.get('contributions',0)\
                                for contrib in contribs_list}
            sum_contribs = sum(contrib for contrib in contribs_dict.values())
            try:
                user_contrib = 100*contribs_dict[login]/sum_contribs
            except:
                user_contrib = 0
            df_repo['contribution %'] = user_contrib
            df_repo['contributions'] = contribs_dict.get(login,0)
            df_repo['owner'] = repo.get('owner',{}).get('login','')
            user_details = ['login','name','email','score']
            for item in user_details:
                df_repo['user_' + item] = user.get(item,'')
            repos_dfs.append(df_repo)
    df_all = pd.concat(repos_dfs, axis=0, ignore_index=True)
    date_cols = ['updated_at','created_at', 'pushed_at']
    for col in date_cols:
        df_all[col] = pd.to_datetime(df_all[col],infer_datetime_format=True)
    return df_all

if __name__ == '__main__':
    try:
        search_string = sys.argv[1]
    except IndexError:
        print('\nRequires search string')
        sys.exit(0)
    fields = ['user_name', 'user_login', 'user_email', 'user_score', 'full_name', 'owner',
              'html_url', 'language', 'updated_at', 'forks_count', 'stargazers_count',
              'contribution %', 'contributions']
    print("\nFinding users matching '{} ...".format(search_string))
    matching_users, users_list = get_matching_users(search_string)
    n_matches = len(users_list)
    if n_matches == 0:
        print("Found 0 users matching '{}'; exiting\n".format(search_string))
        sys.exit(0)
    else:
        print("Found {} users matching '{}'; fetching details ...".format(n_matches, search_string))
        tabulated_details = parse_user_details(matching_users)[fields]
        file_name = search_string.replace(' ','_') + '_github.xlsx'
        tabulated_details.to_excel(file_name)
        print('Details saved to {}'.format(file_name),'\n')

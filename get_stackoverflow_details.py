#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 14 16:08:54 2017

@author: srikant
"""

import argparse
import stackexchange



so = stackexchange.Site(stackexchange.StackOverflow)

if __name__ == '__main__':
    # get search_string and auth_key from command line arguments
    parser = argparse.ArgumentParser("\npython3 get_github_details_pygithub.py")
    parser.add_argument("search_string", type=str,
                        help="name to search for in user's name/email/login fields")
    parser.add_argument("auth_token", type=str, nargs="?",
                        help="github authentication token (to avoid rate limitation)")
    args = parser.parse_args()
    search_string = args.search_string
    auth_token = args.auth_token
    # initialize so object
    # find all users matching the search string
    # fields to output to excel file
    # get all details for mathing users and save specified fields to excel sheet
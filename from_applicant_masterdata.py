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


MASTER_FILE = "Copy of Applicant Master Data 2017.xlsx"

# read master appliant information
try:
    master_df_raw = pd.read_excel(MASTER_FILE, sheetname='Sheet1')
except FileNotFoundError as err:
    print("\nCouldnt find '{}' \n".format(MASTER_FILE))
    sys.exit(0)

# drop rows where both name and email are missing
missing_name_email_idx = (master_df_raw['NAME'].isnull()) & (master_df_raw['EMAIL'].isnull())
master_df = master_df_raw.drop(missing_name_email_idx, axis=0)

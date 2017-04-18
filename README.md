__Purpose__
* Search Github and Stackexchange for information about a job candidate.
* Retrive all relevant data for the candidate from Github and Stackexchange.
* Identify and extract data pertinent for rating the candidate.
* Use a suitable methodology for rating the candidate using this data.

__Implemented Functionality__
- [x] Search Github for a specified name/username/email and retrive users' data.
  * Auth: Github authentication token either as command-line input or as AUTH_TOKEN in github_auth.py. (Authentication is necessary for bypassing rate limit of 60 requests/hour)
  * Usage: `$ python3 get_github_details.py "search string" ["authentication_token"]`
  * Output: spreadsheet with relevant github (selective) details named "search_string_github.xlsx"
- [x] Search Stackexchange for name/username/email and retrive users' data.
  * Auth: Authentication token either as command-line input or as AUTH_KEY in stackoverflow_auth.py. (Authentication is necessary for bypassing rate limit of 300 requests/day)
  * Usage: `$ python3 get_stackoverflow_details.py [-i "user_id" | -s "search string"] [-a "authentication_token"]`
  * Output: spreadsheet with relevant stackoverflow (selective) details named "search_string_stackoverflow.xlsx"
- [ ] Identify relevant data from Github and Stackoverflow.
- [ ] Identify methodology and/or an aggregate metric for rating the candidate.

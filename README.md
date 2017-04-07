__Purpose__
* Search Github and Stackexchange for information about a job candidate
* Retrive all relevant data for the candidate from Github and Stackexchange
* Identify and extract data pertinent for rating the candidate
* Use a suitable methodology for rating the candidate using this data

__Implemented Functionality__
- [x] Search Github for a specified name/username/email and retrive relevant data.
  * Requirements: Github auth token (as a AUTH_TOKEN in github_auth.py) - necessary only for bypassing rate limits.
  * Usage command: $ python3 get_github_details.py "search string"
  * Output: spreadsheet with relevant github (selective) details named "search_string_github.xlsx"
- [ ] Search Stackexchange for name/username/email and retrive relevant data.
- [ ] Identify data pertinent for rating the candidate.
- [ ] Methodology for rating the candidate.



## Purpose
* Search Github and Stackexchange for information about a job candidate.
* Retrive all relevant data for the candidate from Github and Stackexchange.
* Identify and extract data pertinent for rating the candidate.
* Use a suitable methodology for rating the candidate using this data.

## Implemented Functionality
- [x] Search Github for a specified name/username/email and retrive users' data.
  * Auth: Github authentication token either as command-line input or as AUTH_TOKEN in github_auth.py. (Authentication is necessary for bypassing rate limit of 60 requests/hour)
  * Usage: `$ python3 get_github_details.py "search string" ["authentication_token"]`
  * Output: spreadsheet with relevant github (selective) details named "search_string_github.xlsx"
- [x] Search Stackexchange for name/username/email and retrive users' data.
  * Auth: Authentication token either as command-line input or as AUTH_KEY in stackoverflow_auth.py. (Authentication is necessary for bypassing rate limit of 300 requests/day)
  * Usage: `$ python3 get_stackoverflow_details.py [-i "user_id" | -s "search string"] [-a "authentication_token"]`
  * Output: spreadsheet with relevant stackoverflow (selective) details named "search_string_stackoverflow.xlsx"
- [ ] Relevant data from Github and Stackoverflow.
  * __Github Data__:
     * Data from each repository: User_contributions, User_contributions_%, Stars_count, Forks_count, Language, Owner_type (User or Not-User)
     * Repository Score: Weighted average of all quantitative fields, grouped by Owner_type, grouped by language.
  * __Stackoverflow Data__:
     * Overall Data: Reputation, Badge_Count (Bronze, Silver, Gold), Answer_acceptance_rate
     * Expertise Data: For each tag (skill/expertise) : Answer_count, Answer_score, Question_count, Question_score
- [ ] Aggregate metric(s) for rating the candidate.
  * __Github Metric__: Weighted average? Sum? of all the individual repository scores; overall as well as grouped by Language
  * __Stackoverflow Metric__: Weighted Average

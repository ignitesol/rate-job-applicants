### Purpose
* Search Github and Stackexchange for information about a job candidate.
* Retrive all relevant data for the candidate from Github and Stackexchange.
* Identify and extract data pertinent for rating the candidate.
* Use a suitable methodology for rating the candidate using this data.

### Implemented Functionality
- [x] __Search Github for a specified name/username/email and retrive users' data.__
  * Auth: Github authentication token either as command-line input or as AUTH_TOKEN in github_auth.py. (Authentication is necessary for bypassing rate limit of 60 requests/hour)
  * Usage: `$ python3 get_github_details.py "search string" ["authentication_token"]`
  * Output: spreadsheet with relevant github (selective) details named "search_string_github.xlsx"
- [x] __Search Stackexchange for name/username/email and retrive users' data.__
  * Auth: Authentication token either as command-line input or as AUTH_KEY in stackoverflow_auth.py. (Authentication is necessary for bypassing rate limit of 300 requests/day)
  * Usage: `$ python3 get_stackoverflow_details.py [-i "user_id" | -s "search string"] [-a "authentication_token"]`
  * Output: spreadsheet with relevant stackoverflow (selective) details named "search_string_stackoverflow.xlsx"
- [ ] __Relevant data from Github and Stackoverflow.__
  * __Github Data__:
     * Data from each repository: User_contributions, User_contributions_%, Stars_count, Forks_count, Language, Owner_type (User or Not-User)
     * Repository Score: Weighted average of all quantitative fields, grouped by Owner_type, grouped by language.
  * __Stackoverflow Data__:
     * Overall Data: Reputation, Badge_Count (Bronze, Silver, Gold), Answer_acceptance_rate
     * Expertise(tags) Data: For each tag (skill/expertise) : Answer_count, Answer_score, Question_count, Question_score
- [ ] __Aggregate metric(s) for rating the candidate.__
  * __Github Rating__: Weighted average? Sum? of all the individual repository scores; overall as well as grouped by Language
  * __Stackoverflow Rating__: Weighted average of Overall Data and Expertise Data; overall as well as grouped by Expertise (Tags)
  * __Overall Rating__: Weighted harmonic mean or Github Rating and Stackoverflow Rating

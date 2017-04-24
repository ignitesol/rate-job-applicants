### Purpose
* Search Github and Stackexchange for information about a job candidate.
* Retrive all relevant data for the candidate from Github and Stackexchange.
* Identify and extract data pertinent for rating the candidate.
* Use a suitable methodology for rating the candidate using this data.

### Implemented Functionality
- [X] __Search Github for a specified name/username/email and retrive users' data.__
  * Auth: Github authentication token either as command-line input or as AUTH_TOKEN in github_auth.py. (Authentication is necessary for bypassing rate limit of 60 requests/hour)
  * Usage: `$ python3 get_github_details.py -s "search string" [-a "authentication_token"]`
  * Output: spreadsheet with relevant github (selective) details named "search_string_github.xlsx"
- [X] __Search Stackexchange for name/username/email and retrive users' data.__
  * Auth: Authentication token either as command-line input or as AUTH_KEY in stackoverflow_auth.py. (Authentication is necessary for bypassing rate limit of 300 requests/day)
  * Usage: `$ python3 get_stackoverflow_details.py [-i "user_id" | -s "search string"] [-a "authentication_token"]`
  * Output: spreadsheet with relevant stackoverflow (selective) details named "search_string_stackoverflow.xlsx"
- [X] __Relevant data from Github and Stackoverflow.__
  * __Github Data__:
     * Data from each repository: All_Contributions, User_Contributions_%, Stars_count, Forks_count, Language, Owner_type (User or Not-User)
     * Repository Score: Weighted average of all quantitative fields, grouped by Owner_type, grouped by language.
  * __Stackoverflow Data__:
     * Overall Data: Reputation, Badge_Count (Bronze, Silver, Gold), Answer_acceptance_rate
     * Expertise(tags) Data: For each tag (skill/expertise) : Answer_count, Answer_score, Question_count, Question_score
- [X] __Aggregate metric(s) for rating the candidate.__
  * __Github Rating__:
     * __Repository_Rating__: `count(Stars) + 2*count(Forks) + log(All_Contributions + 1)` for each Repository
     * __User_Repository_Rating__: `User_Contributions_% * (User is Owner ? 1 : 1.25) * Repository_Rating` for each Repository
     * __Overall_User_Rating__: `sum(User_Repository_Ratings)` for all Repositories
     * __User_Expertise_Rating__: `User_Repository_Ratings GROUPBY Language` for all Repositories
  * __Stackoverflow Rating__:
     * __Overall_User_Rating__: `10*exp(Acceptance_Rate/100)-10 + sum(Bronze_Badges + 2*Silver_Badges + 3*Gold_Badges) + 100*log(Reputation + 1)`
     * __User_Expertise_Rating__: `sum(Answer_Count + Answer_Score + Question_Count + Question_Score) GROUPBY Tag`
- [ ] __Overall Rating__
  * Weighted harmonic mean ? of Github Ratings and Stackoverflow Ratings: Overall and By Expertise

### Purpose
* Search Github and Stackexchange for information about a job applicant.
* Retrive all relevant data for the applicant from Github and Stackexchange.
* Identify and extract data pertinent for rating the applicant.
* Use a suitable methodology for rating the applicant using this data.

### Implemented Functionality
- [X] __Search Github for a specified name/username/email and retrive matching users' data.__
  * Auth: Github authentication token, either as command-line input or as AUTH_TOKEN in github_auth.py. (Authentication is necessary for bypassing rate limit of 60 requests/hour)
  * Usage: `bash$ python3 get_github_details.py -s "search string" [-a "authentication_token"]`
  * Output: spreadsheet with relevant github (selective) details named "search_string_github.xlsx"
- [X] __Search Stackoverflow for a specified user_id/username and retrive matching users' data.__
  * Auth: Stackapps authentication key, either as command-line input or as AUTH_KEY in stackoverflow_auth.py. (Authentication is necessary for bypassing rate limit of 300 requests/day)
  * Usage: `bash$ python3 get_stackoverflow_details.py -i "user_id" | -s "search string" [-a "authentication_key"]`
  * Output: spreadsheet with relevant stackoverflow (selective) details named "search_string_stackoverflow.xlsx"
- [X] __Relevant data from Github and Stackoverflow.__
  * __Github Data__:
     * List of all user's repositories
     * Data from each repository: All_Contributions, User_Contributions_%, Stars_count, Forks_count, Language, Owner_type (User or Not-User)
  * __Stackoverflow Data__:
     * Overall User Data: Reputation, Badge_Count (Bronze, Silver, Gold), Answer_acceptance_rate
     * Expertise (tags) Data: For each tag (language/expertise) : Answer_count, Answer_score, Question_count, Question_score
- [X] __Aggregate metric(s) for rating the candidate.__
  * __Github Rating__:
     * __Repository_Ratings__: `count(Stars) + 2*count(Forks) + log(All_Contributions + 1)` (list)
     * __User_Repo_Ratings__: `User_Contributions_% * (User is Owner ? 1 : 1.25) * Repository_Rating` (list)
     * __Overall_User_Rating__: `sum(User_Repository_Ratings)` for all Repositories
     * __User_Expertise_Ratings__: `User_Repository_Ratings GROUPBY Language` for all Repositories
  * __Stackoverflow Rating__:
     * __Overall_User_Rating__: `10*exp(Acceptance_Rate/100)-10 + sum(Bronze_Badges + 2*Silver_Badges + 3*Gold_Badges) + 100*log(Reputation + 1)`
     * __User_Expertise_Ratings__: `sum(Answer_Count + Answer_Score + Question_Count + Question_Score) GROUPBY Tag`
- [ ] __Overall Rating__
  * Weighted harmonic mean ? of Github Ratings and Stackoverflow Ratings: Overall and By Expertise

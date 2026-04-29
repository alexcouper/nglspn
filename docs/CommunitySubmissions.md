Community Submissions


Right now we only support users creating projects they own. They create them and are automatically submitted into that months competition bracket.


We want to support 2 additional types of project:
 - Group owned. That is more than one person is involved in the project, or a company owns the project (not in this change)
 - Unowned/Community submission. That is a project added to naglasupan by someone OTHER than the person who created it - as they (presumably) have not signed up.


## Group Owned (out of scope for THIS change - we want to focus on community/unowned projects - but gives some context of where we're heading)

Creator of the project can add contributors.
Adds a contributor by email (man do we need usernames?)
That person receives a link
Clicking on that link causes them to have to login/register
Once logged in, they are shown a list of "pending invites"
NOTE: they may be invited to the project on one email but login with another - the invite still stands.

Accepting the project puts them into a list of contributors on the project
They are rendered in the headline of the project once they have accepted, but not before.



## Community/Unowned Projects

A new user - that is unable to login - exists called Community/Unowned. With a description of "Projects submitted by community members but owned by people outside of Naglasúpan."

During project submission, a new checkbox appears that by default is checked - "I own this project".

When this is checked, things work as they do now. Unchecked means this becomes owned by the Community/Unowned user.

The submitter is added as a special kind of contributor on the project: "SUGGESTER".

SUGGESTER contributors should appear somewhere on the project page, but not in the top bar.

Users can see their suggested contributions under a separate heading inside "my Projects". They can edit the description/images.

Edits are recorded for a project - it's possible to go and view previous iterations of the project at the db level (not in the UI for now)

Community projects should not be entered into the current competition

Community owned projects will

## Implications

 - New Contributors many to many with projects, with at least 2 roles:
    - OWNER
    - SUGGESTER

 - Rename current owner field to be "creator"
 - Add all existing "creators" to be OWNER-type contributors to each of their own projects
 - Move all access control (write access) to be based on if you are a contributor to the project
 - Alter the UI of the projects to render contributors NOT creators in the top bar
 - Alter the UI of the projects to render creator of project somewhere at the bottom underneath the tags etc

 - Add a user that is hardcoded in the system called Community/Unowned. With a description of "Projects submitted by community members but owned by people outside of Naglasúpan."
 - Add the checkbox for ownership of the project
 - When the checkbox is false, set the creator to the submitter, but add the Community/Unowned as the OWNER-contributor. Add the creator as SUGGESTER.
 - When the checkbox is false, do not add the project to the currently running competition.

 - Listing projects api: should list projects I own and projects I am a suggester of.
 - UI: Render suggested projects in a separate section on the my projects page


## Later / Out of scope

These projects need a ´claim´ button, allowing users to notify me if a project has been submitted that they own

Suggesting edits: Anyone can "edit" any other project. It results in a suggestion of changes that must be accepted by a contributor on the project
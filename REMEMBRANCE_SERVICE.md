# Reminders DBus Service version 5.0 Documentation
name: io.github.dgsasha.Remembrance.Service3

interface: io.github.dgsasha.Remembrance.Service3.Reminders

object: /io/github/dgsasha/Remembrance/Service3

Currently this is only packaged with Reminders and anyone who wants to use it will have to have the full Reminders app installed. The reason this exists is to allow integrating the Reminders app with desktop environments through extensions.

At some point I might seperate this from Reminders and offer it as a standalone library, but until then you probably shouldn't use it if you are making your own reminder app.

This service will have some breaking changes made to it at times, so make sure you use the GetVersion method to check that the right version is installed.

Newer versions of this service should still always be compatible with apps that expect an older version. If this ever changes, the bus name will be updated.

## Enums
### RepeatType
On what interval to repeat the reminder.
- DISABLED = 0
- MINUTE = 1 *Can not be appled to Microsoft Tasks*
- HOUR = 2 *Can not be appled to Microsoft Tasks*
- DAY = 3
- WEEK = 4
- MONTH = 5
- YEAR = 6

### RepeatDays
What days to repeat on for weekly repeating reminders, can be zero to just use the weekday of the Reminder's timestamp, or add multiple values together to repeat on multiple days.
- MON = 1
- TUE = 2
- WED = 4
- THU = 8
- FRI = 16
- SAT = 32
- SUN = 64

## Reminder Object
Type: a{sv}
| Key | VariantType | Description | Default |
| --- | --- | --- | --- |
| 'id' | s | This is the id of the reminder. | This usually cannot be left blank, no default. |
| 'title' | s | This is the title of the reminder. | '' |
| 'description' | s | This is a short description of the reminder. | '' |
| 'due-date' | u | This is a Unix timestamp for the day that the reminder is due. This should be at 00:00 of the desired day in UTC, and can be 0 if you don't want to set a due date. | 0 |
| 'timestamp' | u | This is a Unix timestamp that sets when the notification will be sent. This has to be on the same day as the due date, and if it isn't the due date will be changed. This can be 0 if you don't want to send a notification. | 0 |
| 'important' | b | Whether or not the reminder is important. | False |
| 'completed' | b | Whether or not the reminder is completed. | False |
| 'repeat-type' | q | This is the enum [RepeatType](#repeattype). | 0 |
| 'repeat-frequency' | q | How often to repeat the reminder, so if 'repeat-type' is 4 and and 'repeat-frequency' is 3, it will repeat every 3 weeks. | 1 |
| 'repeat-days' | q | This is the enum [RepeatDays](#repeatdays). | 0 |
| 'repeat-times'| q | How many times in total the reminder should be repeated, this gets decreased by 1 each time the reminder is repeated. -1 if you want to repeat forever or are not repeating. Must be -1 for Microsoft Tasks. | -1 |
| 'repeat-until' | u | This is a Unix timestamp that represents the last day that the reminder should be repeated on. This should be at 00:00 of the desired day in UTC. Must be 0 for Microsoft Tasks | 0 |
| 'created-timestamp' | u | This is a Unix timestamp that represents the time the reminder was created, this is set automatically and cannot be changed. | 0 |
| 'updated-timestamp' | u | This is a Unix timestamp that represents the last time the reminder was updated, this is set automatically and cannot be changed. | 0 |
| 'completed-date' | u | This is a Unix timestamp that represents the day the reminder was completed, at 00:00 in UTC. 0 if not complete. This is set automatically and cannot be changed. | 0 |
| 'list-id' | s | This is the id of the list that the reminder is in. | 'local' |

## List Object
Type: a{sv}
| Key | VariantType | Description | Default |
| --- | --- | --- | --- |
| 'id' | s | This is the id of the reminder. | This usually cannot be left blank, no default. |
| 'name' | s | This is the name of the list. | '' |
| 'user-id' | s | This is the id of the user who owns the list. | '' |

## Methods

### GetUsers
Get usernames of all users, including the local user
- Returns (a{sa{ss}})
    - usernames
        - Type: a{sa{ss}}
        - Each key is either 'local', 'ms-to-do', or 'caldav' and each value is a dict
        - Each of these dicts represents the users within that service, and within that dict each key is a user id and each value is the username

### GetLists
Get all lists. This will also return lists that aren't being synced.
- Returns (aas{sv})
    - lists
        - Type: aas{sv}
        - An array of [lists](#list-object)

### GetListsDict
Get all lists as a dictionary. This will also return lists that aren't being synced.
- Returns (a{sas{sv}})
    - lists
        - Type: a{sas{sv}}
        - An dictionary where each key is a list id and each value is a [list](#list-object)
        - The 'id' key is not included in the list object

### GetReminders
Returns all reminders
- Returns (aa{sv})
    - reminders
        - Type: aa{sv}
        - An array of [reminders](#reminder-object)

### GetRemindersDict
Returns all reminders as a dictionary
- Returns (a{sa{sv}})
    - reminders
        - Type: a{sa{sv}}
        - An dictionary where each key is a reminder id and each value is a [reminder](#reminder-object)
        - The 'id' key is not included in the reminder object

### GetRemindersInList
Returns all reminders in specified list
- Parameters (ss)
    - user-id
        - Type: s
    - list-id
        - Type: s
- Returns (aa{sv})
    - reminders
        - Type: aa{sv}
        - An array of [reminders](#reminder-object)

### GetSyncedLists
- Returns (as)
    - list-ids
        - Type: as
        - An array of remote list ids that are being synced

### SetSyncedLists
Set the task lists that should be synced, this also refreshes the reminders
- Parameters (as)
    - list-ids
        - Type: as
        - An array of remote list ids that are being synced

### GetWeekStart
- Returns (b)
    - week-start-sunday
        - Type: b
        - True if week starts on sunday

### SetWeekStart
- Parameters (b)
    - week-start-sunday
        - Type: b
        - True if week starts on sunday

### CreateList
Create a list
- Parameters (sss)
    - [app-id](#app-id-parameter)
        - Type: s
    - [list](#list-object)
        - Type: a{sv}
        - Note that the 'id' key will be ignored here

- Returns (s)
    - list-id
        - Type: s
        - Id that was generated to represent the list, keep track of these

### UpdateList
Rename/Update a list
- Parameters (ssss)
    - [app-id](#app-id-parameter)
        - Type: s
    - [list](#list-object)
        - Type: a{sv}
        - Note that the 'user-id' key will be ignored here, you currently can't move lists between users

### RemoveList
Remove a list
- Parameters (sss)
    - [app-id](#app-id-parameter)
        - Type: s
    - list-id
        - Type: s
        - The id of the list you are deleting, list ids that are equal to the user id are default lists and cannot be removed

### CreateReminder
Add a new reminder
- Parameters (sa{sv})
    - [app-id](#app-id-parameter)
        - Type: s
    - [reminder](#reminder-object)
        - Type: a{sv}
        - Note that the 'completed' and 'id' key will be ignored here
        - You can leave any of these values blank, in that case the default value will be used

- Returns (su)
    - reminder-id
        - Type: s
        - Id that was generated to represent the reminder, keep track of these
    - created-timestamp
        - Type: u
        - The Unix timestamp of when the reminder was created

### UpdateReminder
Update an existing reminder
- Parameters (sa{sv})
    - [app-id](#app-id-parameter)
        - Type: s
    - [reminder](#reminder-object)
        - Type: a{sv}
        - Note that the 'completed' key will be ignored here
        - You can leave any of these values blank, in that case the previous value will be used

- Returns (u)
    - updated-timestamp
        - Type: u
        - The Unix timestamp of when the reminder was updated

### UpdateCompleted
Update the completed status of a reminder
- Parameters (ssb)
    - [app-id](#app-id-parameter)
        - Type: s
    - reminder-id
        - Type: s
        - Id of the reminder you want to update
    - completed
        - Type: b
        - Whether or not the reminder should be completed
    - completed-date
        - Type: u
        - The Unix timestamp of the day the reminder was completed

- Returns (u)
    - updated-timestamp
        - Type: u
        - The Unix timestamp of when the reminder was updated

### RemoveReminder
Remove a reminder
- Parameters (ss)
    - [app-id](#app-id-parameter)
        - Type: s
    - reminder-id
        - Type: s
        - Id of the reminder you want to remove

### UpdateReminderv
Update an existing reminder
- Parameters (saa{sv})
    - [app-id](#app-id-parameter)
        - Type: s
    - reminders
        - Type: aa{sv}
        - An array of [reminders](#reminder-object) that were updated
        - Note that the 'completed' key will be ignored here
        - You can leave any of these values blank, in that case the previous value will be used

- Returns (u)
    - updated-reminder-ids
        - Type: as
        - Ids of reminders that were actually updated (in case there were errors)
    - updated-timestamp
        - Type: u
        - The Unix timestamp of when the reminder was updated

### UpdateCompletedv
Update the completed status of a reminder
- Parameters (sasb)
    - [app-id](#app-id-parameter)
        - Type: s
    - reminder-ids
        - Type: as
        - Ids of the reminders you want to update
    - completed
        - Type: b
        - Whether or not the reminder should be completed

- Returns (asu)
    - updated-reminder-ids
        - Type: as
        - Ids of reminders that were actually updated (in case there were errors)
    - updated-timestamp
        - Type: u
        - The Unix timestamp of when the reminder was updated
    - completed-date
        - Type: u
        - The Unix timestamp of the day the reminder was completed

### RemoveReminderv
Remove multiple reminders
- Parameters (sas)
    - [app-id](#app-id-parameter)
        - Type: s
    - reminder-ids
        - Type: as
        - Ids of the reminders you want to remove

- Returns (as)
    - removed-reminder-ids
        - Type: as
        - Ids of reminders that were actually removed (in case there were errors)

### MSGetLoginURL
Gets a url so the user can login to a microsoft account, once logged out the reminders will be refreshed
- Returns (s)
    - url
        - Type: s
        - The login url

### CalDAVLogin
Log in to a CalDAV server, once logged out the reminders will be refreshed
- Parameters (ssss)
    - display-name
        - Type: s
        - This will be saved as the username for display purposes, but will not be used to login to the server
    - url
        - Type: s
        - The server url
    - username
        - Type: s
        - The server login username
    - password
        - Type: s
        - The server login password

### CalDAVUpdateDisplayName
Log in to a CalDAV server, once logged out the reminders will be refreshed
- Parameters (ss)
    - user-id
        - Type: s
        - The user to update
    - display-name
        - Type: s
        - This will be saved as the username for display purposes, but will not be used to login to the server

### Logout
Log out of a remote account, once logged out the reminders will be refreshed
- Parameters (s)
    - user-id
        - Type: s

### ExportLists
Export lists to ical/ics file
- Parameters (as)
    - list-ids
        - Type: as
        - An array of list ids that represent the lists to export

- Returns (s)
    - folder
        - Type: s

### ImportLists
Import lists from an ical/ics file
- Parameters (ass)
    - ical-files
        - Type: as
        - An array of files ids to import
    - list-id
        - Type: s
        - The list to import the files to, or 'auto' if you want to create new lists

### Refresh
Read reminders file again and also check for remote updates. Changes will be emitted with their respective signals

### RefreshUser
Same as [refresh](#refresh) but only for one user
- Parameters (s)
    - user-id
        - Type: s
        - The user to refresh

### GetVersion
- Returns (s)
    - version
        - Type: s
        - The version of the service that is currently loaded (PEP 440)

### Quit
Quits the service

## Signals

### SyncedListsChanged
Emitted when the dictionary of synced lists is changed
- Parameters (a{sas})
    - list-ids
        - Type: a{sas}
        - Each key is a user id and each value is an array of the list ids that are synced on that account

### WeekStartChanged
- Parameters (s)
    - week-start-sunday
        - Type: b
        - True if week starts on sunday

### ListUpdated
Emitted when a list is created or updated
- Parameters (a{sv})
    - [app-id](#app-id-parameter)
        - Type: s
    - [list](#list-object)
        - Type: a{sv}

### ListRemoved
Emitted when a list is removed
- Parameters (sss)
    - [app-id](#app-id-parameter)
        - Type: s
    - list-id
        - Type: s
        - The id of the list that was removed

### ReminderShown
Emitted when a reminder is shown
- Parameters (s)
    - reminder-id
        - Type: s
        - The id of the reminder that was shown in a notification

### ReminderUpdated
Emitted when a Reminder is created or updated
- Parameters (sa{sv})
    - [app-id](#app-id-parameter)
        - Type: s
    - [reminder](#reminder-object)
        - Type: a{sv}
        - Note that the 'completed' key will not be included here

### CompletedUpdated
Emitted when a reminder's completed status is changed
- Parameters (ssbuu)
    - [app-id](#app-id-parameter)
        - Type: s
    - reminder-id
        - Type: s
        - The id of the reminder that was updated
    - completed
        - Type: b
        - Whether or not the reminder was set as completed
    - updated-timestamp
        - Type: u
        - The Unix timestamp of when the reminder was last updated
    - completed-date
        - Type: u
        - The Unix timestamp of the day the reminder was completed

### ReminderRemoved
Emitted when a reminder is removed
- Parameters (ss)
    - [app-id](#app-id-parameter)
        - Type: s
    - reminder-id
        - Type: s
        - The id of the reminder that was deleted

### RemindersUpdated
- Parameters (saa{sv})
    - [app-id](#app-id-parameter)
        - Type: s
    - reminders
        - Type: aa{sv}
        - An array of [reminders](#reminder-object) that were updated

### RemindersCompleted
Emitted when multiple reminders' completed status changes
- Parameters (saa{sv})
    - [app-id](#app-id-parameter)
        - Type: s
    - reminder-ids
        - Type: as
        - The ids of the reminders that were completed
    - completed
        - Type: b
        - Whether or not the reminders were set as completed
    - updated-timestamp
        - Type: u
        - The Unix timestamp of when the reminders were updated
    - completed-date
        - Type: u
        - The Unix timestamp of the day the reminders were completed

### RemindersRemoved
- Parameters (sas)
    - [app-id](#app-id-parameter)
        - Type: s
    - removed-reminders
        - Type: as
        - An array of reminder ids that were removed

### MSSignedIn
Emitted when the user signs in to a Microsoft account
- Parameters (ss)
    - user-id
        - Type: s
    - username
        - Type: s

### CalDAVSignedIn
Emitted when the user signs in to a Microsoft account
- Parameters (ss)
    - user-id
        - Type: s
    - name
        - Type: s

## SignedOut
Emitted when an account is signed out
- Parameters (ss)
    - user-id
        - Type: s

## Error
Emitted when making certain changes fails (otherwise the error will be returned through dbus)
- Parameters (s)
    - stack-trace
        - Type: s
        - This is a stack trace of the error

## app-id parameter
This parameter should be set to the id of your app, although it can be left empty. This will be returned in a signal after the reminder is updated, which will let you ignore the signal if you initiated the update.

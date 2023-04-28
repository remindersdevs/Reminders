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
| 'id' | s | This is the id of the reminder. | This cannot be left blank, no default. |
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
| 'list-id' | s | This is the id of the list that the reminder is in. | 'local' |
| 'user-id' | s | This is the id of the user that owns the reminder. | 'local' |

## Methods

### GetUsers
Get usernames of all users, including the local user
- Returns (a{sa{ss}})
    - usernames
        - Type: a{sa{ss}}
        - Each key is either 'local', 'ms-to-do', or 'caldav' and each value is a dict
        - Each of these dicts represents the users within that service, and within that dict each key is a user id and each value is the username

### GetLists
Get all lists. This will also return lists that arent being synced.
- Returns (a{sa{ss}})
    - lists
        - Type: a{sa{ss}}
        - Each key is a user id and each value is another dictionary where each key is a list id and each value is the name of the list

### GetReminders
Returns all reminders
- Returns (aa{sv})
    - reminders
        - Type: aa{sv}
        - An array of [reminders](#reminder-object)

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
- Returns (a{sas})
    - list-ids
        - Type: a{sas}
        - Each key is a user id and each value is an array of the list ids that are synced on that account

### SetSyncedLists
Set the task lists that should be synced, this also refreshes the reminders
- Parameters (a{sas})
    - list-ids
        - Type: a{sas}
        - Each key should be a user id and each value should be an array of the list ids that are synced on that account

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
    - user-id
        - Type: s
        - The user the list should be created for, can be 'local' or a Microsoft user id
    - list-name
        - Type: s
        - The name of the list

- Returns (s)
    - list-id
        - Type: s
        - Id that was generated to represent the list, keep track of these

### RenameList
Rename a list
- Parameters (ssss)
    - [app-id](#app-id-parameter)
        - Type: s
    - user-id
        - Type: s
        - The user where the list is located, can be 'local' or a Microsoft user id
    - list-id
        - Type: s
        - The id of the list you are renaming
    - list-name
        - Type: s
        - The new name of the list

### RemoveList
Remove a list
- Parameters (sss)
    - [app-id](#app-id-parameter)
        - Type: s
    - user-id
        - Type: s
        - The user where the list is located, can be 'local' or a Microsoft user id
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
        - Note that the 'completed' key will be ignored here
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

### Refresh
Read reminders file again and also check for remote updates. Changes will be emitted with their respective signals, mainly through the [refreshed](#refreshed) signal.

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
- Parameters (ssss)
    - app-id
        - Type: s
        - The id of the app that initiated the change
    - user-id
        - Type: s
        - The user id of the list that was updated
    - list-id
        - Type: s
        - The id of the list that was updated
    - list-name
        - Type: s
        - The name of the list that was updated

### ListRemoved
Emitted when a list is removed
- Parameters (sss)
    - app-id
        - Type: s
        - The id of the app that initiated the change
    - user-id
        - Type: s
        - The user id of the list that was removed
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
    - app-id
        - Type: s
        - The id of the app that initiated the change
    - [reminder](#reminder-object)
        - Type: a{sv}
        - Note that the 'completed' key will not be included here

### CompletedUpdated
Emitted when a reminder's completed status is changed
- Parameters (ssbu)
    - app-id
        - Type: s
        - The id of the app that initiated the change
    - reminder-id
        - Type: s
        - The id of the reminder that was updated
    - completed
        - Type: b
        - Whether or not the reminder was set as completed
    - updated-timestamp
        - Type: u
        - The Unix timestamp of when the reminder was updated

### ReminderRemoved
Emitted when a reminder is removed
- Parameters (ss)
    - app-id
        - Type: s
        - The id of the app that initiated the change
    - reminder-id
        - Type: s
        - The id of the reminder that was deleted

### Refreshed
- Parameters (aa{sv}as)
    - updated-reminders
        - Type: aa{sv}
        - An array of [reminders](#reminder-object) that were updated
        - Note that the 'completed' key will not be included here
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
Emitted when making a remote change failed
- Parameters (s)
    - error
        - Type: s
        - This is a stack trace of the error

## app-id parameter
This parameter should be set to the id of your app, although it can be left empty. This will be returned in a signal after the reminder is updated, which will let you ignore the signal if you initiated the update.

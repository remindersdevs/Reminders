# Reminders DBus Service Info, version 2.2
name: io.github.dgsasha.Remembrance.Service1

interface: io.github.dgsasha.Remembrance.Service1.Reminders

object: /io/github/dgsasha/Remembrance/Service1

Currently this is only packaged with Reminders and anyone who wants to use it will have to have the full Reminders app installed. The reason this exists is to allow integrating the Reminders app with desktop environments through extensions.

At some point I might seperate this from Remembrance and offer it as a standalone library, but until then you probably shouldn't use it if you are making your own reminder app.

This service will have some breaking changes made to it at times, so make sure you use the GetVersion method to check that the right version is installed.

Newer versions of this service should still always be compatible with apps that expect an older version. If this ever changes, the bus name will be updated

## Enums
### RepeatType
- DISABLED = 0
- MINUTE = 1
- HOUR = 2
- DAY = 3
- WEEK = 4

### RepeatDays
- MON = 1
- TUE = 2
- WED = 4
- THU = 8
- FRI = 16
- SAT = 32
- SUN = 64

## Methods

### AddReminder
Add a new reminder
- Parameters (sa{sv})
    - app-id 
        - Type: s
        - Explanation [here](#app-id-parameter)
    - reminder
        - Type: a{sv}
        - {'title': s, 'description': s, 'timestamp': u, 'repeat-type': q, 'repeat-frequency': q, 'repeat-days': q, 'repeat-times': n, 'repeat-until': u, 'list': s, 'user-id': s}
        - 'timestamp' and 'repeat-until' should be a Unix timestamp, set them to 0 to disable them
        - 'repeat-times' should be -1 if you don't want to limit the repeat times
        - `list` can be 'local', 'ms-tasks' or a list id
        - `user-id` can be 'local' or a Microsoft user id

- Returns (s)
    - reminder-id
        - Type: s
        - Id that was generated to represent the reminder, keep track of these

### UpdateReminder
Update an existing reminder
- Parameters (sa{sv})
    - app-id 
        - Type: s
        - Explanation [here](#app-id-parameter)
    - reminder
        - Type: a{sv}
        - {'id': s, 'title': s, 'description': s, 'timestamp': u, 'repeat-type': q, 'repeat-frequency': q, 'repeat-days': q, 'repeat-times': n, 'repeat-until': u, 'list': s, 'user-id': s}
        - 'id' is the id of the reminder returned by AddReminder or ReturnReminders
        - 'timestamp' and 'repeat-until' should be a Unix timestamp, set them to 0 to disable them
        - 'repeat-times' should be -1 if you don't want to limit the repeat times
        - `list` can be 'local', 'ms-tasks' or a list id
        - `user-id` can be 'local' or a Microsoft user id
        - Any key can be left out to use the default instead
        - You only need to include the keys that are being updated, aside from the 'id' key which is required.

### UpdateCompleted
Update the completed status of a reminder
- Parameters (ssb)
    - app-id 
        - Type: s
        - Explanation [here](#app-id-parameter)
    - reminder-id
        - Type: s
        - Id of the reminder you want to update
    - completed 
        - Type: b
        - Whether or not the reminder should be completed

### RemoveReminder
Remove a reminder
- Parameters (ss)
    - app-id 
        - Type: s
        - Explanation [here](#app-id-parameter)
    - reminder-id
        - Type: s
        - Id of the reminder you want to remove

### CreateList
Create a list
- Parameters (sss)
    - app-id 
        - Type: s
        - Explanation [here](#app-id-parameter)
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
Create a list
- Parameters (ssss)
    - app-id 
        - Type: s
        - Explanation [here](#app-id-parameter)
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
Create a list
- Parameters (sss)
    - app-id 
        - Type: s
        - Explanation [here](#app-id-parameter)
    - user-id
        - Type: s
        - The user where the list is located, can be 'local' or a Microsoft user id
    - list-id
        - Type: s
        - The id of the list you are deleting

### ReturnReminders
Returns all reminders
- Returns (aa{sv})
    - reminders
        - Type: aa{sv}
        - An array of dictionaries that represent the reminders
        - {'id': s, 'title': s, 'description': s, 'timestamp': u, 'completed': b, 'repeat-type': q, 'repeat-frequency': q, 'repeat-days': q, 'repeat-times': n, 'repeat-until': u, 'old-timestamp': u, 'list': s, 'user-id': s}

### ReturnLists
Get all lists
- Returns (a{ss})
    - lists
        - Type: a{ss}
        - Each key is a list id and each value is the name of the list

### Refresh
Read reminders file again and also check for remote updates.

### MSGetEmails
Get emails of currently logged in Microsoft accounts
- Returns (a{ss})
    - email
        - Type: a{ss}
        - Each key is a user id and each value is the email of the account

### MSGetSyncedLists
- Returns (a{sas})
    - list-ids
        - Type: a{sas}
        - Each key is a user id and each value is an array of the list ids that are synced on that account

### MSSetSyncedLists
Set the task lists that should be synced
- Parameters (a{sas})
    - list-ids
        - Type: a{sas}
        - Each key should be a user id and each value should be an array of the list ids that are synced on that account

### MSLogin
Open browser window to login to microsoft account

### MSLogout
Log out of a microsoft account
- Parameters (s)
    - user-id
        - Type: s

### GetVersion
- Returns (d)
    - version
        - Type: d
        - The version of the service that is currently loaded

### Quit
Quits the service

## Signals

### RepeatUpdated
Emitted when a reminder is shown
- Parameters (s)
    - reminder-id
        - Type: s
        - The id of the reminder that was shown in a notification
    - timestamp
        - Type: u
        - The new timestamp (will be same as before if not repeating)
    - old-timestamp
        - Type: u
        - The timestamp from the last notification
    - repeat-times
        - Type: s
        - How many times left that the reminder will repeat (-1 if no limit)

### CompletedUpdated
Emitted when a reminder's completed status is changed
- Parameters (ssb)
    - app-id
        - Type: s
        - The id of the app that initiated the change
    - reminder-id
        - Type: s
        - The id of the reminder that was updated
    - completed
        - Type: b
        - Whether or not the reminder was set as completed

### ReminderDeleted
Emitted when a reminder is deleted
- Parameters (ss)
    - app-id
        - Type: s
        - The id of the app that initiated the change
    - reminder-id
        - Type: s
        - The id of the reminder that was deleted

### ReminderUpdated
Emitted when a Reminder is created or updated
- Parameters (sa{sv})
    - app-id
        - Type: s
        - The id of the app that initiated the change
    - reminder
        - Type: a{sv}
        - A dictionary with the new contents of the reminder that was updated
        - {'id': s, 'title': s, 'description': s, 'timestamp': u, 'repeat-type': q, 'repeat-frequency': q, 'repeat-days': q, 'repeat-times': n, 'repeat-until': u, 'list': s, 'user-id': s}

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

### ListUpdated
Emitted when a list is created or updated
- Parameters (ssss)
    - app-id
        - Type: s
        - The id of the app that initiated the change
    - user-id
        - Type: s
        - The user id of the list that was removed
    - list-id
        - Type: s
        - The id of the list that was removed
    - list-id
        - Type: s
        - The name of the list

### MSSignedIn
Emitted when the user signs in to a Microsoft account from the browser
- Returns (ss)
    - user-id
        - Type: s
    - email
        - Type: s

## MSSignedOut
Emitted when a Microsoft account is signed out
- Returns (ss)
    - user-id
        - Type: s

### MSSyncedListsChanged
Emitted when the dictionary of synced lists is changed
- Returns (a{sas})
    - list-ids
        - Type: a{sas}
        - Each key is a user id and each value is an array of the list ids that are synced on that account

## app-id parameter
This paremeter should be set to the id of your app, although it can be left empty. This will be returned in a signal after the reminder is updated, which will let you ignore the signal if you initiated the update.

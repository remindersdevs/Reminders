# Remembrance DBus Service Info, version 0.1
name: com.github.dgsasha.Remembrance.Service
interface: com.github.dgsasha.Remembrance.Service
object: /com/github/dgsasha/Remembrance/Service

Currently this is only packaged with Remembrance and anyone who wants to use it will have to have the full Remembrance app installed. The reason this exists is to allow integrating the Remembrance app with desktop environments through extensions.

At some point I might seperate this from Remembrance and offer it as a standalone library, but until then you probably shouldn't use it if you are making your own reminder app.

This service will have some breaking changes made to it at times, so make sure you use the GetVersion method to check that the right version is installed. You can relaunch the service with its desktop file to load the newest installed version, or by launching it in the command line with the `--gapplication-replace` argument.

Newer versions of this service should still always be compatible with apps that expect an older version. If this ever changes, the bus name will be updated

## Methods

### AddReminder
- Parameters (sa{sv})
    - app_id 
        - Type: s
        - Explanation [here](#app_id-parameter)
    - reminder
        - type a{sv}
        - {'title': s, 'description': s, 'timestamp': u}
        - 'timestamp' should be a Unix timestamp

- Returns (s)
    - reminder_id
        - Type: s
        - Id that was generated to represent the reminder, keep track of these

### UpdateReminder
- Parameters (sa{sv})
    - app_id 
        - Type: s
        - Explanation [here](#app_id-parameter)
    - reminder
        - type a{sv}
        - {'id': s, 'title': s, 'description': s, 'timestamp': u}
        - 'id' is the id of the reminder returned by AddReminder or ReturnReminders
        - 'timestamp' should be a Unix timestamp


### UpdateCompleted
- Parameters (ssb)
    - app_id 
        - Type: s
        - Explanation [here](#app_id-parameter)
    - reminder_id
        - Type: s
        - Id of the reminder you want to update
    - completed 
        - Type: b
        - Whether or not the reminder should be completed

### RemoveReminder
- Parameters (ss)
    - app_id 
        - Type: s
        - Explanation [here](#app_id-parameter)
    - reminder_id
        - Type: s
        - Id of the reminder you want to remove

### ReturnReminders
- Returns
    - reminders (aa{sv})
        - Type: aa{sv}
        - An array of dictionaries that represent the reminders
        - {'id: s, 'title': s, 'description': s, 'timestamp': u, 'completed': b}

### GetVersion
- Returns (d)
    - version
        - Type: d
        - The version of the service that is currently loaded


## Signals

### ReminderShown
- Parameters (s)
    - reminder_id
        - Type: s
        - The id of the reminder that was shown in a notification

### CompletedUpdated
- Parameters (ssb)
    - app_id
        - Type: s
        - The id of the app that initiated the change
    - reminder_id
        - Type: s
        - The id of the reminder that was updated
    - completed
        - Type: b
        - Whether or not the reminder was set as completed

### ReminderDeleted
- Parameters (ss)
    - app_id
        - Type: s
        - The id of the app that initiated the change
    - reminder_id
        - Type: s
        - The id of the reminder that was deleted

### ReminderUpdated
- Parameters (sa{sv})
    - app_id
        - Type: s
        - The id of the app that initiated the change
    - reminder
        - Type: a{sv}
        - A dictionary with the new contents of the reminder that was updated
        - {'id': s, 'title': s, 'description': s, 'timestamp': u}

## app_id parameter
This paremeter should be set to the id of your app, although it can be left empty. This will be returned in a signal after the reminder is updated, which will let you ignore the signal if you initiated the update.

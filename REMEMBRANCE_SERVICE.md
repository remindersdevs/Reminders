# Reminders DBus Service Info, version 1.4
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
- Parameters (sa{sv})
    - app_id 
        - Type: s
        - Explanation [here](#app_id-parameter)
    - reminder
        - Type: a{sv}
        - {'title': s, 'description': s, 'timestamp': u, 'repeat-type': q, 'repeat-frequency': q, 'repeat-days': q, 'repeat-times': n, 'repeat-until': u}
        - 'timestamp' and 'repeat-until' should be a Unix timestamp, set them to 0 to disable them
        - 'repeat-times' should be -1 if you don't want to limit the repeat times

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
        - Type: a{sv}
        - {'id': s, 'title': s, 'description': s, 'timestamp': u, 'repeat-type': q, 'repeat-frequency': q, 'repeat-days': q, 'repeat-times': n, 'repeat-until': u}
        - 'id' is the id of the reminder returned by AddReminder or ReturnReminders
        - 'timestamp' and 'repeat-until' should be a Unix timestamp, set them to 0 to disable them
        - 'repeat-times' should be -1 if you don't want to limit the repeat times

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

### Quit
Quits the service

## Signals

### RepeatUpdated
- Parameters (s)
    - reminder_id
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
        - {'id': s, 'title': s, 'description': s, 'timestamp': u, 'repeat-type': q, 'repeat-frequency': q, 'repeat-days': q, 'repeat-times': n, 'repeat-until': u}

## app_id parameter
This paremeter should be set to the id of your app, although it can be left empty. This will be returned in a signal after the reminder is updated, which will let you ignore the signal if you initiated the update.

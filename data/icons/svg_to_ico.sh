#!/usr/bin/env bash

for ID in 'io.github.remindersdevs.Reminders' 'io.github.remindersdevs.Reminders.Devel'; do
    convert -density 256x256 -background none "${ID}.svg" -define 'icon:auto-resize=256,96,80,72,64,60,48,40,36,32,30,24,20,16' -colors 256 "${ID}.ico"
done

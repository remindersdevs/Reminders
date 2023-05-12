
$IDS = @('io.github.remindersdevs.Reminders', 'io.github.remindersdevs.Reminders.Devel')
For ($i=0; $i -lt $IDS.Length; $i++) {
    $id = $IDS[$i]
    magick -density 256x256 -background none "${id}.svg" -define 'icon:auto-resize=256,96,80,72,64,60,48,40,36,32,30,24,20,16' -colors 256 "${id}.ico"
}

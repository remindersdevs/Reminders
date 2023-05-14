#!/usr/bin/env bash

=$(dirname "$(realpath "$0")")

cd "${dir}/../"

xgettext -f "${dir}/POTFILES" -o "${dir}/reminders.pot" --keyword=_ --add-comments=Translators --from-code=UTF-8 --package-name=reminders

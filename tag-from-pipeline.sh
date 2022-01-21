#! /bin/bash

function version_gt() {
  test "$(printf '%s\n' "$@" | sort -V | head -n 1)" != "$1";
}

function get_version_in_changelog() {
  for i in 1 2 3 4 5 6 7
  do
    version_line=$(sed "${i}q;d" CHANGELOG.rst) # Get ith line of file
    set -- $version_line
    version=$2
    if [[ $version =~ ^[0-9]+\.[0-9]+$ ]]; then
      echo $version $3
      return
    fi
  done
  if [[ ! $version ]]
  then
    printf "\033[0;31mChangelog file is incorrect, one of the first seven lines should be of the format 'Version xx.xx.'\033[0m";
    return 171
  fi
}

function verify_changelog_version() {
  read -r version date < <(get_version_in_changelog)
  current_version=$(git tag -l --sort=-version:refname | grep -E "^[0-9]+(\.[0-9]){1,2}$" | head -n 1)
  if version_gt "$current_version" "$version"; then
    printf "\033[0;31mNew version in the changelog (%s) should be greater than the current version (%s).\n\033[0m" "$version" "$current_version";
    return 172
  fi
  if [ $(git tag -l "$version") ]; then
    printf "Version %s already exists.\n" "$version";
    return 172
  fi
  printf "Current version is %s, new version is %s.\n" "$current_version" "$version";
}

function create_new_tag() {
  read -r version date < <(get_version_in_changelog)
  if [ -n "$date" ]; then
    printf "\033[0;33mWarning: content found after the version number, not releasing a new version.\n\033[0m";
    return 173
  fi
  # Only tag if version doesn't exist yet
  if ! [ $(git tag -l "$version") ]; then
    printf "Releasing version %s.\n" "$version"
    curl -X POST -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$GITHUB_REPOSITORY/releases" \
         -d "{\"tag_name\": \"$version\", \"name\": \"$version\", \"body\": \"Changelog: https://github.com/$GITHUB_REPOSITORY/blob/main/CHANGELOG.rst\"}"
  fi
}

"$@"

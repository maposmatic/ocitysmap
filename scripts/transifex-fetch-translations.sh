#! /bin/sh -x

# Pull translations from transifex
tx pull

# Commit any changes
# git diff

git config user.email "hakan@gurkensalat.com"
git config user.name "Hakan Tandogan"

git add scripts/transifex-fetch-translations.sh
git commit -m "Updated message translation fetching script" scripts/transifex-fetch-translations.sh

# Loop over all translations
for translation in $(find locale -name \*.po)
do
    # Set sane defaults for attribution
    git config user.email "transifex-daemon@gurkensalat.com"
    git config user.name "Transifex Daemon"

    # Try hard to attribute git commits to translators
    LAST_TRANSLATOR=$(grep Last-Translator: ${translation} | head -n 1)
    if [ $? == 0 ]
    then
	LAST_TRANSLATOR=$(echo ${LAST_TRANSLATOR} | sed -e 's/\"Last-Translator: //')
	LAST_TRANSLATOR=$(echo ${LAST_TRANSLATOR} | sed -e 's/\\n\"//')
	USER_EMAIL=$(echo ${LAST_TRANSLATOR} | sed -e 's/.*<//' | sed -e 's/>$//')
	USER_NAME=$(echo ${LAST_TRANSLATOR} | sed -e 's/ <.*>//')

	if [ ! "${USER_NAME}" == "FULL NAME" ]
	then
	    git config user.email "${USER_EMAIL}"
	    git config user.name "${USER_NAME}"
	fi
    fi

    # git config --list

    git add ${translation}
    git commit -m "Translated ${translation} on transifex.com" ${translation}

done

# Keep Jenkins happy so it won't mark the build as failed for no reason :-(
true

# Done, git push to be done manually or from jenkins

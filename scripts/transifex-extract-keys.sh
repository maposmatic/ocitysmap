#! /bin/sh -x

extract_gettext() {
    DIR=$1

    if [ -d ${DIR} ]
    then    
	pushd ${DIR}
	python2 ${DIR}/i18n.py --make-pot
	grep -v "POT-Creation-Date:" ${DIR}/locale/ocitysmap.pot > ${DIR}/locale/temp.pot
	mv ${DIR}/locale/temp.pot ${DIR}/locale/ocitysmap.pot
    fi
}

# Try to extract keys no matter where we are
[ -x ./i18n.py ]  && extract_gettext .
[ -x ../i18n.py ] && extract_gettext ..

# Push keys to transifex
tx push --no-interactive --source

# Commit any changes
git diff

git config user.email "hakan@gurkensalat.com"
git config user.name "Hakan Tandogan"

git add scripts/transifex-extract-keys.sh
git commit -m "Updated message key extraction script" scripts/transifex-extract-keys.sh

git config user.email "transifex-daemon@gurkensalat.com"
git config user.name "Transifex Daemon"

POTFILE=$(find . -name \*.pot | head -n 1)
git add ${POTFILE}
git commit -m "Extracted message keys" ${POTFILE}

# Keep Jenkins happy so it won't mark the build as failed for no reason :-(
true

# Done, git push to be done manually or from jenkins
